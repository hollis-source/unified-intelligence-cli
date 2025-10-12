# DSL User Guide - Category Theory Workflows

**Complete guide to the Unified Intelligence CLI's Category Theory DSL with Hindley-Milner Type System**

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Operators](#core-operators)
3. [Type System (Phase 3)](#type-system-phase-3)
4. [Workflow Examples](#workflow-examples)
5. [Tool History & Metrics](#tool-history--metrics)
6. [Advanced Patterns](#advanced-patterns)

---

## Quick Start

### Execute a Workflow

```bash
# Workflow mode
python -m src.main --workflow examples/workflows/model_fallback.ct --provider auto

# Direct task mode
python -m src.main --task "analyze code quality" --provider grok
```

### Basic Workflow Syntax

```ct
# Simple composition
pipeline = test ∘ build

# Parallel execution
analysis = security × performance

# Fallback (coproduct)
resilient = primary + backup

# Execute
pipeline
```

---

## Core Operators

### 1. Sequential Composition (`∘`)

**Execution**: Right-to-left (mathematical function composition)

```ct
# Type signature
f :: A → B
g :: B → C
result :: A → C
result = g ∘ f

# Example: CI/CD Pipeline
deploy :: Artifact → Deployment
build :: TestReport → Artifact
test :: Code → TestReport

ci_pipeline = deploy ∘ build ∘ test
# Execution order: test → build → deploy
```

**Real Example**:
```bash
python -m src.main --workflow examples/workflows/ci_pipeline.ct
```

### 2. Parallel Composition (`×`)

**Execution**: Concurrent (all tasks run simultaneously)

```ct
# Type signature
f :: A → B
g :: C → D
result :: (A × C) → (B × D)
result = f × g

# Example: Parallel Analysis
security :: Code → SecurityReport
performance :: Code → PerformanceReport
quality :: Code → QualityReport

parallel = security × performance × quality
# All three analyses run concurrently
```

**Real Example**:
```bash
python -m src.main --workflow examples/workflows/parallel_analysis.ct
```

### 3. Coproduct/Choice (`+`)

**Execution**: First-success with lazy evaluation (Phase 2c)

```ct
# Type signature (both must have same input/output types)
f :: A → B
g :: A → B
result :: A → B
result = f + g

# Example: Model Fallback
grok :: Query → Answer
qwen :: Query → Answer
claude :: Query → Answer

# Try grok first, if fails try qwen, if both fail try claude
resilient = grok + qwen + claude
```

**Semantics**:
1. Try left alternative with input
2. If succeeds, return result (short-circuit)
3. If fails, try right alternative
4. If both fail, raise combined error

**Real Example**:
```bash
python -m src.main --workflow examples/workflows/model_fallback.ct
```

### 4. Duplicate/Broadcast (`Δ`)

**Execution**: Broadcast input to both branches

```ct
# Type signature
Δ :: a → (a × a)

# Example: Broadcast for Parallel Processing
analyze :: Code → Analysis
review :: Code → Review

# Broadcast code to both analyze and review
parallel = (analyze × review) ∘ Δ
```

---

## Type System (Phase 3)

### Optional Type Checking

**Enable type checking** to catch errors before execution:

```ct
# Type annotations (optional, recommended)
format :: Code → Code
lint :: Code → Code
test :: Code → TestReport
build :: TestReport → Artifact

# Valid composition (types match)
pipeline = build ∘ test ∘ lint ∘ format
# ✅ test output (TestReport) matches build input (TestReport)

# Invalid composition (type error)
# invalid = test ∘ build
# ❌ build output (Artifact) ≠ test input (Code)
```

### Type Annotations

**Basic Types**:
```ct
task :: InputType → OutputType
```

**Polymorphic Types** (Phase 3):
```ct
identity :: a → a
duplicate :: a → (a × a)
map :: (a → b) → [a] → [b]
```

**Product Types**:
```ct
parallel :: (A × B) → (C × D)
```

### Type Checking Rules

1. **Composition (`∘`)**: `f: A → B`, `g: B → C` ⇒ `g ∘ f: A → C`
   - Requires: `f.output` unifies with `g.input`

2. **Product (`×`)**: `f: A → B`, `g: C → D` ⇒ `f × g: (A × C) → (B × D)`
   - Always valid (no type constraints)

3. **Coproduct (`+`)**: `f: A → B`, `g: A → B` ⇒ `f + g: A → B`
   - Requires: Same input types AND same output types
   - Ensures consistent result type for fallback

---

## Workflow Examples

### Example 1: Model Fallback with Resilience

```ct
# File: examples/workflows/model_fallback.ct

# Type annotations
grok :: Query → Analysis
qwen :: Query → Analysis
claude :: Query → Analysis

# Triple fallback
resilient_analysis = grok + qwen + claude

# Execute
resilient_analysis
```

**Run**:
```bash
python -m src.main --workflow examples/workflows/model_fallback.ct
```

**Tool History**: All execution attempts logged to SurrealDB

### Example 2: CI/CD Pipeline

```ct
# File: examples/workflows/ci_pipeline.ct

# Type annotations
format :: Code → Code
lint :: Code → Code
test :: Code → TestReport
build :: TestReport → Artifact
deploy :: Artifact → Deployment

# Sequential pipeline
functor ci_pipeline = deploy ∘ build ∘ test ∘ lint ∘ format

# Execute
ci_pipeline
```

**Run**:
```bash
python -m src.main --workflow examples/workflows/ci_pipeline.ct --collect-metrics
```

### Example 3: Parallel Security Analysis

```ct
# File: examples/workflows/parallel_analysis.ct

# Type annotations
security_scan :: Code → SecurityReport
performance_analysis :: Code → PerformanceReport
code_quality :: Code → QualityReport

# Concurrent execution
parallel_analysis = security_scan × performance_analysis × code_quality

# Execute
parallel_analysis
```

**Run**:
```bash
python -m src.main --workflow examples/workflows/parallel_analysis.ct --parallel
```

### Example 4: Complex Deployment (All Operators)

```ct
# File: examples/workflows/complex_deployment.ct

# Build and test
build_pipeline = build ∘ test

# Deployment with fallback
deployment = (deploy_prod + deploy_staging) ∘ build_pipeline

# Parallel validation
validation = validate_security × validate_health

# Complete workflow
complete_workflow = validation ∘ deployment

# Execute
complete_workflow
```

**Run**:
```bash
python -m src.main --workflow examples/workflows/complex_deployment.ct \
  --provider auto \
  --routing team \
  --agents scaled \
  --collect-metrics
```

---

## Tool History & Metrics

### Enable Tool History (Phase 2b)

Tool execution history is automatically tracked when SurrealDB is available:

```bash
# Start SurrealDB
surreal start --log trace --bind 0.0.0.0:8000 file://db/

# Run workflow with history tracking
python -m src.main --workflow examples/workflows/resilient_pipeline.ct \
  --collect-metrics
```

### Query Tool History

```python
from src.adapters.database.tool_history_repository import ToolHistoryRepository

repo = ToolHistoryRepository(
    host="localhost",
    port=8000,
    namespace="project_builder",
    database="production"
)

# Get metrics for a team
metrics = repo.get_team_metrics("backend-team")
print(f"Success rate: {metrics['success_rate']:.1%}")
print(f"Avg duration: {metrics['avg_duration_ms']}ms")
print(f"Most used tool: {metrics['most_used_tool']}")
```

### Metrics Dashboard

View real-time metrics:

```bash
# Enable metrics collection
python -m src.main --workflow examples/workflows/ci_pipeline.ct \
  --collect-metrics \
  --metrics-dir data/metrics
```

---

## Advanced Patterns

### Pattern 1: Resilient Multi-Stage Pipeline

```ct
# Each stage has fallback
analyze = (primary_analyze + backup_analyze)
transform = (primary_transform + backup_transform)
validate = (primary_validate + backup_validate)

# Compose resilient stages
resilient_pipeline = validate ∘ transform ∘ analyze
```

### Pattern 2: Fan-Out/Fan-In

```ct
# Broadcast input to parallel processors
process_a :: Data → ResultA
process_b :: Data → ResultB
process_c :: Data → ResultC

# Combine results
combine :: (ResultA × ResultB × ResultC) → FinalResult

# Fan-out then fan-in
pipeline = combine ∘ (process_a × process_b × process_c) ∘ Δ
```

### Pattern 3: Conditional Execution with Coproduct

```ct
# Different execution paths based on success
fast_path :: Input → Output
slow_path :: Input → Output
emergency_path :: Input → Output

# Automatically selects working path
adaptive = fast_path + slow_path + emergency_path
```

### Pattern 4: Reusable Functors

```ct
# Define reusable workflows
functor security_check = scan_vulnerabilities ∘ analyze_dependencies
functor quality_check = lint ∘ type_check ∘ test

# Compose functors
complete_check = security_check × quality_check
```

---

## Execution Modes

### 1. Workflow Mode (Recommended)

```bash
python -m src.main --workflow FILE.ct [OPTIONS]
```

**Options**:
- `--provider`: LLM provider (auto, grok, qwen, claude)
- `--routing`: team (recommended) or individual
- `--agents`: scaled (16 agents), extended (8), or default (5)
- `--orchestrator`: hybrid (default), simple, or openai-agents
- `--collect-metrics`: Enable metrics collection
- `--parallel`: Enable parallel execution
- `--verbose`: Detailed output

### 2. Direct Task Mode

```bash
python -m src.main --task "TASK DESCRIPTION" [OPTIONS]
```

### 3. Type-Checked Mode (Phase 3)

```python
from src.dsl.use_cases.interpreter import Interpreter
from src.dsl.types.type_checker import TypeEnvironment
from src.dsl.types.type_system import FunctionType, MonomorphicType

# Create type environment
type_env = TypeEnvironment()
type_env.bind("test", FunctionType(
    input_type=MonomorphicType("Code"),
    output_type=MonomorphicType("TestReport")
))

# Enable type checking
interpreter = Interpreter(
    task_executor=executor,
    enable_type_checking=True,
    type_env=type_env
)

# Type errors caught before execution
result = await interpreter.execute(ast)
```

---

## Troubleshooting

### Type Errors

**Problem**: `Type mismatch in composition`

**Solution**: Check type annotations match:
```ct
# ❌ Invalid
f :: A → B
g :: C → D
invalid = g ∘ f  # B ≠ C

# ✅ Valid
f :: A → B
g :: B → C
valid = g ∘ f  # B = B ✓
```

### Coproduct Errors

**Problem**: `Coproduct: both alternatives failed`

**Solution**: Ensure fallbacks have same types:
```ct
# ✅ Valid (same types)
primary :: String → Int
backup :: String → Int
fallback = primary + backup

# ❌ Invalid (different output types)
primary :: String → Int
backup :: String → Float
invalid = primary + backup
```

### Tool History Not Recording

**Problem**: Tool history not saved

**Solutions**:
1. Start SurrealDB: `surreal start --bind 0.0.0.0:8000 file://db/`
2. Enable metrics: `--collect-metrics`
3. Check connection: `curl http://localhost:8000/health`

---

## Additional Resources

- **Examples**: `examples/workflows/` (45+ real workflows)
- **Tests**: `tests/dsl/` (comprehensive test suite)
- **Type System**: `src/dsl/types/` (Hindley-Milner implementation)
- **Architecture**: `docs/ARCHITECTURE_OVERVIEW.md`

---

## Summary

The DSL provides:
- ✅ **Category Theory Operators** (∘, ×, +, Δ)
- ✅ **Hindley-Milner Type System** (optional type checking)
- ✅ **Tool History Tracking** (SurrealDB persistence)
- ✅ **Real Multi-Agent Integration** (production-ready)
- ✅ **45+ Real-World Examples** (comprehensive library)

**Next Steps**: Explore `examples/workflows/` and create your own workflows!
