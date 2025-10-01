# Week 9 Phase 3: LoRA Fine-Tuning Setup - COMPLETE ✅

**Date**: 2025-10-01
**Duration**: ~3 hours (setup)
**Status**: ✅ Setup complete - Ready to start 12-24 hour training run

---

## Executive Summary

Phase 3 setup complete. All infrastructure ready for LoRA fine-tuning of Qwen2.5-Coder-7B on 298 successful interactions. Training expected to take 12-24 hours on CPU (AMD EPYC 9454P, 48C/96T).

### Setup Deliverables ✅

✅ **Training libraries installed**: transformers, peft, datasets, accelerate (in venv)
✅ **Training data prepared**: 298 interactions → instruction format, split 238/29/31
✅ **LoRA training script**: `training/scripts/train_lora.py`
✅ **Data preparation script**: `training/scripts/prepare_training_data.py`
✅ **Documentation**: `training/README.md` with full usage guide

---

## Training Data Summary

**Source**: `data/training/interactions_20251001.jsonl` (302 interactions)
**Filtered**: 298 successful interactions (98.7% of total)

### Splits

| Split | Count | Percentage | Purpose |
|-------|-------|------------|---------|
| **Train** | 238 | 79.9% | LoRA fine-tuning |
| **Validation** | 29 | 9.7% | Early stopping, best model selection |
| **Test** | 31 | 10.4% | Final evaluation (held out) |

### Agent Distribution (Training Set)

```
coder       : 140 examples (58.8%)
tester      :  59 examples (24.8%)
researcher  :  21 examples ( 8.8%)
coordinator :  16 examples ( 6.7%)
reviewer    :   2 examples ( 0.8%)
```

### Data Format

**Input** (Qwen2.5 chat template):
```
<|im_start|>system
You are an expert software engineer specializing in Clean Architecture and SOLID principles...
<|im_end|>
<|im_start|>user
Implement binary search following Clean Code principles
<|im_end|>
<|im_start|>assistant
def binary_search(sorted_list: List[int], target: int) -> int:
    """Search for target in sorted list using binary search..."""
    ...
<|im_end|>
```

---

## LoRA Configuration

**Base Model**: Qwen/Qwen2.5-Coder-7B-Instruct (7.61B parameters)

### LoRA Hyperparameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Rank (r)** | 8 | Good balance: 0.1-1% trainable params |
| **Alpha** | 32 | Typical 4×r scaling |
| **Dropout** | 0.1 | Regularization, prevent overfitting |
| **Target modules** | q_proj, v_proj, k_proj, o_proj | All attention layers |

### Training Hyperparameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Epochs** | 3 | Standard for LoRA |
| **Batch size** | 2 | Conservative for CPU |
| **Gradient accumulation** | 8 | Effective batch = 16 |
| **Learning rate** | 2e-4 | Higher than full FT (LoRA adapters need stronger signal) |
| **Warmup steps** | 50 | Gradual LR increase |
| **Weight decay** | 0.01 | L2 regularization |
| **Max grad norm** | 1.0 | Gradient clipping |
| **Max length** | 2048 | Context window |

### Trainable Parameters

- **Total params**: ~7,610,000,000 (7.61B)
- **LoRA params**: ~7,000,000 (7M, 0.09%)
- **Memory footprint** (training): ~18-20GB RAM estimated
  - Base model (FP32): ~14GB
  - Gradients + optimizer states: ~4-6GB

---

## Training Execution Plan

### Phase 3A: Training Setup (Complete ✅)

**Duration**: 3 hours
**Status**: ✅ Complete

1. ✅ Install HuggingFace transformers + PEFT (venv)
2. ✅ Prepare training data (298 → 238/29/31 split)
3. ✅ Create LoRA training script with monitoring
4. ✅ Document training procedures

### Phase 3B: LoRA Training (Next - 12-24 hours)

**Duration**: 12-24 hours (CPU)
**Status**: Ready to start

**Start training**:
```bash
# Background training with logging
nohup venv/bin/python3 training/scripts/train_lora.py \
  > training/logs/training_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Save PID for monitoring
echo $! > training/training.pid
```

**Monitor progress**:
```bash
# Check log output
tail -f training/logs/training_*.log

# Check CPU usage
htop  # Look for python3 using ~100% across multiple cores

# Check checkpoints
ls -lh training/models/qwen2.5-coder-7b-lora/checkpoint-*/
```

### Phase 3C: Evaluation (After Training - 2-4 hours)

1. Evaluate on test set (31 examples)
2. Compare with baseline (20.1s avg, 98.7% success)
3. Calculate metrics: speed, quality, memory

### Phase 3D: Decision (After Evaluation - 1 hour)

**Deploy** if:
- Speed: <12s avg latency (40% improvement)
- Quality: ≥98% success rate (maintain baseline)
- Memory: ≤10GB RAM

**Iterate** if:
- Speed >12s OR quality <98%
- Try: more epochs, different LR, more data

**Abort** if:
- No improvement on both metrics

---

## Expected Training Timeline

### CPU Training (AMD EPYC 9454P, 48C/96T)

| Stage | Duration | Details |
|-------|----------|---------|
| **Initial setup** | 5-10 min | Download model (7GB), load into memory |
| **Data loading** | 1-2 min | Tokenize 238 training examples |
| **Epoch 1** | 4-8 hours | ~80 steps (238 / 3 grad accum) |
| **Epoch 2** | 4-8 hours | ~80 steps |
| **Epoch 3** | 4-8 hours | ~80 steps |
| **Save final model** | 1-2 min | Write adapters to disk |
| **Total** | **12-24 hours** | ~240 total training steps |

**Steps per epoch**: 238 examples / (2 batch × 8 accum) = ~15 steps
**Total steps**: 15 steps × 3 epochs = **45 steps** (correction from estimate)

**Checkpoints saved**: Every 50 steps → 1 checkpoint after 45 steps (end of training)

---

## Infrastructure Created

### Files

```
training/
├── README.md                           (✅ Complete documentation)
├── data/
│   ├── train.jsonl                     (✅ 238 examples)
│   ├── val.jsonl                       (✅ 29 examples)
│   ├── test.jsonl                      (✅ 31 examples)
│   └── metadata.json                   (✅ Dataset info)
├── scripts/
│   ├── prepare_training_data.py        (✅ Data preparation)
│   └── train_lora.py                   (✅ LoRA training)
├── models/                             (Created during training)
│   └── qwen2.5-coder-7b-lora/
│       ├── checkpoint-50/              (If 50 steps reached)
│       ├── final_model/                (After training)
│       ├── logs/                       (Training metrics)
│       └── training_config.json        (Config snapshot)
└── logs/                               (✅ Created for output logs)
```

### Scripts Created

1. **`training/scripts/prepare_training_data.py`**
   - Loads 302 interactions from `data/training/interactions_20251001.jsonl`
   - Filters to 298 successful
   - Converts to Qwen2.5 chat format with agent-specific system prompts
   - Splits 238/29/31 (train/val/test)
   - Outputs JSONL files

2. **`training/scripts/train_lora.py`**
   - Loads Qwen2.5-Coder-7B base model
   - Applies LoRA adapters (r=8, alpha=32)
   - Trains on 238 examples for 3 epochs
   - Saves checkpoints every 50 steps
   - Uses validation set for early stopping
   - Outputs trained adapters

---

## Success Criteria Reminder

**Primary Goals** (from Phase 2):

1. ✅ **Speed**: <12s avg latency (vs 20.1s baseline, 40% reduction)
2. ✅ **Quality**: ≥98% success rate (maintain 98.7% baseline)
3. ✅ **Efficiency**: ≤10GB RAM (vs 32.5GB for 30B model)

**Stretch Goals**:

4. 🎯 **Speed**: <10s avg latency (50% reduction)
5. 🎯 **Quality**: 99%+ success rate (+1% improvement)

---

## Risk Assessment

### Risk 1: Training Takes >24 Hours

**Probability**: Medium (30%)
**Mitigation**:
- Accept 48-hour training time
- OR rent cloud GPU ($50-100 for A100)

### Risk 2: Quality Degrades <98%

**Probability**: Low (20%)
**Mitigation**:
- Check validation loss curve
- Reduce learning rate to 1e-4
- Train for 5 epochs
- Collect more data (Phase 1 again)

### Risk 3: Speed Not Improved

**Probability**: Very Low (10%)
**Rationale**: 7B model inherently faster than 30B
**Mitigation**: Use base Qwen2.5-Coder-7B without fine-tuning

---

## Next Steps

### Immediate (Now)

1. **Start training run**:
   ```bash
   cd /home/ui-cli_jake/unified-intelligence-cli

   nohup venv/bin/python3 training/scripts/train_lora.py \
     > training/logs/training_$(date +%Y%m%d_%H%M%S).log 2>&1 &

   echo $! > training/training.pid
   ```

2. **Monitor initial startup** (first 10 minutes):
   ```bash
   tail -f training/logs/training_*.log
   # Should see: model loading → tokenization → training starts
   ```

3. **Check after 1 hour**:
   - Training should be at ~3-5 steps
   - CPU usage should be high (>80% across cores)
   - Memory usage should be stable (~18-20GB)

### After Training (12-24 hours)

1. **Verify completion**:
   ```bash
   ls -lh training/models/qwen2.5-coder-7b-lora/final_model/
   # Should see: adapter_config.json, adapter_model.safetensors
   ```

2. **Create evaluation script** (TODO):
   ```bash
   venv/bin/python3 training/scripts/evaluate_lora.py \
     --model training/models/qwen2.5-coder-7b-lora/final_model \
     --test-data training/data/test.jsonl
   ```

3. **Compare metrics**:
   - Baseline: 98.7% success, 20.1s avg
   - Fine-tuned: ?% success, ?s avg

4. **Decision**: Deploy, iterate, or abort

---

## Dependencies Installed

```
# Core training libraries (in venv)
transformers==4.56.2        # HuggingFace Transformers
peft==0.17.1                # Parameter-Efficient Fine-Tuning (LoRA)
datasets==4.1.1             # Dataset loading and processing
accelerate==1.10.1          # Distributed training utilities
torch==2.8.0                # PyTorch backend
bitsandbytes==0.48.0        # Quantization utilities
sentencepiece==0.2.1        # Tokenization for Qwen models
protobuf==6.32.1            # Data serialization

# Supporting libraries
numpy==2.3.3
pandas==2.3.3
safetensors==0.6.2
tokenizers==0.22.1
```

---

## Monitoring Commands

### During Training

```bash
# Follow training log
tail -f training/logs/training_*.log

# Check process status
ps aux | grep train_lora.py

# Check CPU usage
htop

# Check memory usage
free -h

# Check disk usage (model checkpoints)
du -sh training/models/*

# Kill training (if needed)
kill $(cat training/training.pid)
```

### After Training

```bash
# Check final model size
du -sh training/models/qwen2.5-coder-7b-lora/final_model/

# List checkpoints
ls -lh training/models/qwen2.5-coder-7b-lora/checkpoint-*/

# View training logs summary
grep -i "train\|eval\|loss" training/logs/training_*.log | tail -50
```

---

## Troubleshooting

### Issue: "CUDA out of memory"

**Unlikely on CPU**, but if it happens:
- Reduce batch size: `--batch-size 1`
- Reduce max length: Edit `train_lora.py`, set `max_length=1024`

### Issue: "Training too slow"

**Expected**: 12-24 hours is normal for CPU
**Options**:
1. Accept slow training
2. Rent cloud GPU (A100, $50-100 total)
3. Reduce epochs: `--epochs 2`

### Issue: "Model not loading"

**Check**:
- Internet connection (model downloads from HuggingFace)
- Disk space (model is ~7GB)
- HuggingFace Hub access (may need token for some models)

---

## References

- [Phase 2 Baseline Results](./PHASE_2_BASELINE_EVALUATION_COMPLETE.md)
- [Training Pipeline Strategy](./MODEL_TRAINING_STRATEGY_PIPELINE_ULTRATHINK.md)
- [Training README](../training/README.md)
- [Qwen2.5-Coder Documentation](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct)
- [PEFT Documentation](https://huggingface.co/docs/peft)

---

## Phase 3 Status

**Setup**: ✅ Complete (3 hours)
**Training**: ⏳ Ready to start (12-24 hours)
**Evaluation**: ⏳ Pending (2-4 hours)
**Decision**: ⏳ Pending (1 hour)

**Total Timeline**: 3 + 12-24 + 2-4 + 1 = **18-32 hours** (setup to decision)

---

**Document Version**: 1.0
**Date**: 2025-10-01
**Phase**: Week 9 Phase 3 - LoRA Fine-Tuning Setup
**Status**: ✅ Setup complete, ready to start training
