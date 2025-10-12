# Category Theory DSL Examples

This directory contains examples demonstrating the Category Theory DSL for task orchestration.

## Files

### Python Examples
- **dsl_example.py**: Mock executor demonstration (visitor pattern)
- **dsl_real_interpreter.py**: Real interpreter with CLI integration
- **run_dsl_example.sh**: Run mock executor examples
- **run_real_interpreter.sh**: Run real interpreter examples

### DSL Workflow Files (.ct)
- **workflows/simple_pipeline.ct**: Basic CI/CD pipeline
- **workflows/parallel_build.ct**: Parallel frontend/backend build
- **workflows/fullstack_pipeline.ct**: Complete full-stack workflow
- **workflows/ci_pipeline.ct**: Reusable CI/CD functor
- **workflows/README.md**: Detailed documentation for .ct files

## Running the Examples

### Option 1: CLI Integration (Execute .ct files)
```bash
# Run a DSL workflow file
PYTHONPATH=. venv/bin/python -m src.dsl.cli_integration examples/workflows/simple_pipeline.ct

# With verbose output
PYTHONPATH=. venv/bin/python -m src.dsl.cli_integration examples/workflows/fullstack_pipeline.ct --verbose

# Other examples
PYTHONPATH=. venv/bin/python -m src.dsl.cli_integration examples/workflows/parallel_build.ct
PYTHONPATH=. venv/bin/python -m src.dsl.cli_integration examples/workflows/ci_pipeline.ct
```

### Option 2: Python Examples
```bash
# Mock executor (demonstrates visitor pattern)
./examples/run_dsl_example.sh

# Real interpreter (demonstrates CLI integration)
./examples/run_real_interpreter.sh

# Or with Python directly
PYTHONPATH=. venv/bin/python3 examples/dsl_example.py
PYTHONPATH=. venv/bin/python3 examples/dsl_real_interpreter.py
```

## What's Demonstrated

The example shows the complete DSL pipeline:

1. **Parsing**: DSL text → AST using Lark parser
2. **Visitor Pattern**: AST traversal for execution
3. **Category Theory Semantics**:
   - **Composition (∘)**: Sequential task chaining
   - **Product (×)**: Parallel execution
   - **Functors**: Reusable workflow mappings

## Example Programs

### Simple Sequential Composition
```
test ∘ build
```
Execute `build` first, then `test`.

### Parallel Execution
```
frontend × backend
```
Execute `frontend` and `backend` concurrently.

### Complex Pipeline
```
(test_ui × test_api) ∘ (build_ui × build_api) ∘ plan
```
Three-stage pipeline:
1. Plan
2. Build UI and API in parallel
3. Test UI and API in parallel

### Functor Definition
```
functor ci_pipeline = deploy ∘ test ∘ build
```
Define reusable workflow: build → test → deploy.

## Architecture

- **Clean Architecture**: Adapter layer (parser) → Entity layer (AST)
- **Visitor Pattern**: MockExecutor traverses AST
- **Immutability**: All AST nodes are frozen dataclasses
- **Type Safety**: Parser validates syntax, entities validate structure

## Features Implemented

✅ **Complete DSL Pipeline**:
1. **Parser**: Lark-based EBNF parser (DSL text → AST)
2. **Interpreter**: Visitor pattern execution with asyncio
3. **Result Propagation**: Data flows through compositions
4. **CLI Integration**: Execute .ct files from command line
5. **Task-to-Agent Mapping**: Intelligent routing (22 default mappings)

✅ **Category Theory Semantics**:
- **Composition (∘)**: Sequential, right-to-left execution with result propagation
- **Product (×)**: True parallel execution with asyncio.gather
- **Functors**: Reusable named workflows
- **Type Safety**: Parser + entity validation throughout

✅ **Production Ready**:
- 87 tests passing (100%)
- 78% code coverage
- Clean Architecture (4 layers)
- SOLID principles throughout
- TDD from start (Red-Green-Refactor)

## Quick Start

1. **Create a .ct file** (or use examples in `workflows/`):
   ```
   # my_workflow.ct
   deploy ∘ test ∘ build
   ```

2. **Execute it**:
   ```bash
   PYTHONPATH=. venv/bin/python -m src.dsl.cli_integration my_workflow.ct
   ```

3. **See results with verbose mode**:
   ```bash
   PYTHONPATH=. venv/bin/python -m src.dsl.cli_integration my_workflow.ct --verbose
   ```
