# LangGraph Integration Guide

**Practical guide for integrating LangGraph into unified-intelligence-cli**

---

## Quick Start

### Installation
```bash
pip install langgraph langchain-core
```

### Basic Usage
```python
# Use LangGraph orchestrator
python3 -m src.main \
  --orchestrator langgraph \
  --task "Your task here"

# With checkpointing
python3 -m src.main \
  --orchestrator langgraph \
  --enable-checkpointing \
  --task "Task that needs persistence"

# With human-in-loop
python3 -m src.main \
  --orchestrator langgraph \
  --enable-human-in-loop \
  --task "Task requiring approval"
```

---

## Architecture Diagrams

### Current System Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Entry Point                          │
│                         (src/main.py)                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OrchestrationFactory                          │
│                (src/factories/orchestration_factory.py)          │
├─────────────────────────────────────────────────────────────────┤
│  create_orchestrator(mode) → IAgentCoordinator                  │
│    - mode="simple"  → TaskCoordinatorUseCase                    │
│    - mode="hybrid"  → HybridOrchestrator                        │
│    - mode="openai-agents" → OpenAIAgentsSDKAdapter              │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│   Simple    │  │    Hybrid    │  │  OpenAI SDK  │
│ Orchestrator│  │ Orchestrator │  │   Adapter    │
└─────────────┘  └──────────────┘  └──────────────┘
         │               │               │
         └───────────────┼───────────────┘
                         ▼
         ┌───────────────────────────────┐
         │   IAgentCoordinator Interface │
         │   coordinate(tasks, agents)   │
         └───────────────────────────────┘
```

### With LangGraph Integration
```
┌─────────────────────────────────────────────────────────────────┐
│                    OrchestrationFactory                          │
├─────────────────────────────────────────────────────────────────┤
│  create_orchestrator(mode) → IAgentCoordinator                  │
│    - mode="simple"     → TaskCoordinatorUseCase                 │
│    - mode="hybrid"     → HybridOrchestrator                     │
│    - mode="langgraph"  → LangGraphOrchestrator  ← NEW!          │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬───────────────┐
         ▼               ▼               ▼               ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Simple    │  │    Hybrid    │  │  OpenAI SDK  │  │  LangGraph   │
│ Orchestrator│  │ Orchestrator │  │   Adapter    │  │ Orchestrator │
└─────────────┘  └──────────────┘  └──────────────┘  └──────┬───────┘
                                                             │
                                                             ▼
                                              ┌──────────────────────┐
                                              │  LangGraph StateGraph│
                                              │  - Nodes (agents)    │
                                              │  - Edges (routing)   │
                                              │  - Checkpointing     │
                                              │  - Human-in-loop     │
                                              └──────────────────────┘
```

### LangGraph Orchestrator Internal Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│              LangGraphOrchestrator (Adapter)                     │
├─────────────────────────────────────────────────────────────────┤
│  Implements: IAgentCoordinator                                  │
│  Wraps: LangGraph StateGraph                                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │   State Conversion Layer      │
         │   ExecutionContext ↔ GraphState│
         └───────────────┬───────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │      LangGraph StateGraph     │
         ├───────────────────────────────┤
         │  START → supervisor           │
         │  supervisor → agent_1         │
         │  supervisor → agent_2         │
         │  agent_1 → supervisor         │
         │  agent_2 → supervisor         │
         │  supervisor → END             │
         └───────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ Agent 1 │    │ Agent 2 │    │ Agent N │
    │  Node   │    │  Node   │    │  Node   │
    └─────────┘    └─────────┘    └─────────┘
         │               │               │
         └───────────────┼───────────────┘
                         ▼
         ┌───────────────────────────────┐
         │   Our AgentExecutor           │
         │   (reuses existing logic)     │
         └───────────────────────────────┘
```

---

## Implementation Steps

### Step 1: Create LangGraph Orchestrator Adapter

**File**: `src/adapters/orchestration/langgraph_orchestrator.py`

```python
"""
LangGraph Orchestrator Adapter.

Integrates LangGraph as an orchestration strategy while preserving
Clean Architecture and DIP compliance.
"""

import logging
from typing import List, Optional, Dict, Any, Literal
from dataclasses import dataclass

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

from src.entity import Agent, Task, ExecutionResult, ExecutionStatus, ExecutionContext
from src.interface import IAgentCoordinator, IAgentExecutor


logger = logging.getLogger(__name__)


class LangGraphOrchestrator(IAgentCoordinator):
    """
    LangGraph-based orchestrator adapter.
    
    DIP: Implements IAgentCoordinator interface
    Adapter Pattern: Wraps LangGraph StateGraph
    Strategy Pattern: One of many orchestration strategies
    
    Use Cases:
    - Complex workflows with cycles
    - Human-in-the-loop approval flows
    - Workflows requiring checkpointing/persistence
    - Map-reduce patterns
    """
    
    def __init__(
        self,
        agent_executor: IAgentExecutor,
        enable_checkpointing: bool = False,
        enable_human_in_loop: bool = False,
        logger_instance: Optional[logging.Logger] = None
    ):
        """
        Initialize LangGraph orchestrator.
        
        Args:
            agent_executor: Executor for running individual agents
            enable_checkpointing: Enable state persistence
            enable_human_in_loop: Enable human approval workflows
            logger_instance: Optional logger
        """
        self.agent_executor = agent_executor
        self.enable_checkpointing = enable_checkpointing
        self.enable_human_in_loop = enable_human_in_loop
        self.logger = logger_instance or logger
        
        # Graph will be built per-request with available agents
        self.graph = None
    
    async def coordinate(
        self,
        tasks: List[Task],
        agents: List[Agent],
        context: Optional[ExecutionContext] = None
    ) -> List[ExecutionResult]:
        """
        Coordinate task execution using LangGraph.
        
        Strategy:
        1. Build LangGraph from available agents
        2. Convert tasks → LangGraph state
        3. Execute graph
        4. Convert results back to ExecutionResult
        
        Args:
            tasks: Tasks to execute
            agents: Available agents
            context: Optional execution context
            
        Returns:
            List of ExecutionResult
        """
        self.logger.info(f"LangGraph orchestrating {len(tasks)} tasks with {len(agents)} agents")
        
        # Build graph for this execution
        self.graph = self._build_graph(agents)
        
        results = []
        for task in tasks:
            result = await self._execute_task(task, agents, context)
            results.append(result)
        
        return results
    
    def _build_graph(self, agents: List[Agent]):
        """
        Build LangGraph StateGraph from agents.
        
        Architecture:
        - Supervisor node (routes to agents)
        - Agent nodes (execute tasks)
        - Conditional edges (routing logic)
        """
        # Define state schema
        @dataclass
        class GraphState(MessagesState):
            session_id: str
            current_task_id: str
            agent_outputs: Dict[str, Any]
            needs_human_approval: bool = False
        
        builder = StateGraph(GraphState)
        
        # Add supervisor node
        builder.add_node("supervisor", self._create_supervisor_node(agents))
        
        # Add agent nodes
        for agent in agents:
            builder.add_node(agent.role, self._create_agent_node(agent))
        
        # Entry point
        builder.add_edge(START, "supervisor")
        
        # Supervisor routes to agents
        agent_names = [a.role for a in agents]
        builder.add_conditional_edges(
            "supervisor",
            self._route_to_agent,
            {name: name for name in agent_names} | {"__end__": END}
        )
        
        # Agents return to supervisor
        for agent in agents:
            builder.add_edge(agent.role, "supervisor")
        
        # Compile with optional checkpointing
        if self.enable_checkpointing:
            return builder.compile(checkpointer=MemorySaver())
        
        return builder.compile()
    
    def _create_supervisor_node(self, agents: List[Agent]):
        """Create supervisor node function."""
        async def supervisor(state: Dict) -> Command:
            """Supervisor decides which agent to call next."""
            # Simple routing: use first agent for now
            # TODO: Implement intelligent routing based on task
            
            if state.get("agent_outputs"):
                # Task complete
                return Command(goto=END)
            
            # Route to first agent
            next_agent = agents[0].role
            self.logger.debug(f"Supervisor routing to {next_agent}")
            
            return Command(
                goto=next_agent,
                update={"current_task_id": state.get("current_task_id", "unknown")}
            )
        
        return supervisor
    
    def _create_agent_node(self, agent: Agent):
        """Create agent node function."""
        async def agent_node(state: Dict) -> Dict:
            """Execute agent on current task."""
            # Extract task from state
            task = Task(
                task_id=state.get("current_task_id", "unknown"),
                description=state["messages"][-1].content if state.get("messages") else "",
                priority=1
            )
            
            # Execute using our existing executor
            result = await self.agent_executor.execute(agent, task)
            
            # Update state
            return {
                "messages": [{"role": "assistant", "content": str(result.output)}],
                "agent_outputs": {agent.role: result.output}
            }
        
        return agent_node
    
    def _route_to_agent(self, state: Dict) -> str:
        """Routing function for conditional edges."""
        if state.get("agent_outputs"):
            return "__end__"
        
        # Default: route to first available agent
        # TODO: Implement intelligent routing
        return "agent"
    
    async def _execute_task(
        self,
        task: Task,
        agents: List[Agent],
        context: Optional[ExecutionContext]
    ) -> ExecutionResult:
        """Execute single task using LangGraph."""
        # Convert to LangGraph input
        graph_input = {
            "messages": [{"role": "user", "content": task.description}],
            "session_id": context.session_id if context else "default",
            "current_task_id": task.task_id,
            "agent_outputs": {},
            "needs_human_approval": False
        }
        
        try:
            # Execute graph
            graph_output = await self.graph.ainvoke(graph_input)
            
            # Convert back to ExecutionResult
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=graph_output.get("agent_outputs", {}),
                metadata={
                    "orchestrator": "langgraph",
                    "graph_state": graph_output
                }
            )
        
        except Exception as e:
            self.logger.error(f"LangGraph execution failed: {e}")
            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                output=None,
                errors=[str(e)],
                error_details={
                    "error_type": "LangGraphExecutionError",
                    "component": "LangGraphOrchestrator",
                    "root_cause": str(e)
                }
            )
```

### Step 2: Update OrchestrationFactory

**File**: `src/factories/orchestration_factory.py`

```python
# Add import
try:
    from src.adapters.orchestration.langgraph_orchestrator import LangGraphOrchestrator
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    LangGraphOrchestrator = None

# Update create_orchestrator method
@staticmethod
def create_orchestrator(
    mode: str,
    llm_provider: ITextGenerator,
    task_planner: ITaskPlanner,
    agent_executor: IAgentExecutor,
    agents: List[Agent],
    logger_instance: Optional[logging.Logger] = None,
    enable_checkpointing: bool = False,  # NEW
    enable_human_in_loop: bool = False   # NEW
) -> IAgentCoordinator:
    """Create orchestrator based on mode."""
    
    if mode == "langgraph":
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph not installed. Run: pip install langgraph")
        
        logger_instance.info("Creating LangGraph orchestrator")
        return LangGraphOrchestrator(
            agent_executor=agent_executor,
            enable_checkpointing=enable_checkpointing,
            enable_human_in_loop=enable_human_in_loop,
            logger_instance=logger_instance
        )
    
    elif mode == "simple":
        # Existing simple orchestrator
        ...
    
    elif mode == "hybrid":
        # Existing hybrid orchestrator
        ...
```

### Step 3: Update CLI

**File**: `src/main.py`

```python
@click.option(
    "--orchestrator",
    type=click.Choice(["simple", "hybrid", "openai-agents", "langgraph"]),
    default="simple",
    help="Orchestration strategy"
)
@click.option(
    "--enable-checkpointing",
    is_flag=True,
    help="Enable LangGraph checkpointing (requires --orchestrator langgraph)"
)
@click.option(
    "--enable-human-in-loop",
    is_flag=True,
    help="Enable human-in-loop workflows (requires --orchestrator langgraph)"
)
def main(
    task: str,
    orchestrator: str,
    enable_checkpointing: bool,
    enable_human_in_loop: bool,
    ...
):
    """Main CLI entry point."""
    
    # Create orchestrator with new flags
    coordinator = orchestration_factory.create_orchestrator(
        mode=orchestrator,
        llm_provider=llm_provider,
        task_planner=task_planner,
        agent_executor=agent_executor,
        agents=agents,
        logger_instance=logger,
        enable_checkpointing=enable_checkpointing,
        enable_human_in_loop=enable_human_in_loop
    )
    
    # Execute
    results = await coordinator.coordinate(tasks, agents, context)
```

---

## Usage Examples

### Example 1: Simple Task (No LangGraph Needed)
```bash
# Use our existing simple orchestrator
python3 -m src.main \
  --orchestrator simple \
  --task "Implement feature X"
```

### Example 2: Task with Retries (LangGraph Cycles)
```bash
# Use LangGraph for retry logic
python3 -m src.main \
  --orchestrator langgraph \
  --task "Debug issue, retry until fixed (max 3 attempts)"
```

### Example 3: Human Approval Workflow
```bash
# Use LangGraph for human-in-loop
python3 -m src.main \
  --orchestrator langgraph \
  --enable-human-in-loop \
  --task "Generate deployment plan, wait for approval, then deploy"
```

### Example 4: Long-Running Task with Checkpointing
```bash
# Use LangGraph for persistence
python3 -m src.main \
  --orchestrator langgraph \
  --enable-checkpointing \
  --task "Multi-hour refactoring task (can resume if interrupted)"
```

---

## Testing

### Unit Tests

**File**: `tests/unit/adapters/test_langgraph_orchestrator.py`

```python
import pytest
from src.adapters.orchestration.langgraph_orchestrator import LangGraphOrchestrator
from src.entity import Agent, Task, ExecutionContext
from tests.mocks import MockAgentExecutor

@pytest.mark.asyncio
async def test_langgraph_orchestrator_basic():
    """Test basic LangGraph orchestration."""
    executor = MockAgentExecutor()
    orchestrator = LangGraphOrchestrator(executor)
    
    agents = [Agent(role="test-agent", capabilities=["testing"])]
    tasks = [Task(task_id="1", description="Test task", priority=1)]
    
    results = await orchestrator.coordinate(tasks, agents)
    
    assert len(results) == 1
    assert results[0].status == ExecutionStatus.SUCCESS
```

### Integration Tests

**File**: `tests/integration/test_langgraph_integration.py`

```python
@pytest.mark.asyncio
async def test_langgraph_with_real_agents():
    """Test LangGraph with real agent execution."""
    # Setup
    llm_provider = create_test_llm_provider()
    agents = create_test_agents()
    orchestrator = LangGraphOrchestrator(
        agent_executor=AgentExecutor(llm_provider),
        enable_checkpointing=True
    )
    
    # Execute
    tasks = [Task(task_id="1", description="Complex task", priority=1)]
    results = await orchestrator.coordinate(tasks, agents)
    
    # Verify
    assert results[0].status == ExecutionStatus.SUCCESS
    assert "langgraph" in results[0].metadata["orchestrator"]
```

---

## Performance Considerations

### Conversion Overhead
- **State conversion**: ExecutionContext ↔ LangGraph state adds ~5-10ms per task
- **Mitigation**: Cache graph compilation, reuse across tasks

### Memory Usage
- **Checkpointing**: MemorySaver stores full state history
- **Mitigation**: Use Redis checkpointer for production

### Latency
- **Graph compilation**: ~50-100ms per graph build
- **Mitigation**: Build graph once, reuse for multiple tasks

---

## Troubleshooting

### Issue: "LangGraph not installed"
```bash
pip install langgraph langchain-core
```

### Issue: "State conversion failed"
- Check ExecutionContext has all required fields
- Verify LangGraph state schema matches

### Issue: "Graph execution timeout"
- Increase recursion limit: `config={"recursion_limit": 50}`
- Check for infinite loops in conditional edges

---

## Next Steps

1. Implement `LangGraphOrchestrator` adapter
2. Add to `OrchestrationFactory`
3. Update CLI with new flags
4. Write tests
5. Document usage patterns
6. Benchmark performance
7. Production validation

---

## References

- Main analysis: `docs/LANGGRAPH_INTEGRATION_ANALYSIS.md`
- LangGraph docs: https://langchain-ai.github.io/langgraph/
- Our orchestration: `docs/HYBRID_ORCHESTRATION_GUIDE.md`

