
## A/B Artifacts Quickstart
See docs/ab_artifacts_guide.md for fields, interpretation tips, and jq one-liners.

# Autonomous Task-Agent Dev Orchestration (ATADO)
- Advanced metrics: see docs/advanced_metrics.md and run scripts/advanced_metrics_report.py to generate drift/performance/cross-domain insights.


![Tests](https://github.com/hollis-source/autonomous-task-agent-dev-orchestration/workflows/Tests/badge.svg)
[![Smoke Tests](https://github.com/hollis-source/autonomous-task-agent-dev-orchestration/actions/workflows/smoke.yml/badge.svg)](https://github.com/hollis-source/autonomous-task-agent-dev-orchestration/actions/workflows/smoke.yml)

![Python](https://img.shields.io/badge/python-3.12+-blue)
![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)

**Production-ready multi-agent task orchestration framework** following Clean Architecture principles.

A CLI tool that intelligently distributes tasks to specialized agents (coder, tester, reviewer, researcher, coordinator) using LLM-powered execution with tool support. Inspired by *AI Agents in Action* and Robert C. Martin's Clean Code principles.

## Features

✅ **Multi-Task CLI**: Accept multiple tasks in a single command
✅ **DSL Workflow Mode**: Execute category theory-based `.ct` workflow files with lifecycle phases
✅ **HTN Decomposition**: Hierarchical Task Network compilation for recursive task breakdown
✅ **Graph Validation**: DAG cycle detection and topological execution order (NEW - Sprint 3)
✅ **Dynamic Executor Pool**: Capability-based task routing with no hardcoded mappings (NEW - Sprint 3)
✅ **Intelligent Agent Selection**: Fuzzy matching assigns tasks to best-fit agents
✅ **Multiple Orchestration Modes**: Simple (stable) or OpenAI Agents SDK (advanced features)
✅ **Tool Support**: Agents can execute shell commands, read/write files, run tests
✅ **LLM Providers**: Mock (testing), Grok, and Tongyi (production) with extensible architecture
✅ **Parallel Execution**: Concurrent task processing with dependency handling
✅ **Lifecycle Phases**: Plan → Verify → Decompose → Execute → Complete state tracking
✅ **Clean Architecture**: Entities → Use Cases → Interfaces → Adapters
✅ **95% Test Coverage**: 670 tests (all passing, including 61 Sprint 3 tests)

## Quick Start
For the fastest path, see docs/quickstart.md. For caching controls, see docs/developer/caching.md.


### Installation

**Requirements**: Python 3.12+ (Ubuntu 24.04+ or system supporting PEP 668)

```bash
# Clone repository
git clone https://github.com/hollis-source/autonomous-task-agent-dev-orchestration.git
cd autonomous-task-agent-dev-orchestration

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install UI-CLI (creates entry points)
pip install -e .

# Configure API keys
cp .env.example .env  # Then edit .env with your API keys
```

### Usage

**Option 1: Using wrapper script (works without venv activation)**
```bash
./bin/atado \
  --task "Write a Python function for factorial" \
  --task "Write tests for factorial function" \
  --provider auto
```

**Option 2: Using entry point (requires venv activation)**
```bash
source venv/bin/activate
atado \
  --task "Implement FizzBuzz in Python" \
  --task "Create comprehensive tests" \
  --provider grok \
  --verbose
```

**Option 3: Direct module invocation (legacy)**
```bash
source venv/bin/activate
python -m src.main \
  --task "Task description" \
  --provider auto
```

## Usage Examples

### Single Task

```bash
python3 src/main.py --task "Review the codebase for security issues" --provider mock
```

### Multi-Task Workflow

```bash
python3 src/main.py \
  --task "Implement binary search function" \
  --task "Write unit tests with edge cases" \
  --task "Review code for optimization opportunities" \
  --provider grok \
  --verbose
```


### Week 2 Pattern Collection Defaults (qwen3, RAG)

For Week 2 RAG pattern collection using scripts/build_rag_patterns.py:
- Default provider: qwen3 (Qwen/Qwen3-Next-80B-A3B-Instruct via HF Inference API)
- Default parallelism: P=6 (locked in as the standard for reliability)
- RAG: Enabled for each task invocation; embeddings stored with sentence-transformers/all-mpnet-base-v2

Quick start:
```bash
# In repo root (requires venv + HF token)
source venv/bin/activate
export HF_TOKEN=...  # or HUGGINGFACE_TOKEN

# Collect 25 patterns (defaults to --parallel 6)
python scripts/build_rag_patterns.py --target 25

# Override parallelism if needed (temporary):
python scripts/build_rag_patterns.py --target 25 --parallel 6
```

Notes:
- SurrealDB execution_log is used for storage; verify with the SurrealDB CLI if needed
- Keep domain-balanced selection (the script auto-balances across architecture, backend, devops, qa, testing)

### With Timeout and Parallel Execution

```bash
python3 src/main.py \
  --task "Analyze performance bottlenecks" \
  --task "Generate optimization report" \
  --provider grok \
  --timeout 120 \
  --parallel
```

### With Configuration File

```bash
# Create config file (see config.example.json)
python3 src/main.py \
  --task "Implement feature X" \
  --task "Write tests for feature X" \
  --config config.example.json \
  --verbose  # CLI args override config file
```

### DSL Workflow Mode (NEW)

Execute category theory-based workflow files (`.ct` DSL) with lifecycle phases:

```bash
# Execute DSL workflow with lifecycle tracking
python -m src.main \
  --workflow examples/workflows/simple_pipeline.ct \
  --verbose

# Output shows lifecycle phases:
✓ PLAN: Parsed workflow from examples/workflows/simple_pipeline.ct
✓ VERIFY: Passed 2 validation checks
✓ DECOMPOSE: 3 executable tasks identified
✓ EXECUTE: Workflow completed successfully

======================================================================
✓ Workflow Completed Successfully
======================================================================
Phases: PLAN → VERIFY → DECOMPOSE → EXECUTE → COMPLETE
```

**DSL Syntax Example** (`simple_pipeline.ct`):
```haskell
# Define workflow functors
functor build = python-specialist
functor test = unit-test-engineer
functor deploy = devops-lead

# Compose into pipeline (deploy ∘ test ∘ build)
functor main = deploy o test o build
```

**Benefits**:
- 📊 **Lifecycle Phases**: Plan → Verify → Decompose → Execute → Complete
- ✅ **Validation**: Workflows validated before execution
- 📝 **Declarative**: Express complex workflows in category theory DSL
- 🔄 **Composition**: Combine tasks using mathematical operators (`∘`, `×`)
- 🎯 **Phase Tracking**: Detailed execution progress with timing

For more DSL examples, see `examples/workflows/`.

### HTN Decomposition (NEW - Sprint 2)

Hierarchical Task Network compilation enables recursive task breakdown with composition semantics preserved:

```bash
# Execute HTN workflow
python -m src.main \
  --workflow examples/workflows/htn_pipeline.ct \
  --verbose

# Output shows HTN decomposition:
✓ DECOMPOSE: HTN: 5 tasks, depth=5, nodes=9
  HTN root: pipeline
  Subtasks: ['deployment', 'composition']
```

**HTN Example** (`htn_pipeline.ct`):
```haskell
# 5-stage development pipeline
functor analyze = research
functor design = design_arch
functor implement = code
functor test = testing
functor deploy = deployment

# HTN compiles to hierarchical tree
functor pipeline = deploy o test o implement o design o analyze
```

**How HTN Works**:
1. **AST Compilation**: DSL entities → HTNNode tree via visitor pattern
2. **Semantic Preservation**:
   - Composition (∘): Right-to-left execution order maintained
   - Product (×): Parallel execution semantics
   - Functors: Named reusable workflows
3. **Recursive Decomposition**: HTNNode.decompose() breaks complex tasks into subtasks
4. **Enhanced Observability**: Track depth, node count, execution structure

### Graph Validation & Executor Pool (NEW - Sprint 3)

Dependency graph modeling with cycle detection and dynamic agent routing:

```bash
# Execute workflow with graph validation
python -m src.main \
  --workflow examples/workflows/ci_pipeline.ct \
  --verbose

# Output shows graph validation:
✓ PLAN: Parsed workflow from examples/workflows/ci_pipeline.ct
✓ VERIFY: Passed 2 validation checks
✓ DECOMPOSE: HTN: 3 tasks, depth=3, nodes=5
  HTN root: ci_pipeline
  Graph: 5 nodes, 4 edges, DAG validated  # ← New graph validation
✓ EXECUTE: Workflow completed successfully
```

**Graph Validation Features**:
- **HTN→Graph Conversion**: Hierarchical tasks → Dependency graph (DAG)
- **Cycle Detection**: Validates no circular dependencies before execution (fail-fast)
- **Topological Execution**: Tasks execute in dependency-respecting order
- **Parallel Optimization**: Identifies independent tasks for concurrent execution

**Dynamic Executor Pool**:
- **No Hardcoded Mappings**: Tasks routed to agents based on capabilities
- **Automatic Registration**: Agents registered from AgentFactory (default/extended/scaled modes)
- **Capability Matching**: Task descriptions matched against agent capabilities
- **Extensible**: Add new agents without changing routing code (Open/Closed Principle)

**Example - Cycle Detection**:
```bash
# This workflow would fail validation (circular dependency)
functor a = task_a
functor b = task_b o a
functor main = a o b  # Creates cycle: a → b → a

# Error output:
✗ FAILED: Graph validation failed: Workflow contains circular dependencies (cycle detected)
```

**Benefits**:
- ⚡ **Fail-Fast**: Invalid workflows caught at planning time, not runtime
- 📊 **Execution Planning**: Graph analysis shows task dependencies and parallelization opportunities
- 🔧 **Dynamic Routing**: Capability-based task→agent matching (no hardcoded mappings)
- 🧩 **Extensibility**: Add agents/tasks without modifying routing code

**HTN Benefits** (Sprint 2):
- 🌳 **Hierarchical Structure**: Complex workflows decomposed into tree
- 🔄 **Composition Semantics**: Mathematical operators preserved in HTN
- 📊 **Enhanced Metrics**: Depth tracking, node counting, structure analysis
- 🧩 **Modular Workflows**: Functor reuse across different contexts
- ✅ **Backward Compatible**: Works with all existing DSL workflows

See `src/dsl/adapters/htn_compiler.py` for implementation.

### Orchestration Modes (Week 7)

Choose between two orchestration strategies:

**Simple Orchestrator (default, stable)**:
```bash
python3 src/main.py \
  --task "Research AI frameworks" \
  --task "Compare performance metrics" \
  --orchestrator simple \
  --provider tongyi
```

**OpenAI Agents SDK Orchestrator (advanced, Phase 1)**:
```bash
python3 src/main.py \
  --task "Research AI frameworks" \
  --task "Compare performance metrics" \
  --orchestrator openai-agents \
  --provider tongyi
```

**Performance Comparison**:
- **Simple**: Proven stability, full planning pipeline, best for complex workflows
- **OpenAI Agents**: 4x faster (Phase 1), future support for handoffs and tool calling

**Recommendation**: Use `simple` (default) for production. Use `openai-agents` for testing advanced features.

See [docs/PHASE_1.5_VALIDATION_SUMMARY.md](docs/PHASE_1.5_VALIDATION_SUMMARY.md) for benchmark results.

### End-to-End Demo

```bash
# Run complete dev workflow demo (requires API key)
python3 demo_full_workflow.py
```

## Architecture

```
src/
├── entity/            # Core business objects (Agent, Task, ExecutionResult)
├── use_cases/         # Business logic (TaskCoordinator, TaskPlanner)
├── interface/         # Abstractions (ITextGenerator, IAgentExecutor, IAgentCoordinator)
├── adapters/          # External integrations
│   ├── llm/          # LLM providers (GrokAdapter, MockProvider, TongyiAdapter)
│   ├── agent/        # Agent implementations (LLMAgentExecutor)
│   ├── orchestration/ # Orchestration adapters (OpenAIAgentsSDKAdapter)
│   └── cli/          # CLI adapters (ResultFormatter)
├── factories/         # Dependency Injection (AgentFactory, ProviderFactory, OrchestrationFactory)
├── composition.py     # Composition root
├── tools.py           # Dev tools (run_command, read_file, write_file, list_files)
└── main.py            # CLI entry point
```

### Clean Architecture Layers

1. **Entities** (innermost): Core business objects with no external dependencies
2. **Use Cases**: Business logic orchestrating entities
3. **Interfaces**: Abstractions following Dependency Inversion Principle
4. **Adapters** (outermost): External integrations (LLMs, CLI, tools)

**Dependency Rule**: Dependencies point inward only. Inner layers never depend on outer layers.

## Security

This CLI enables LLM agents to execute shell commands and file operations. See [SECURITY.md](SECURITY.md) for:
- Command execution security model
- File operation safety
- API key protection
- Best practices and threat model

**TL;DR**: The CLI is a power tool for trusted local development. Run in isolated workspaces, review agent actions, use version control, and see SECURITY.md for full details.

## Development

### Run Tests

```bash
source venv/bin/activate
PYTHONPATH=. pytest tests/ -v
```

### Check Coverage

```bash
PYTHONPATH=. pytest tests/ --cov=src --cov-report=term-missing
```

### Test Profiles

Fast/dry-run suite (excludes non-dry-run smoke tests):
```bash
source venv/bin/activate
PYTHONPATH=. pytest tests/ -v -k "not build_rag_patterns_smoke"
```

Non-dry-run smoke tests (minimal end-to-end):
```bash
source venv/bin/activate
PYTHONPATH=. pytest tests/integration/test_build_rag_patterns_smoke.py -v
```

### CI Workflows

- Default Tests workflow runs the fast suite and coverage (excludes non-dry-run smoke)
- Smoke Tests (Non-Dry-Run) workflow runs the minimal end-to-end smokes
  - Triggers: Manual (workflow_dispatch) and daily schedule (06:00 UTC)
  - Requires HF_TOKEN/HUGGINGFACE_TOKEN secrets if your provider uses HF

See:
- .github/workflows/tests.yml (fast suite)
### A/B Routing Evaluation

Run a small A/B evaluation (baseline vs RAG) and save a JSON report under logs/:
```bash
source venv/bin/activate
PYTHONPATH=. python scripts/ab_routing_eval.py --domains frontend research backend --per-domain 2 --provider qwen3
```

Summarize recent routing decisions (grouped by rag_used) to Markdown and JSON:
```bash
PYTHONPATH=. python scripts/routing_decisions_summary.py --limit 100
```
Notes:
- Proportions use both normal and Wilson score 95% CIs; difference in proportions uses Newcombe (1998) Wilson-based method.
- CSV includes per-condition aggregates and a diff row with both normal and Newcombe CIs for the difference.

- A separate diff CSV is also saved: logs/ab_eval_diff_<timestamp>.csv


CI:
- .github/workflows/ab_evaluation.yml runs a nightly small-N A/B evaluation and uploads the report as an artifact.

- .github/workflows/ab_evaluation.yml runs a daily small-N A/B and a weekly larger-N A/B (with CSV and routing summary artifacts)

For methodology, troubleshooting sparse routing_decisions, domain normalization rules, and interpreting CIs, see docs/ab_rag_vs_baseline.md.


- .github/workflows/smoke.yml (non-dry-run smokes)


### Add New Agent Type

```python
# src/factories/agent_factory.py
Agent(
    role="your_role",
    capabilities=["capability1", "capability2"]
)
```

### Add New LLM Provider

1. Implement `ITextGenerator` interface in `src/adapters/llm/`
2. Register in `ProviderFactory.create_provider()`
3. Add tests in `tests/integration/test_provider_integration.py`

### Add New Tool

Use the extensible tool registry for easy registration:

```python
# In your module
from src.tool_registry import default_registry

@default_registry.register(
    name="your_tool",
    description="What your tool does",
    parameters={
        "param": {"type": "string", "description": "Parameter description"}
    },
    required=["param"]
)
def your_tool(param: str) -> str:
    """Tool implementation."""
    return result
```

Tools are automatically available to LLM providers via `DEV_TOOLS` and `TOOL_FUNCTIONS`.

### CI/CD

GitHub Actions workflows automatically run on push/PR:

- **Tests**: Run full test suite on Python 3.10, 3.11, 3.12
- **Coverage**: Generate and upload coverage reports
- **Linting**: Check code style with flake8
- **Security**: Scan with bandit and safety
- See docs/claude_output_hooks.md for configuration-driven control of assistant output (redaction, verbosity, routing trace, code wrapping).


See [.github/workflows/tests.yml](.github/workflows/tests.yml) for configuration.

## Project Structure

- `src/`: Production code (Clean Architecture layers)
- `tests/`: Unit and integration tests (TDD approach)
- `scripts/`: Utilities (GrokSession, API clients)
- `demo_full_workflow.py`: End-to-end workflow demonstration
- `REFACTORING_ASSESSMENT.md`: Code quality analysis

## Testing Strategy

- **Unit Tests** (73): Test entities, use cases, tools, and CLI logic in isolation
- **Integration Tests** (31): Test component interactions, end-to-end workflows, and real file operations
- **Coverage**: 85% (tools: 96%, composition: 100%, use cases: 87-89%)

## Configuration

### Environment Variables (`.env` file)

```bash
XAI_API_KEY=your_grok_api_key_here
```

### Configuration File (Optional)

Use `--config` flag to load settings from JSON file. CLI arguments override config file values.

Example `config.json`:
```json
{
  "provider": "grok",
  "provider_config": {
    "model": "grok-code-fast-1",
    "temperature": 0.7
  },
  "parallel": true,
  "timeout": 120,
  "verbose": true,
  "custom_agents": [
    {
      "role": "security_analyst",
      "capabilities": ["security", "audit", "vulnerability"]
    }
  ]
}
```

See `config.example.json` for complete example.

## Roadmap

**Completed (Phase 1):**
- ✅ Multi-task CLI input
- ✅ Intelligent agent selection with fuzzy matching
- ✅ Tool-supported LLM execution
- ✅ Clean Architecture foundation
- ✅ Multiple LLM providers (Mock, Grok, Tongyi)
- ✅ OpenAI Agents SDK integration (Phase 1: adapter + fallback)
- ✅ Orchestration modes (simple, openai-agents)
- ✅ Performance benchmarking infrastructure

**In Progress (Phase 2):**
- 🔄 Full OpenAI Agents SDK execution (remove fallback)
- 🔄 Agent handoffs and delegation
- 🔄 Advanced tool calling via SDK
- 🔄 Guardrails and validation

**Future Enhancements:**
- 🔄 Additional LLM providers (OpenAI GPT-4, Anthropic Claude)
- 🔄 Persistent task history and context
- 🔄 Web UI for task management
- 🔄 Plugin system for custom agents and tools
- 🔄 Tracing and observability (OpenTelemetry)

## Principles

This project follows:
- **Clean Code** (Robert C. Martin): Small functions, meaningful names, explicit error handling
- **Clean Architecture**: Dependency inversion, use case-driven design
- **SOLID Principles**: SRP, OCP, LSP, ISP, DIP
- **TDD**: Tests first, refactor later
- **Pragmatic**: Fact-based decisions, avoid premature optimization

See `CLAUDE.md` for development guidelines.