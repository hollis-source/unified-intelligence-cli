# Category Theory DSL Examples

This directory contains examples demonstrating the Category Theory DSL for task orchestration.

## Files

- **dsl_example.py**: End-to-end demonstration of DSL parsing and execution
- **run_dsl_example.sh**: Shell wrapper to run the example (handles PYTHONPATH)

## Running the Examples

```bash
# From project root
./examples/run_dsl_example.sh

# Or with Python directly
PYTHONPATH=. venv/bin/python3 examples/dsl_example.py
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

## Next Steps

The mock executor demonstrates the visitor pattern. A real interpreter would:
1. Map task names to actual agents (e.g., `build` → `python-specialist`)
2. Execute tasks via the unified-intelligence-cli
3. Handle parallel execution with asyncio
4. Propagate results through compositions
