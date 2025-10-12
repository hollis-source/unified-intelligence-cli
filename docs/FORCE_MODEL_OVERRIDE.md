# FORCE_MODEL Environment Variable Override

## Purpose

Temporarily bypass all model routing logic to force selection of a specific LLM provider. This is useful for:
- Development and debugging
- Model-specific optimization work
- Benchmarking specific models
- Testing without interference from intelligent routing

## Usage

### Basic Usage

```bash
# Force qwen3_hf_inference for all requests
export FORCE_MODEL=qwen3_hf_inference
python3 -m src.main --task "your task here"
```

### One-time Override

```bash
# Force qwen3 for a single command
FORCE_MODEL=qwen3_hf_inference python3 -m src.main --task "your task"
```

### Disable Override (Restore Normal Routing)

```bash
# Unset the variable to restore intelligent routing
unset FORCE_MODEL
```

## Available Models

- `qwen3_hf_inference` - Qwen3-8B via HuggingFace Inference API (1.2s latency, 100% success rate)
- `qwen3_zerogpu` - Qwen3-8B via ZeroGPU (13.8s latency)
- `qwen3_next_80b_thinking` - Qwen3-Next-80B thinking model (48s latency, superior reasoning)
- `tongyi-local` - Tongyi-DeepResearch-30B local inference (20.1s avg)
- `grok` - Grok-2-Latest API (5s latency, tool support)

## What Gets Bypassed

When `FORCE_MODEL` is set, the following routing logic is disabled:

1. **ULTRATHINK routing** - Even tasks with "ultrathink" in the prompt won't route to Grok
2. **Intelligent model selection** - Criteria-based scoring (speed, quality, cost, privacy) is bypassed
3. **Fallback chain** - Only the forced model is used, no fallback to other models
4. **Task analysis** - Task description keywords (offline, fast, accurate, etc.) are ignored

## Implementation Details

### Location

- **File**: `src/adapters/llm/model_orchestrator.py`
- **Lines**: 117-157 (environment variable check and routing logic)

### Code Structure

```python
forced_model = os.getenv("FORCE_MODEL")

if forced_model:
    logger.warning(
        f"FORCE_MODEL={forced_model} - Bypassing all routing logic "
        f"(ULTRATHINK, criteria, selection, fallback disabled)"
    )
    primary_model = forced_model
    fallback_chain = [primary_model]
else:
    # Normal routing logic (ULTRATHINK, criteria-based selection, fallback)
    ...
```

### Testing

Tests are located at `tests/unit/test_model_orchestrator_force_qwen.py` and verify:
- FORCE_MODEL bypasses normal routing
- ULTRATHINK routing is ignored when forced
- No fallback to other models occurs
- Only the specified model is requested

## Use Cases

### 1. Qwen3 Optimization Work

```bash
# Force qwen3 to optimize batching/caching without interference
export FORCE_MODEL=qwen3_hf_inference
python3 -m src.main --task "optimize inference pipeline"
```

**Why**: When optimizing a specific model, you need consistent routing to that model. Otherwise, the intelligent router might select grok or other models based on task characteristics.

### 2. Model-Specific Benchmarking

```bash
# Benchmark qwen3_zerogpu performance
FORCE_MODEL=qwen3_zerogpu python3 scripts/benchmark_model.py
```

### 3. Local-Only Development

```bash
# Force local model for offline work
export FORCE_MODEL=tongyi-local
```

### 4. Debug Specific Model Issues

```bash
# Reproduce issue with grok
FORCE_MODEL=grok python3 -m src.main --task "failing task"
```

## Architecture Compliance

### Clean Architecture

- **OCP (Open-Closed Principle)**: Configuration-based override, no code modification required
- **DIP (Dependency Inversion)**: Still uses ITextGenerator abstraction
- **SRP (Single Responsibility)**: ModelOrchestrator maintains single responsibility (orchestration)

### Reversibility

The override is completely reversible:
1. Unset `FORCE_MODEL` → Normal routing restored
2. No code changes required
3. No persistent state changes
4. Original routing logic preserved intact

## Migration from Hardcoded Override

### Before (Hardcoded)

```python
# TEMP DEV OVERRIDE: Force-select Qwen3 HF Inference
primary_model = "qwen3_hf_inference"
fallback_chain = [primary_model]
```

**Issues**:
- Requires code changes to re-enable routing
- Not toggleable without editing code
- Violates OCP (modification over configuration)

### After (Environment Variable)

```bash
# Toggleable via environment, no code changes
export FORCE_MODEL=qwen3_hf_inference
```

**Benefits**:
- Toggle via environment variable
- No code modifications needed
- Clean Architecture compliant
- Easy to enable/disable for different tasks

## Logging

When `FORCE_MODEL` is set, you'll see:

```
WARNING:src.adapters.llm.model_orchestrator:FORCE_MODEL=qwen3_hf_inference - Bypassing all routing logic (ULTRATHINK, criteria, selection, fallback disabled)
INFO:src.adapters.llm.model_orchestrator:Selected model: qwen3_hf_inference, fallback chain: ['qwen3_hf_inference']
```

This confirms the override is active and normal routing is bypassed.

## Warning

**Remember to unset `FORCE_MODEL` after development work** to restore intelligent routing in production:

```bash
unset FORCE_MODEL
```

Leaving it set permanently defeats the purpose of the intelligent routing system.
