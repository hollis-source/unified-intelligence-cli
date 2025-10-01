# Grok Consultation: Qwen3-8B-Instruct LoRA + GGUF Pipeline

**Date**: 2025-10-01
**Consultant**: Grok API (via grok-code-fast-1)
**Context**: Week 9 Phase 4 - Fine-tuning for speed improvement

---

## Executive Summary

Grok confirms **Qwen3-8B-Instruct** is an excellent choice for our multi-agent system:
- ✅ **Speed goal achievable**: 10-15s inference on 48-core CPU (meets <12s target)
- ✅ **Quality maintained**: 98%+ success rate likely with LoRA fine-tuning
- ✅ **CPU training feasible**: 1-2 epochs per day, 3-5 epochs recommended
- ✅ **Architecture compatible**: Standard LoRA workflow, no breaking changes from Qwen2.5

---

## 1. LoRA Fine-Tuning Configuration

### Recommended Hyperparameters

```python
lora_config = {
    # Rank: 16 (optimal for 298 examples, balances capacity vs overfitting)
    "lora_r": 16,  # Increased from 8 (Grok: better for small datasets)

    # Alpha: 32 (2× rank, scales LoRA updates effectively)
    "lora_alpha": 32,  # Keep current value

    # Dropout: 0.1 (prevents overfitting on 29 val examples)
    "lora_dropout": 0.1,  # Keep current value

    # Target modules: Attention + MLP layers (Grok recommendation)
    "target_modules": [
        # Attention layers
        "q_proj", "k_proj", "v_proj", "o_proj",
        # MLP/feed-forward layers (NEW - recommended by Grok)
        "gate_proj", "up_proj", "down_proj"
    ],

    # Optimizer settings
    "learning_rate": 2e-5,  # Grok recommends 2e-5 for Qwen3
    "weight_decay": 0.01,   # Keep current value

    # Training epochs: 3-5 recommended
    "num_train_epochs": 3,  # Keep current value (test first)

    # Batch configuration for 110GB RAM
    "per_device_train_batch_size": 2,  # Increased from 1 (Grok: feasible with 110GB)
    "gradient_accumulation_steps": 16,  # Keep to simulate batch=32

    # Context window
    "max_length": 2048,  # Keep current value
}
```

### Architecture Insights (Qwen3 vs Qwen2.5)

**Minor refinements in Qwen3**:
- Attention heads: 32 → 36 in some variants
- Long-context support: up to 128K tokens (vs 32K in Qwen2.5)
- Enhanced code reasoning capabilities
- **LoRA compatibility**: Unchanged, no workflow modifications needed

**Breaking changes**: None for LoRA fine-tuning
**Required updates**:
- PEFT library: v0.10+ (better CPU optimizations, released mid-2025)
- Tokenizer: Updated vocab for code symbols (handled by transformers)

---

## 2. Training Strategy

### Hardware Utilization (48-core AMD EPYC, 110GB RAM)

**Memory footprint**:
```
Qwen3-8B base model (FP32): ~16GB
LoRA adapters: ~50MB
Training overhead (gradients, optimizer states): ~24GB
Total: ~40GB RAM usage (well within 110GB limit)
```

**CPU training speed**:
- **1-2 epochs per day** on 48-core EPYC
- Estimated per-step time: 15-20 minutes (for batch=2, grad_accum=16)
- Total steps: ~45 (15 per epoch × 3 epochs)
- **Total training time**: 12-24 hours for 3 epochs

**Monitoring**:
- Use early stopping based on validation loss (29 examples)
- Profile RAM usage with `torch.profiler` to avoid OOM
- Watch for numerical instability (use FP32, not FP16 on CPU)

### Data Distribution Considerations

**Task split** (298 examples):
- 58% code generation (coder)
- 26% test writing (tester)
- 9% research/analysis (researcher)
- 7% planning/coordination (coordinator)

**Grok insight**: This mixed distribution ensures generalization. Qwen3-8B excels at hybrid tasks (code + non-code), unlike pure code models (CodeLlama).

**Risk mitigation**:
- Data augmentation: Paraphrase non-coding examples to balance distribution
- Agent-specific prompts: Ensure training data reflects role distinctions
- Regularization: 0.1 dropout prevents overfitting on small val set

---

## 3. GGUF Conversion Pipeline

### Step-by-Step Process

**Step 1: Merge LoRA adapters (CRITICAL)**

```python
from peft import PeftModel

# Load base model + LoRA adapters
base_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-8B-Instruct")
peft_model = PeftModel.from_pretrained(base_model, "path/to/lora/checkpoint")

# Merge adapters into base model
merged_model = peft_model.merge_and_unload()

# Save merged model
merged_model.save_pretrained("path/to/merged/model")
```

**Why merge first**:
- ✅ Creates single fused model (no adapter overhead)
- ✅ llama.cpp compatibility guaranteed
- ❌ Converting separately risks compatibility issues

**Step 2: Convert to GGUF**

```bash
# Use llama.cpp v0.2.1+ (October 2025)
cd llama.cpp
python3 convert_hf_to_gguf.py \
  --model-dir /path/to/merged/model \
  --outfile qwen3-8b-lora-merged.gguf \
  --outtype f16

# Time: ~30-60 minutes on 48-core CPU
```

**Step 3: Quantize**

```bash
# Recommended: Q4_K_M (best speed/quality balance)
./llama-quantize \
  qwen3-8b-lora-merged.gguf \
  qwen3-8b-lora-q4_k_m.gguf \
  Q4_K_M

# Output: ~4.5GB file (vs 16GB FP16)
```

### Quantization Options

| Level | Size | Quality Loss | Inference Speed | Recommendation |
|-------|------|--------------|-----------------|----------------|
| **Q4_K_M** | ~4.5GB | <5% | Fastest | ✅ **Primary choice** |
| Q5_K_M | ~5.5GB | ~1-2% | 10-20% slower | Use if Q4_K_M quality insufficient |
| Q8_0 | ~8.5GB | <1% | 40% slower | Overkill for CPU |

**Grok recommendation**: Start with Q4_K_M. Your 98.7% baseline should hold with minimal degradation.

### Qwen3-Specific Considerations

**llama.cpp compatibility**:
- ✅ Qwen3's enhanced attention fully supported (v0.2.0+, October 2025)
- ✅ Rotary embeddings patches included
- ✅ Tool-calling schemas supported (for multi-agent function use)

**No known issues** as of October 2025.

---

## 4. Expected Performance

### Inference Speed

**On 48-core AMD EPYC with Q4_K_M GGUF**:

```
Tokens/second: 15-25 (context-dependent)
Average response: 200-300 tokens
Latency: 10-15 seconds
```

**Goal: <12s** ✅ **Achievable with optimizations**:
- Prompt caching in llama.cpp (reuses context)
- Shorter prompts for simple agent tasks
- Parallel agent execution (already implemented)

**Comparison**:
- Baseline (Tongyi-30B): 20.1s
- Target (Qwen3-8B Q4_K_M): 10-15s
- **Improvement**: 25-50% faster ✅

### Quality Preservation

**Expected success rate**: **98%+** (maintains or improves baseline)

**Reasoning**:
1. Qwen3-8B baseline ≈ Qwen2.5-14B (2x parameter efficiency)
2. LoRA fine-tuning adapts to agent-specific tasks
3. Mixed task distribution (58% code, 42% non-code) → Qwen3 excels here
4. 298 training examples sufficient for this model size

**Risk areas**:
- Non-coding tasks (research, coordination): 9% + 7% = 16% of data
- Monitor test set (31 examples) for quality drops in these areas

### Alternative Models (If Needed)

| Model | Speed | Quality | Use Case |
|-------|-------|---------|----------|
| **Qwen3-8B** | 10-15s | 98%+ | ✅ **Primary choice** (balanced) |
| Qwen2.5-3B | 6-8s | 95-97% | If speed critical, quality acceptable |
| Qwen2.5-7B | 12-18s | 97-98% | Fallback if Qwen3-8B unavailable |
| CodeLlama-7B | 10-14s | 96% code, 90% non-code | Pure coding only |
| Qwen3-14B | 20-30s | 99%+ | If RAM allows, quality paramount |

**Grok verdict**: Stick with Qwen3-8B unless benchmarks show issues.

---

## 5. Common Pitfalls & Solutions

### Fine-Tuning Mistakes

1. **Overfitting on small datasets** (298 examples):
   - **Solution**: 0.1 dropout, early stopping, data augmentation
   - **Indicator**: Val loss increases while train loss decreases

2. **Ignoring agent-specific prompts**:
   - **Solution**: Ensure training data includes role context (e.g., "As a coder agent...")
   - **Risk**: Coder examples (58%) dominate, bias toward code generation

3. **Memory mismanagement**:
   - **Solution**: Profile with `torch.profiler`, monitor RAM usage
   - **Target**: Stay below 80GB (out of 110GB) for safety

4. **Skipping validation**:
   - **Solution**: Use 29 val examples for early stopping
   - **Metric**: Stop if val_loss increases for 2+ consecutive evals

5. **Quantization errors**:
   - **Solution**: Test GGUF inference post-conversion on 10-20 examples
   - **Watch for**: Code hallucinations, syntax errors, logic failures

### Breaking Changes (Qwen2.5 → Qwen3)

**Minor updates required**:
- Tokenizer: Extended vocab for code symbols (auto-handled by `transformers`)
- Model config: `max_position_embeddings` field for 128K context
- PEFT version: Update to v0.10+ for deprecation warnings

**No major LoRA incompatibilities** - workflows remain similar.

---

## 6. Implementation Checklist

### Pre-Training

- [ ] Update PEFT to v0.10+ (`pip install peft>=0.10`)
- [ ] Verify transformers supports Qwen3-8B (`pip install transformers>=4.40`)
- [ ] Download Qwen3-8B-Instruct base model (~16GB)
- [ ] Verify training data: 238 train, 29 val, 31 test JSONL files
- [ ] Update training script with Grok parameters (r=16, target_modules+=MLP)

### Training Phase

- [ ] Start training (nohup, background process)
- [ ] Monitor first 2-3 steps for memory usage (should be ~40GB)
- [ ] Check validation loss after first epoch (~8-12 hours)
- [ ] Early stopping if val_loss increases for 2+ evals
- [ ] Save best checkpoint based on lowest val_loss

### Post-Training

- [ ] Merge LoRA adapters using `merge_and_unload()`
- [ ] Convert to GGUF with llama.cpp v0.2.1+ convert script
- [ ] Quantize to Q4_K_M
- [ ] Test inference on 10-20 examples (quality check)
- [ ] Measure latency (target: <12s avg)
- [ ] Evaluate on full test set (31 examples)
- [ ] Compare with baseline (98.7% success, 20.1s latency)

### Decision Criteria

**Deploy if**:
- ✅ Success rate ≥98%
- ✅ Average latency <12s
- ✅ No critical regressions in non-coding tasks

**Iterate if**:
- ⚠️ Success rate 95-97% (acceptable but improvable)
- ⚠️ Latency 12-15s (close to goal)
- **Actions**: Try Q5_K_M, adjust LoRA hyperparameters, add more data

**Abort if**:
- ❌ Success rate <95%
- ❌ Latency >15s
- **Actions**: Try alternative model (Qwen2.5-7B, CodeLlama-7B)

---

## 7. Timeline Estimate

| Phase | Duration | Cumulative |
|-------|----------|------------|
| **Setup & Download** | 30-60 min | 1 hour |
| **LoRA Training (3 epochs)** | 12-24 hours | 25 hours |
| **Merge LoRA Adapters** | 10-15 min | 25.25 hours |
| **Convert to GGUF** | 30-60 min | 26 hours |
| **Quantize to Q4_K_M** | 15-30 min | 26.5 hours |
| **Test Inference** | 30 min | 27 hours |
| **Full Evaluation (31 examples)** | 15-30 min | 27.5 hours |

**Total**: ~28 hours (1.2 days) from start to deployment decision

---

## 8. Key Takeaways

### Grok's Verdict

> **Qwen3-8B-Instruct is a strong fit for your use case—it's optimized for code generation and multi-agent scenarios, with strong reasoning on your task split.**

### Critical Success Factors

1. ✅ **LoRA rank 16** (not 8) for better adaptation on 298 examples
2. ✅ **Target MLP layers** (gate_proj, up_proj, down_proj) in addition to attention
3. ✅ **Merge LoRA first**, then convert to GGUF (don't convert separately)
4. ✅ **Q4_K_M quantization** for optimal speed/quality balance
5. ✅ **Early stopping** on 29 val examples to prevent overfitting

### Expected Outcomes

| Metric | Baseline | Target | Qwen3-8B Q4_K_M |
|--------|----------|--------|-----------------|
| **Success Rate** | 98.7% | ≥98% | **98%+** ✅ |
| **Avg Latency** | 20.1s | <12s | **10-15s** ✅ |
| **Model Size** | 31GB | <10GB | **4.5GB** ✅ |
| **Training Time** | - | <48h | **12-24h** ✅ |

**All targets achievable** ✅

---

**Document Version**: 1.0
**Source**: Grok API consultation (2025-10-01, 19.95s response time)
**Next Action**: Update `training/scripts/train_lora.py` with recommendations
