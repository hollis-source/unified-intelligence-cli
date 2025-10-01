# LoRA Fine-Tuning - Phase 3

**Status**: Setup complete, ready to train
**Target**: Qwen2.5-Coder-7B fine-tuned on 298 interactions
**Goal**: <12s avg latency, ≥98% success rate, <10GB RAM

---

## Directory Structure

```
training/
├── README.md (this file)
├── data/
│   ├── train.jsonl          (238 examples, 80%)
│   ├── val.jsonl            (29 examples, 10%)
│   ├── test.jsonl           (31 examples, 10%)
│   └── metadata.json        (dataset info)
├── models/
│   └── qwen2.5-coder-7b-lora/  (output from training)
│       ├── checkpoint-*/
│       ├── final_model/
│       ├── logs/
│       └── training_config.json
├── scripts/
│   ├── prepare_training_data.py  ✅ Complete
│   ├── train_lora.py             ✅ Complete
│   ├── evaluate_lora.py          (TODO)
│   └── convert_to_gguf.py        (TODO)
└── configs/
    └── lora_config.json
```

---

## Training Configuration

**Model**: Qwen/Qwen2.5-Coder-7B-Instruct

**LoRA Parameters**:
- Rank (r): 8
- Alpha: 32
- Dropout: 0.1
- Target modules: q_proj, v_proj, k_proj, o_proj (all attention layers)

**Training Parameters**:
- Epochs: 3
- Batch size: 2 (per device)
- Gradient accumulation: 8 (effective batch = 16)
- Learning rate: 2e-4
- Weight decay: 0.01
- Max sequence length: 2048 tokens

**Hardware**:
- CPU-only training (AMD EPYC 9454P, 48C/96T)
- FP32 precision
- Expected duration: 12-24 hours

---

## Quick Start

### 1. Prepare Data (✅ Complete)

```bash
python3 training/scripts/prepare_training_data.py
```

Output:
- `training/data/train.jsonl` (238 examples)
- `training/data/val.jsonl` (29 examples)
- `training/data/test.jsonl` (31 examples)

### 2. Start Training

```bash
# Standard training (3 epochs, batch=2)
venv/bin/python3 training/scripts/train_lora.py

# Custom configuration
venv/bin/python3 training/scripts/train_lora.py \
  --epochs 5 \
  --batch-size 4 \
  --output-dir training/models/qwen2.5-coder-7b-lora-v2

# Background training (recommended for 12-24 hour run)
nohup venv/bin/python3 training/scripts/train_lora.py \
  > training/logs/training_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Monitor progress
tail -f training/logs/training_*.log
```

### 3. Evaluate Model

```bash
venv/bin/python3 training/scripts/evaluate_lora.py \
  --model training/models/qwen2.5-coder-7b-lora/final_model \
  --test-data training/data/test.jsonl \
  --output results/lora_evaluation.json
```

### 4. Convert to GGUF (for llama.cpp)

```bash
venv/bin/python3 training/scripts/convert_to_gguf.py \
  --model training/models/qwen2.5-coder-7b-lora/final_model \
  --output models/qwen2.5-coder-7b-lora.gguf
```

---

## Training Progress

### Expected Timeline

| Phase | Duration | Checkpoint |
|-------|----------|------------|
| Model download | 5-10 min | First run only |
| Data loading | 1-2 min | Each run |
| Epoch 1 | 4-8 hours | checkpoint-50, 100, 150 |
| Epoch 2 | 4-8 hours | checkpoint-200, 250, 300 |
| Epoch 3 | 4-8 hours | checkpoint-350, 400, 450 |
| **Total** | **12-24 hours** | final_model |

### Monitoring

**Check training logs**:
```bash
tail -f training/models/qwen2.5-coder-7b-lora/logs/events.out.tfevents.*
```

**Check checkpoints**:
```bash
ls -lh training/models/qwen2.5-coder-7b-lora/checkpoint-*/
```

**Monitor CPU usage**:
```bash
htop
# Look for python3 process using ~100% CPU across multiple cores
```

---

## Data Format

### Input (Collected Interactions)

```json
{
  "task": {"description": "Implement binary search..."},
  "agent": {"role": "coder"},
  "execution": {"output": "def binary_search(...)..."}
}
```

### Output (Training Format)

```
<|im_start|>system
You are an expert software engineer specializing in Clean Architecture...
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

## Success Criteria

**Phase 3 will be successful if**:

1. ✅ **Speed**: <12s avg latency (40% reduction from 20.1s baseline)
2. ✅ **Quality**: ≥98% success rate (maintain baseline)
3. ✅ **Efficiency**: ≤10GB RAM (3x reduction from 30B model)

**Stretch goals**:

4. 🎯 Speed: <10s avg latency (50% reduction)
5. 🎯 Quality: 99%+ success rate (+1% improvement)

---

## Troubleshooting

### Training hangs or crashes

**Issue**: Out of memory
**Solution**: Reduce batch size to 1, increase gradient accumulation

```bash
venv/bin/python3 training/scripts/train_lora.py --batch-size 1
```

### Training too slow

**Issue**: CPU training taking >24 hours
**Options**:
1. **Accept slower training**: Let it run for 48 hours
2. **Use cloud GPU**: Rent A100 for $1-3/hour (~$30-90 total)
3. **Reduce epochs**: Train for 1-2 epochs instead of 3

### Model quality degraded

**Issue**: Test accuracy < 98%
**Solution**:
1. Check validation loss curve (should decrease)
2. Reduce learning rate: `--lr 1e-4`
3. Increase epochs to 5
4. Collect more training data

---

## Next Steps After Training

1. **Evaluate on test set** (31 examples)
   - Success rate
   - Average latency
   - Quality comparison

2. **Compare with baseline**
   - Baseline: 98.7% success, 20.1s avg
   - Fine-tuned: ? success, ? avg

3. **Convert to GGUF** for llama.cpp deployment

4. **A/B test in production** (if successful)
   - 50% baseline, 50% fine-tuned
   - Monitor for 1 week
   - Roll out to 100%

---

## References

- [Qwen2.5-Coder Model Card](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct)
- [PEFT Documentation](https://huggingface.co/docs/peft)
- [LoRA Paper](https://arxiv.org/abs/2106.09685)
- [Training Pipeline Strategy](../docs/MODEL_TRAINING_STRATEGY_PIPELINE_ULTRATHINK.md)
- [Phase 2 Baseline Results](../docs/PHASE_2_BASELINE_EVALUATION_COMPLETE.md)

---

**Status**: Ready to train
**Created**: 2025-10-01
**Phase**: Week 9 Phase 3 - LoRA Fine-Tuning
