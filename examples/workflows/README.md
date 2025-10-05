# DSL Workflow Examples (.ct files)

This directory contains example Category Theory DSL programs that can be executed from the command line.

## Files

- `simple_pipeline.ct` - Basic sequential CI/CD pipeline
- `parallel_build.ct` - Parallel frontend/backend build
- `fullstack_pipeline.ct` - Complete full-stack development workflow
- `ci_pipeline.ct` - Reusable CI/CD functor definition

## Running DSL Programs

### Unified CLI (Recommended - NEW)

Execute workflows through the main CLI with lifecycle phases:

```bash
# From project root (with venv activated)
python -m src.main --workflow examples/workflows/simple_pipeline.ct

# With verbose output showing lifecycle phases
python -m src.main --workflow examples/workflows/fullstack_pipeline.ct --verbose

# Output shows lifecycle progression:
✓ PLAN: Parsed workflow from examples/workflows/simple_pipeline.ct
✓ VERIFY: Passed 2 validation checks
✓ DECOMPOSE: 3 executable tasks identified
✓ EXECUTE: Workflow completed successfully
```

**Lifecycle Phases**:
- **PLAN**: Parse `.ct` file to AST, extract symbol table
- **VERIFY**: Validate workflow structure (non-empty, executable nodes)
- **DECOMPOSE**: Identify and count executable tasks
- **EXECUTE**: Run workflow via interpreter
- **COMPLETE**: Return results with timing

### Legacy Method (Deprecated):
```bash
# Old way - still works but lacks lifecycle tracking
PYTHONPATH=. venv/bin/python -m src.dsl.cli_integration examples/workflows/simple_pipeline.ct
```

### Using Python Directly (Advanced):
```python
from src.dsl.adapters.parser import Parser
from src.dsl.use_cases.interpreter import Interpreter
from src.dsl.adapters.cli_task_executor import CLITaskExecutor

# Read .ct file
with open('examples/workflows/simple_pipeline.ct') as f:
    dsl_text = f.read()

# Parse and execute
parser = Parser()
ast = parser.parse(dsl_text)

executor = CLITaskExecutor()
interpreter = Interpreter(executor)

result = await interpreter.execute(ast)
```

## DSL Syntax

### Composition (∘)
Sequential execution, right-to-left:
```
deploy ∘ test ∘ build
# Executes: build → test → deploy
```

### Product (×)
Parallel execution:
```
frontend × backend
# Executes: frontend ∥ backend (concurrent)
```

### Functor
Reusable named workflow:
```
functor ci_pipeline = deploy ∘ test ∘ build
```

### Complex Expressions
Combine operators with parentheses:
```
(test_ui × test_api) ∘ (build_ui × build_api) ∘ plan
```

## Task-to-Agent Mapping

The DSL automatically maps tasks to appropriate agents:

- `build`, `code`, `implement` → python-specialist
- `test`, `unit_test` → unit-test-engineer
- `frontend`, `build_ui`, `ui` → frontend-lead
- `backend`, `build_api`, `api` → backend-lead
- `deploy`, `integrate`, `package` → devops-lead
- `plan`, `design`, `architect` → master-orchestrator, research-lead
- `document`, `docs` → technical-writer

## Examples Explained

### simple_pipeline.ct
Basic three-stage pipeline. Demonstrates sequential composition where each task's output flows to the next.

### parallel_build.ct
Builds frontend and backend concurrently. Demonstrates parallel execution with the product operator (×).

### fullstack_pipeline.ct
Complete workflow:
1. Plan architecture (sequential)
2. Build UI and API in parallel
3. Test UI and API in parallel
4. Integrate everything (sequential)

Demonstrates combining sequential (∘) and parallel (×) operators.

### ci_pipeline.ct
Defines a reusable workflow using the functor construct. Can be referenced and reused across multiple programs.
