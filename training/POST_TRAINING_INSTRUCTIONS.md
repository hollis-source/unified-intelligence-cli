# Post-Training Pipeline Instructions

## Overview

When LoRA training completes, run the automated pipeline to:
1. ✅ Merge LoRA adapters into base model
2. ✅ Convert to GGUF format (f16)
3. ✅ Quantize to Q4_K_M (~4.5GB, optimal for CPU)
4. ✅ Evaluate on 31-example test set
5. ✅ Generate deploy/iterate/abort recommendation

**Estimated time**: 1-2 hours for complete pipeline

---

## Quick Start (One Command)

```bash
# Wait for training to complete, then run:
python3 training/scripts/post_training_pipeline.py \
    --lora training/models/qwen3-8b-instruct-lora/final_model
```

**Expected output**: Deploy/iterate/abort recommendation with metrics

---

## Individual Scripts (Step-by-Step)

If you prefer to run steps individually:

### Step 1: Merge LoRA Adapters (10-15 min)
```bash
python3 training/scripts/merge_lora_adapters.py \
    --lora training/models/qwen3-8b-instruct-lora/final_model \
    --output training/models/qwen3-8b-merged
```

**Output**: `training/models/qwen3-8b-merged/` (~16GB)

### Step 2: Convert to GGUF f16 (30-60 min)
```bash
python3 training/scripts/convert_to_gguf.py \
    --model training/models/qwen3-8b-merged \
    --output training/models/qwen3-8b-merged-f16.gguf
```

**Output**: `training/models/qwen3-8b-merged-f16.gguf` (~16GB)

### Step 3: Quantize to Q4_K_M (15-30 min)
```bash
python3 training/scripts/quantize_model.py \
    --input training/models/qwen3-8b-merged-f16.gguf \
    --output training/models/qwen3-8b-merged-q4-k-m.gguf \
    --type Q4_K_M
```

**Output**: `training/models/qwen3-8b-merged-q4-k-m.gguf` (~4.5GB)

### Step 4: Evaluate on Test Set (15-30 min)
```bash
python3 training/scripts/evaluate_qwen3.py \
    --model training/models/qwen3-8b-merged \
    --test-data training/data/test.jsonl \
    --merged \
    --output training/evaluation_results.json
```

**Output**:
- `training/evaluation_results.json` (detailed metrics)
- Console: Deploy/iterate/abort recommendation

---

## Target Metrics

From Week 9 Phase 2 baseline:

| Metric | Baseline (Tongyi-30B) | Target (Qwen3-8B Fine-Tuned) | Status |
|--------|----------------------|------------------------------|--------|
| Success Rate | 98.7% | ≥98% | Must maintain quality |
| Avg Latency | 20.1s | <12s | Must improve speed |

**Deployment criteria**: Both targets must be met

---

## Troubleshooting

### Pipeline fails at merge step
- **Check**: LoRA checkpoint exists at specified path
- **Check**: Base model "Qwen/Qwen3-8B" accessible (internet required)
- **Fix**: Ensure virtual environment active with dependencies installed

### GGUF conversion fails
- **Check**: llama.cpp installed at `~/llama.cpp/convert_hf_to_gguf.py`
- **Fix**:
  ```bash
  cd ~
  git clone https://github.com/ggerganov/llama.cpp
  cd llama.cpp && make
  ```

### Quantization fails
- **Check**: llama.cpp binary built at `~/llama.cpp/llama-quantize`
- **Fix**:
  ```bash
  cd ~/llama.cpp && make
  ```

### Evaluation fails with low scores
- **Expected**: Fine-tuning on 298 examples may not be sufficient
- **Options**:
  - Iterate: Collect more training data (500-1000 examples)
  - Iterate: Increase training epochs (5-10 instead of 3)
  - Abort: Fall back to baseline Tongyi-30B if targets not met

---

## Next Steps After Pipeline

### If recommendation is "✅ DEPLOY"
Both targets met! Deploy the Q4_K_M model:
```bash
# Copy to deployment location
cp training/models/qwen3-8b-merged-q4-k-m.gguf /data/ai-models/

# Update unified-intelligence-cli config to use new model
# Test with real queries
```

### If recommendation is "⚠️ ITERATE"
One target met, one failed. Options:
- **If speed good, quality needs work**: More training data or epochs
- **If quality good, speed needs work**: Try Q5_K_M quantization instead

### If recommendation is "❌ ABORT"
Neither target met. Options:
- Fall back to baseline (Tongyi-30B on GPU)
- Try different base model (Qwen2.5-7B-Instruct)
- Collect significantly more training data (1000+ examples)

---

## Files Created by Pipeline

```
training/models/
├── qwen3-8b-merged/              # Merged HF model (~16GB)
│   ├── config.json
│   ├── model.safetensors
│   └── tokenizer files
├── qwen3-8b-merged-f16.gguf      # GGUF f16 (~16GB)
└── qwen3-8b-merged-q4-k-m.gguf   # Quantized Q4_K_M (~4.5GB) ← DEPLOY THIS

training/
├── evaluation_results.json       # Detailed metrics
└── pipeline_results.json         # Pipeline execution log
```

---

## Monitoring Training Progress

Check if training is still running:
```bash
ps aux | grep train_lora.py
```

Monitor log file:
```bash
tail -f training/logs/training_qwen3_20251001_171405.log
```

Check GPU/CPU usage:
```bash
htop
```

**Expected duration**: 6-8 hours (24 steps total, ~15-20 min per step on CPU)

**When training completes**, you'll see:
- Log file shows "Training complete!" message
- Checkpoint saved at `training/models/qwen3-8b-instruct-lora/final_model/`
- Process exits

Then run the post-training pipeline immediately.

---

## Quick Reference

| Task | Command | Time |
|------|---------|------|
| Full pipeline | `python3 training/scripts/post_training_pipeline.py --lora <path>` | 1-2h |
| Merge only | `python3 training/scripts/merge_lora_adapters.py --lora <path>` | 10-15m |
| Convert only | `python3 training/scripts/convert_to_gguf.py --model <path>` | 30-60m |
| Quantize only | `python3 training/scripts/quantize_model.py --input <path>` | 15-30m |
| Evaluate only | `python3 training/scripts/evaluate_qwen3.py --model <path> --merged` | 15-30m |

---

**Documentation generated**: 2025-10-01
**Week 9 Phase 4**: LoRA fine-tuning and GGUF deployment pipeline
