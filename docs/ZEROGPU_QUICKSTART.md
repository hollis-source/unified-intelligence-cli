# ZeroGPU Quick Start Guide

**Goal**: Deploy Qwen3-8B Q5_K_M evaluation to HuggingFace ZeroGPU in 5 minutes.

## Why ZeroGPU?

✅ **FREE** with your HF Pro account ($9/mo)
✅ **H200 GPU** (80GB VRAM, fastest available)
✅ **~18 minutes** evaluation time (vs 5 hours on CPU)
✅ **Zero infrastructure** setup
✅ **Shareable** Space for collaboration

## Prerequisites

- ✅ HuggingFace Pro account (you have this)
- ✅ HF CLI: `pip install huggingface_hub`
- ✅ Login: `huggingface-cli login`

## One-Command Deployment

```bash
cd hf_spaces/qwen3-eval
./deploy.sh
```

That's it! The script will:
1. Verify your HF login
2. Create Space (or use existing)
3. Push all files
4. Give you the Space URL

## Manual Deployment (3 steps)

### 1. Create Space

Go to https://huggingface.co/new-space

- **Name**: `qwen3-eval`
- **SDK**: Gradio
- **Hardware**: ZeroGPU (Nvidia H200)
- **Visibility**: Public or Private

### 2. Push Code

```bash
cd hf_spaces/qwen3-eval

git init
git remote add origin https://huggingface.co/spaces/YOUR_USERNAME/qwen3-eval
git add .
git commit -m "Deploy ZeroGPU evaluation"
git push -u origin main
```

### 3. Run Evaluation

1. Go to your Space URL
2. Wait for build (~2-3 min first time)
3. Paste test data from `test_sample.jsonl`
4. Click "🚀 Run Evaluation"
5. Watch results appear in ~18 minutes!

## What's Inside

```
hf_spaces/qwen3-eval/
├── app.py              # Gradio app with @spaces.GPU
├── requirements.txt    # Dependencies
├── README.md           # Space description
├── DEPLOYMENT.md       # Detailed guide
├── deploy.sh           # Automated deployment
└── test_sample.jsonl   # 31 test examples
```

## Key Features

**Batched Processing**: Evaluates 5-10 examples per GPU call (120s limit)

**Model Caching**: Downloads Q5_K_M (5.5GB) once, cached for all runs

**llama.cpp + CUDA**: GPU-accelerated inference

**Real-time Progress**: Track evaluation in Gradio UI

**Detailed Metrics**: Success rate, latency, agent breakdown

## Expected Timeline

**First Run** (with caching):
- ⏱️ Setup: ~2-3 minutes
- ⏱️ Evaluation: ~15-20 minutes
- **Total**: ~18-23 minutes

**Subsequent Runs** (cached):
- ⏱️ Setup: ~5 seconds
- ⏱️ Evaluation: ~15-20 minutes
- **Total**: ~15 minutes

## Cost

**$0.00** - Included in your HF Pro subscription!

8x ZeroGPU quota = unlimited evaluations for development.

## ROI Comparison

| Option | Time | Cost | GPU | Result |
|--------|------|------|-----|--------|
| **ZeroGPU** | 18min | **FREE** | H200 | ⭐ Best |
| Together.ai | 18min | $32 | H100 | Good |
| HF A10G | 48min | $86 | A10G | OK |
| Local CPU | 5.1hrs | $510* | None | Avoid |

*Developer time @ $100/hr

## Troubleshooting

**Space won't start**: Click "Restart Space"

**Build fails**: Check logs, may need to rebuild llama.cpp

**Timeout errors**: Reduce batch size from 10 to 5

**Out of memory**: Restart Space (clears cache)

## Next Steps

After deployment:

1. ✅ Run full 31-example evaluation
2. 📊 Analyze results (success rate, latency)
3. 🔄 Try Q4_K_M for comparison
4. 📈 Iterate on prompts/examples
5. 📤 Share Space publicly

## Support

**Full documentation**: `hf_spaces/qwen3-eval/DEPLOYMENT.md`

**HF Spaces docs**: https://huggingface.co/docs/hub/spaces

**Questions**: HF Forums or GitHub issues

---

## TL;DR - Deploy Now

```bash
# 1. Go to Space directory
cd hf_spaces/qwen3-eval

# 2. Run deployment script
./deploy.sh

# 3. Visit your Space and run evaluation!
```

**Your HF Pro subscription just paid for itself.** 🚀
