# Quick Start: OpenAI Agents SDK Phase 2 Implementation

**Goal**: Complete Phase 2 integration in 7 days (Week 10)
**Prerequisites**: Phase 1 adapter exists, Tongyi-30B running, 96 cores available

---

## Day 1-2: SDK Setup & Custom Client

### Step 1: Install OpenAI Agents SDK (5 min)
```bash
cd /home/ui-cli_jake/unified-intelligence-cli
venv/bin/pip install openai-agents
```

### Step 2: Verify llama-cpp-server Compatibility (5 min)
```bash
# Test OpenAI-compatible endpoint
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tongyi",
    "messages": [
      {"role": "user", "content": "Say hello"}
    ]
  }'
```

Expected: JSON response with `{"choices": [{"message": {"content": "..."}}]}`

### Step 3: Update OpenAIAgentsSDKAdapter (1 hour)

Edit `src/adapters/orchestration/openai_agents_sdk_adapter.py`:

**Changes**:
1. Add custom client import (top of file):
```python
from openai import OpenAI
```

2. Update `__init__` method (line 45):
```python
def __init__(
    self,
    llm_provider: ITextGenerator,
    agents: List[Agent],
    max_turns: int = 10
):
    if not AGENTS_SDK_AVAILABLE:
        raise ImportError("Run: pip install openai-agents")

    self.llm_provider = llm_provider
    self.agents = agents
    self.max_turns = max_turns

    # NEW: Create custom client for Tongyi (llama-cpp-server)
    self.client = OpenAI(
        base_url="http://localhost:8080/v1",
        api_key="not-needed"  # Local server doesn't need key
    )

    # Convert agents to SDK format
    self.sdk_agents = self._convert_agents_to_sdk(agents)

    logger.info(f"OpenAIAgentsSDKAdapter initialized with SDK client")
```

3. Replace `_execute_single_task` method (line 184):
```python
async def _execute_single_task(
    self,
    task: Task,
    agents: List[Agent],
    context: Optional[ExecutionContext]
) -> ExecutionResult:
    """Execute single task using SDK (Phase 2: Proper SDK integration)."""

    # Select starting agent
    starting_agent = self._select_starting_agent(task, agents)
    if not starting_agent:
        return self._create_failure_result(task, "No suitable agent found")

    logger.debug(f"Selected agent '{starting_agent.role}' for task {task.task_id}")

    sdk_agent = self.sdk_agents.get(starting_agent.role)
    if not sdk_agent:
        return self._create_failure_result(task, f"SDK agent '{starting_agent.role}' not found")

    # NEW: Use SDK properly with custom client
    try:
        # Import Runner (SDK execution engine)
        from agents import Runner

        runner = Runner(client=self.client)

        # Run SDK synchronously (async wrapper in Phase 2.4)
        result = runner.run_sync(
            agent=sdk_agent,
            input=task.description
        )

        # Convert SDK result to our ExecutionResult
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output=result.final_output if hasattr(result, 'final_output') else str(result),
            errors=[],
            metadata={
                "agent_role": starting_agent.role,
                "task_id": task.task_id,
                "orchestrator": "openai-agents-sdk",
                "phase": "2-sdk-integrated"
            }
        )

    except Exception as e:
        logger.error(f"SDK execution failed: {e}")
        return self._create_failure_result(task, str(e))
```

4. Remove old fallback method `_execute_with_llm_provider` (lines 246-288) - no longer needed

### Step 4: Test SDK Integration (30 min)
```bash
# Test simple mode (baseline)
venv/bin/python3 -m src.main \
  --task "Write a Python function to calculate factorial" \
  --provider tongyi \
  --mode simple \
  --verbose

# Test openai-agents mode (SDK)
venv/bin/python3 -m src.main \
  --task "Write a Python function to calculate factorial" \
  --provider tongyi \
  --mode openai-agents \
  --verbose
```

**Expected**: Both modes succeed, openai-agents uses SDK (check logs for "SDK client")

### Step 5: Benchmark Comparison (30 min)
```bash
# Create benchmark script
cat > scripts/benchmark_sdk.py << 'EOF'
#!/usr/bin/env python3
"""Benchmark simple vs openai-agents mode."""

import time
import subprocess

tasks = [
    "Write a function to reverse a string",
    "Create a function to check if a number is prime",
    "Implement binary search algorithm",
    "Write a function to merge two sorted lists",
    "Create a class for a simple stack data structure"
]

def run_task(task, mode):
    """Run single task and measure time."""
    start = time.time()
    result = subprocess.run(
        [
            "venv/bin/python3", "-m", "src.main",
            "--task", task,
            "--provider", "tongyi",
            "--mode", mode
        ],
        capture_output=True,
        text=True
    )
    duration = time.time() - start
    success = result.returncode == 0
    return duration, success

print("Benchmarking: simple vs openai-agents mode")
print("=" * 60)

for mode in ["simple", "openai-agents"]:
    print(f"\nMode: {mode}")
    total_time = 0
    successes = 0

    for i, task in enumerate(tasks, 1):
        duration, success = run_task(task, mode)
        total_time += duration
        successes += success
        print(f"  Task {i}: {duration:.2f}s {'✓' if success else '✗'}")

    avg_time = total_time / len(tasks)
    success_rate = (successes / len(tasks)) * 100

    print(f"\n  Total: {total_time:.2f}s")
    print(f"  Average: {avg_time:.2f}s")
    print(f"  Success Rate: {success_rate:.0f}%")
EOF

chmod +x scripts/benchmark_sdk.py

# Run benchmark
./scripts/benchmark_sdk.py
```

**Expected**: Similar performance initially (handoffs add value in Phase 2.2+)

---

## Day 3-4: Handoffs Implementation

### Step 1: Create Handoff Configuration (30 min)
```bash
mkdir -p config

cat > config/agent_handoffs.json << 'EOF'
{
  "researcher": {
    "description": "Investigates topics, reads documentation, gathers information",
    "handoffs": [
      {
        "target": "coder",
        "triggers": ["implement", "code", "write", "create", "build"],
        "description": "Hand off to coder when implementation is needed"
      }
    ]
  },
  "coder": {
    "description": "Writes code, implements features, fixes bugs",
    "handoffs": [
      {
        "target": "tester",
        "triggers": ["test", "verify", "validate", "check"],
        "description": "Hand off to tester for validation"
      }
    ]
  },
  "tester": {
    "description": "Writes tests, validates code, checks edge cases",
    "handoffs": [
      {
        "target": "reviewer",
        "triggers": ["review", "assess", "critique", "evaluate"],
        "description": "Hand off to reviewer for code quality assessment"
      }
    ]
  },
  "reviewer": {
    "description": "Reviews code, checks SOLID principles, suggests improvements",
    "handoffs": [
      {
        "target": "coder",
        "triggers": ["fix", "refactor", "improve", "change"],
        "description": "Hand off to coder for fixes/improvements"
      }
    ]
  },
  "coordinator": {
    "description": "Plans tasks, breaks down features, coordinates agents",
    "handoffs": [
      {
        "target": "researcher",
        "triggers": ["research", "investigate", "explore", "learn"],
        "description": "Hand off to researcher for investigation"
      },
      {
        "target": "coder",
        "triggers": ["implement", "code", "write"],
        "description": "Hand off to coder for implementation"
      }
    ]
  }
}
EOF
```

### Step 2: Implement Handoff Functions (2 hours)

Edit `src/adapters/orchestration/openai_agents_sdk_adapter.py`:

**Add helper method** (after line 145):
```python
def _load_handoff_config(self) -> Dict[str, Any]:
    """Load handoff configuration from JSON file."""
    import json
    from pathlib import Path

    config_path = Path("config/agent_handoffs.json")
    if not config_path.exists():
        logger.warning("agent_handoffs.json not found, using empty config")
        return {}

    with open(config_path) as f:
        return json.load(f)

def _create_handoff_functions(self) -> Dict[str, callable]:
    """
    Create handoff functions for SDK agents.

    Returns dict: {agent_role: [handoff_functions]}
    """
    config = self._load_handoff_config()
    handoff_funcs = {}

    for agent_role, agent_config in config.items():
        funcs = []

        for handoff in agent_config.get("handoffs", []):
            target = handoff["target"]
            description = handoff["description"]

            # Create closure for handoff function
            def make_handoff(target_role):
                def handoff_to_target():
                    """Handoff function dynamically created."""
                    return self.sdk_agents.get(target_role)
                handoff_to_target.__name__ = f"handoff_to_{target_role}"
                handoff_to_target.__doc__ = description
                return handoff_to_target

            funcs.append(make_handoff(target))

        handoff_funcs[agent_role] = funcs

    return handoff_funcs
```

**Update `_convert_agents_to_sdk`** (line 76):
```python
def _convert_agents_to_sdk(self, agents: List[Agent]) -> Dict[str, SDKAgent]:
    """Convert our Agent entities to SDK Agent objects with handoffs."""

    # Create handoff functions first
    handoff_funcs = self._create_handoff_functions()

    sdk_agents = {}

    for agent in agents:
        instructions = self._capabilities_to_instructions(agent.capabilities)

        # Get handoff functions for this agent
        tools = handoff_funcs.get(agent.role, [])

        # Create SDK agent with handoffs
        sdk_agent = SDKAgent(
            name=agent.role,
            instructions=instructions,
            tools=tools  # SDK will call these to handoff
        )

        sdk_agents[agent.role] = sdk_agent
        logger.debug(f"Converted agent: {agent.role} with {len(tools)} handoffs")

    return sdk_agents
```

### Step 3: Test Multi-Agent Workflow (1 hour)
```bash
# Test 1: Researcher → Coder
venv/bin/python3 -m src.main \
  --task "Research Python async/await syntax, then implement a simple async example" \
  --provider tongyi \
  --mode openai-agents \
  --verbose

# Expected: Handoff from researcher to coder (check logs)

# Test 2: Full Pipeline (Researcher → Coder → Tester)
venv/bin/python3 -m src.main \
  --task "Research the quicksort algorithm, implement it in Python, and write tests for it" \
  --provider tongyi \
  --mode openai-agents \
  --verbose

# Expected: 2 handoffs (researcher → coder → tester)

# Test 3: Review Loop (Coder → Tester → Reviewer → Coder)
venv/bin/python3 -m src.main \
  --task "Write a Python function with intentional bugs, test it to find issues, review the code, and fix the bugs" \
  --provider tongyi \
  --mode openai-agents \
  --verbose

# Expected: 3+ handoffs with loop back to coder
```

---

## Day 5-6: Context Management

### Step 1: Implement SDK Sessions (1 hour)

Edit `src/adapters/orchestration/openai_agents_sdk_adapter.py`:

**Update `_execute_single_task`** (line 184):
```python
async def _execute_single_task(
    self,
    task: Task,
    agents: List[Agent],
    context: Optional[ExecutionContext]
) -> ExecutionResult:
    """Execute with SDK Sessions for context persistence."""

    starting_agent = self._select_starting_agent(task, agents)
    if not starting_agent:
        return self._create_failure_result(task, "No suitable agent found")

    sdk_agent = self.sdk_agents.get(starting_agent.role)
    if not sdk_agent:
        return self._create_failure_result(task, f"SDK agent not found")

    try:
        from agents import Runner, Session

        runner = Runner(client=self.client)

        # NEW: Create session with context variables
        session = Session(
            context_variables={
                "task_id": task.task_id or "unknown",
                "priority": task.priority,
                "description": task.description,
                "shared_findings": {},  # Agents write here
                "handoff_history": []   # Track handoffs
            }
        )

        # Run SDK with session
        result = runner.run_sync(
            agent=sdk_agent,
            input=task.description,
            session=session,  # Persistent across handoffs
            max_turns=self.max_turns
        )

        # Extract context after execution
        final_context = session.context_variables if hasattr(session, 'context_variables') else {}

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output=result.final_output if hasattr(result, 'final_output') else str(result),
            errors=[],
            metadata={
                "agent_role": starting_agent.role,
                "task_id": task.task_id,
                "orchestrator": "openai-agents-sdk",
                "phase": "2-with-context",
                "handoff_history": final_context.get("handoff_history", []),
                "shared_findings": final_context.get("shared_findings", {})
            }
        )

    except Exception as e:
        logger.error(f"SDK execution failed: {e}")
        return self._create_failure_result(task, str(e))
```

### Step 2: Test Context Continuity (1 hour)
```bash
# Test: Context flows across handoffs
venv/bin/python3 -m src.main \
  --task "Research the Singleton design pattern (store findings in context), implement it in Python (read context from researcher), and test it" \
  --provider tongyi \
  --mode openai-agents \
  --verbose

# Verify: Check logs/metadata for shared_findings with researcher's notes
```

---

## Day 7: Parallel Execution & Benchmarking

### Step 1: Parallel Groups with SDK (1 hour)

Edit `src/adapters/orchestration/openai_agents_sdk_adapter.py`:

**Update `coordinate` method** (line 147):
```python
async def coordinate(
    self,
    tasks: List[Task],
    agents: List[Agent],
    context: Optional[ExecutionContext] = None
) -> List[ExecutionResult]:
    """Coordinate with parallel execution for independent tasks."""

    logger.info(f"Coordinating {len(tasks)} tasks with OpenAI Agents SDK")

    # Identify independent tasks (simple heuristic: no shared dependencies)
    # Phase 2.4: Run independent tasks in parallel
    results = await asyncio.gather(*[
        self._execute_single_task(task, agents, context)
        for task in tasks
    ], return_exceptions=True)

    # Convert exceptions to failure results
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            final_results.append(
                self._create_failure_result(tasks[i], str(result))
            )
        else:
            final_results.append(result)

    logger.info(f"Coordination complete: {len(final_results)} results")
    return final_results
```

### Step 2: Comprehensive Benchmark (2 hours)
```bash
# Create parallel benchmark
cat > scripts/benchmark_parallel.py << 'EOF'
#!/usr/bin/env python3
"""Benchmark parallel execution."""

import time
import asyncio
import sys
sys.path.insert(0, '/home/ui-cli_jake/unified-intelligence-cli')

from src.entities import Task
from src.factories import AgentFactory, ProviderFactory, OrchestrationFactory
from src.use_cases.task_planner import TaskPlannerUseCase
from src.adapters.execution.llm_agent_executor import LLMAgentExecutor

async def benchmark(mode, num_tasks):
    """Run benchmark with specified mode and task count."""

    # Create dependencies
    agent_factory = AgentFactory()
    agents = agent_factory.create_default_agents()

    provider_factory = ProviderFactory()
    llm_provider = provider_factory.create_provider("tongyi")

    task_planner = TaskPlannerUseCase()
    agent_executor = LLMAgentExecutor(llm_provider=llm_provider)

    # Create orchestrator
    orchestrator = OrchestrationFactory.create_orchestrator(
        mode=mode,
        llm_provider=llm_provider,
        task_planner=task_planner,
        agent_executor=agent_executor,
        agents=agents
    )

    # Create tasks
    tasks = [
        Task(
            task_id=f"task_{i}",
            description=f"Write a Python function to compute the {i}th Fibonacci number",
            priority=1
        )
        for i in range(1, num_tasks + 1)
    ]

    # Run benchmark
    start = time.time()
    results = await orchestrator.coordinate(tasks, agents)
    duration = time.time() - start

    # Calculate metrics
    successes = sum(1 for r in results if r.status.value == "success")
    success_rate = (successes / len(results)) * 100

    return {
        "mode": mode,
        "tasks": num_tasks,
        "duration": duration,
        "successes": successes,
        "success_rate": success_rate,
        "throughput": num_tasks / duration
    }

async def main():
    print("Parallel Execution Benchmark")
    print("=" * 80)

    for mode in ["simple", "openai-agents"]:
        for num_tasks in [5, 10, 20, 30]:
            result = await benchmark(mode, num_tasks)

            print(f"\nMode: {result['mode']}, Tasks: {result['tasks']}")
            print(f"  Duration: {result['duration']:.2f}s")
            print(f"  Success Rate: {result['success_rate']:.0f}%")
            print(f"  Throughput: {result['throughput']:.2f} tasks/sec")

if __name__ == "__main__":
    asyncio.run(main())
EOF

chmod +x scripts/benchmark_parallel.py

# Run benchmark
venv/bin/python3 scripts/benchmark_parallel.py
```

**Expected Results**:
- **simple mode**: ~2-5 tasks/sec (baseline)
- **openai-agents mode**: ~5-15 tasks/sec (2-3x improvement with handoffs)

### Step 3: Document Results (30 min)
```bash
# Create performance report
cat > docs/PHASE_2_PERFORMANCE_REPORT.md << 'EOF'
# Phase 2 Performance Report

## Benchmark Results (Week 10, Day 7)

### Test Environment
- **CPU**: AMD EPYC 9454P (96 cores)
- **RAM**: 1.1TB total
- **Model**: Tongyi-DeepResearch-30B (llama-cpp-server)
- **Baseline**: simple mode (TaskCoordinatorUseCase)
- **Test**: openai-agents mode (OpenAIAgentsSDKAdapter Phase 2)

### Results

| Mode | Tasks | Duration | Success Rate | Throughput |
|------|-------|----------|--------------|------------|
| simple | 5 | X.Xs | XX% | X.X tasks/sec |
| openai-agents | 5 | X.Xs | XX% | X.X tasks/sec |
| simple | 10 | X.Xs | XX% | X.X tasks/sec |
| openai-agents | 10 | X.Xs | XX% | X.X tasks/sec |
| simple | 20 | X.Xs | XX% | X.X tasks/sec |
| openai-agents | 20 | X.Xs | XX% | X.X tasks/sec |
| simple | 30 | X.Xs | XX% | X.X tasks/sec |
| openai-agents | 30 | X.Xs | XX% | X.X tasks/sec |

### Analysis
- **Handoffs**: Average X handoffs per complex task
- **Context**: Shared context used in X% of multi-agent workflows
- **Parallelism**: X concurrent tasks (vs Y baseline)
- **Improvement**: X.Xx speedup for 30-task workload

### Conclusion
Phase 2 integration: [SUCCESS/NEEDS TUNING]
- Handoffs working: [YES/NO]
- Context sharing: [YES/NO]
- Parallel scaling: [YES/NO]

Next: Phase 2.5 (add 10 more agents) or tune existing implementation.
EOF
```

---

## Verification Checklist

After Day 7, verify:

- [ ] SDK installed: `venv/bin/pip list | grep openai-agents`
- [ ] Custom client working: Check logs for "SDK client" initialization
- [ ] Single agent execution: simple vs openai-agents both succeed
- [ ] Handoffs functional: Researcher → Coder → Tester workflow
- [ ] Context persistence: Shared findings across handoffs
- [ ] Parallel execution: 10+ tasks run concurrently
- [ ] Performance improvement: 2-3x throughput vs baseline
- [ ] Success rate maintained: ≥98% (match baseline)

---

## Troubleshooting

### Issue 1: SDK Import Error
**Error**: `ImportError: No module named 'agents'`
**Fix**: `venv/bin/pip install openai-agents`

### Issue 2: llama-cpp-server Connection Failed
**Error**: `Connection refused to localhost:8080`
**Fix**: Start server with `docker start llama-cpp-server` or check port

### Issue 3: Handoffs Not Triggering
**Error**: No handoffs in logs, single agent handles all
**Fix**:
- Check `config/agent_handoffs.json` exists
- Verify triggers match task description keywords
- Add `--verbose` flag to see handoff decisions

### Issue 4: Context Not Persisting
**Error**: Coder doesn't have researcher's findings
**Fix**:
- Check SDK Session creation in `_execute_single_task`
- Verify `context_variables` dict passed to runner
- Add logging: `logger.debug(f"Session context: {session.context_variables}")`

### Issue 5: Performance Worse Than Baseline
**Error**: openai-agents mode slower than simple
**Fix**:
- Expected initially (handoff overhead)
- Improves with 10+ tasks (parallelism benefit)
- Tune `max_turns` (lower = faster, but fewer handoffs)

---

## Next Steps After Phase 2

### Option 1: Tune Current Implementation (1-2 days)
- Optimize handoff triggers (reduce false positives)
- Add guardrails (prevent infinite loops)
- Improve context structure (templates per agent)

### Option 2: Phase 2.5 - Add 10 More Agents (1 week)
- Create 10 specialized agents (see WEEK_10 doc)
- Define handoffs for new agents
- Benchmark with 15-agent workflows

### Option 3: Production Rollout (Week 12)
- Enable openai-agents mode by default
- Set up monitoring (Prometheus/Grafana)
- Document user guide for new features

---

**Document**: Quick Start Guide
**Date**: 2025-10-01
**Author**: Strategic planning analysis
**Status**: Ready to execute
**Timeline**: 7 days (Week 10)
EOF
```

Perfect! Now I have:
1. Comprehensive Week 10 strategy document
2. Quick start guide with day-by-day instructions
3. All research complete

Let me update the user.
