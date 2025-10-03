# Type-Safe DSL Workflow Guide

**Status**: Production Ready ✅
**Sprints**: 1-3 Complete (Type System + Validation + Grammar Enhancement)

## Overview

The unified-intelligence-cli DSL provides **end-to-end type safety** for workflow composition using category theory principles and Hindley-Milner type annotations.

## Features

### 1. **Hindley-Milner Type Annotations**

```haskell
# Type signature syntax: name :: Type -> Type
fetch_data :: () -> Data
process_data :: Data -> Result
save_result :: Result -> ()
```

**Supported Types:**
- **Monomorphic**: `Int`, `String`, `Data`, `Result` (capitalized)
- **Type Variables**: `a`, `b`, `c` (single lowercase letter)
- **Function Types**: `A -> B`, `A -> B -> C` (right-associative)
- **Product Types**: `A × B`, `(Int × String)` (parallel data)
- **Unit Type**: `()` (empty/void)
- **Type Constructors**: `List[T]`, `Dict[K, V]`

### 2. **Functor Definitions**

Two syntaxes supported (Sprint 3, Phase 1):

```haskell
# Explicit (verbose, clear)
functor workflow = process o fetch

# Implicit (concise, Haskell-style) - NEW in Sprint 3!
workflow = process o fetch
```

**Both are equivalent** - use whichever fits your style!

### 3. **Composition Operators**

#### Sequential Composition: `∘` (or `o`)

```haskell
# Category Theory: (f ∘ g)(x) = f(g(x))
# Right-to-left execution
pipeline = save o process o fetch
```

**Type Checking**: Output of `g` must match input of `f`

```haskell
fetch :: () -> Data
process :: Data -> Result
save :: Result -> ()

# Valid: Data matches Data, Result matches Result
pipeline = save o process o fetch  # ✓ Type-safe

# Invalid: Type mismatch
invalid = fetch o save  # ✗ TypeError: Result ≠ ()
```

#### Parallel Composition: `×` (or `*`)

```haskell
# Category Theory: Product category (A × B)
# Concurrent execution with same input
parallel = (analyze_style * analyze_security * analyze_complexity)
```

**Type**: `(f × g) :: A -> (B × C)` where `f :: A -> B`, `g :: A -> C`

### 4. **Type Safety Levels**

#### Pre-Execution Validation (Sprint 2, Phase 2)

```python
from src.dsl.use_cases import WorkflowValidator

validator = WorkflowValidator()
report = validator.validate_file("workflow.ct")

if report.success:
    print("✓ Type-safe workflow")
    print(report.type_environment)
else:
    print(report.summary())  # Show errors
```

#### Runtime Type Validation (Sprint 2, Phase 3)

```python
from src.dsl.use_cases import TypedInterpreter
from src.dsl.adapters import CLITaskExecutor

# Validate first
report = validator.validate_file("workflow.ct")

# Execute with runtime validation
executor = CLITaskExecutor()
interpreter = TypedInterpreter(
    task_executor=executor,
    type_env=report.type_environment,
    strict=True  # Raise errors on type mismatch
)

result = await interpreter.execute(ast)
```

### 5. **Category Theory Laws**

All compositions enforce mathematical correctness:

1. **Associativity**: `(f ∘ g) ∘ h ≡ f ∘ (g ∘ h)`
2. **Identity**: `id ∘ f ≡ f ≡ f ∘ id`
3. **Type Preservation**: Morphisms preserve structure

## Complete Example

```haskell
# ============================================================================
# Type Annotations
# ============================================================================

get_files :: () -> FileList
analyze_style :: FileList -> StyleReport
analyze_security :: FileList -> SecurityReport
merge_reports :: (StyleReport × SecurityReport) -> FullReport
post_results :: FullReport -> ()

# ============================================================================
# Workflows
# ============================================================================

# Sequential: One analysis
style_check = analyze_style o get_files

# Parallel: Two analyses concurrently
parallel_analysis = (analyze_style * analyze_security) o get_files

# Complex: Sequential + Parallel
full_workflow = post_results o merge_reports o parallel_analysis

# ============================================================================
# Type Flow
# ============================================================================

# full_workflow type derivation:
# ()
#   → get_files :: () -> FileList
#   → FileList
#   → (analyze_style × analyze_security) :: FileList -> (StyleReport × SecurityReport)
#   → (StyleReport × SecurityReport)
#   → merge_reports :: (StyleReport × SecurityReport) -> FullReport
#   → FullReport
#   → post_results :: FullReport -> ()
#   → ()
```

## Validation Workflow

```bash
# 1. Write .ct file with type annotations
vim workflow.ct

# 2. Validate types (pre-execution)
python3 -c "
from src.dsl.use_cases import WorkflowValidator
validator = WorkflowValidator()
report = validator.validate_file('workflow.ct')
print(report.summary())
"

# 3. Execute with runtime validation
python3 -c "
from src.dsl.adapters.parser import Parser
from src.dsl.use_cases import TypedInterpreter
from src.dsl.adapters import CLITaskExecutor
import asyncio

async def run():
    parser = Parser()
    ast = parser.parse(open('workflow.ct').read())

    executor = CLITaskExecutor()
    interpreter = TypedInterpreter(executor)
    result = await interpreter.execute(ast)
    return result

asyncio.run(run())
"
```

## Architecture

### Clean Architecture Layers

```
┌─────────────────────────────────────────┐
│  Use Cases (Business Logic)             │
│  - WorkflowValidator                    │
│  - TypedInterpreter                     │
│  - Interpreter                          │
└─────────────────────────────────────────┘
           ↓ depends on ↓
┌─────────────────────────────────────────┐
│  Entities (Domain Model)                │
│  - Type System (Type, FunctionType,     │
│    MonomorphicType, TypeVariable)       │
│  - AST Nodes (Literal, Composition,     │
│    Product, Functor)                    │
└─────────────────────────────────────────┘
           ↓ depends on ↓
┌─────────────────────────────────────────┐
│  Adapters (External Dependencies)       │
│  - Parser (Lark grammar)                │
│  - CLITaskExecutor                      │
└─────────────────────────────────────────┘
```

### SOLID Principles

- **SRP**: Each class has one responsibility
  - `WorkflowValidator` → Pre-execution validation only
  - `TypedInterpreter` → Runtime validation only
  - `Parser` → Parsing only

- **OCP**: Open for extension, closed for modification
  - `TypedInterpreter extends Interpreter` (adds validation without modifying base)
  - Grammar supports both explicit/implicit syntax (extension, not modification)

- **DIP**: Depend on abstractions
  - `TypedInterpreter` depends on `TypeEnvironment` (interface)
  - `Interpreter` depends on `TaskExecutor` protocol (not concrete implementation)

## Sprint History

| Sprint | Phase | Feature | Commit |
|--------|-------|---------|--------|
| 1 | 3 | Type Checker | 7a770dc |
| 1 | 4 | Category Theory Laws | 3f2e95f |
| 1 | 5 | Error Reporting | 4ca9178 |
| 2 | 1 | Parser Integration | 90f4d85 |
| 2 | 2 | Workflow Validator | 6e77146 |
| 2 | 3 | Runtime Validation | b79a975 |
| 3 | 1 | Grammar Enhancement | e771e97 |
| 3 | 2 | Workflow Examples | (current) |

## References

- **Grammar**: `src/dsl/adapters/grammar.lark`
- **Parser**: `src/dsl/adapters/parser.py`
- **Type System**: `src/dsl/types/type_system.py`
- **Validator**: `src/dsl/use_cases/workflow_validator.py`
- **Runtime**: `src/dsl/use_cases/typed_interpreter.py`
- **Examples**: `examples/workflows/*.ct`

## Next Steps

- **Sprint 3, Phase 3**: Integration testing (validate + execute workflows end-to-end)
- **Future**: Monad transformers, distributed execution semantics
