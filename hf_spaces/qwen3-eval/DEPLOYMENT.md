# ZeroGPU Space Deployment Guide

Complete step-by-step instructions for deploying Qwen3-8B evaluation to HuggingFace ZeroGPU.

## Prerequisites

✅ HuggingFace Pro account ($9/mo - required for ZeroGPU)
✅ HuggingFace CLI installed
✅ Git installed

## Quick Setup (5 minutes)

### 1. Install HuggingFace CLI

```bash
pip install huggingface_hub
```

### 2. Login to HuggingFace

```bash
huggingface-cli login
# Paste your HF token (get from https://huggingface.co/settings/tokens)
```

### 3. Create Space

**Option A: Via Web UI (Recommended)**

1. Go to https://huggingface.co/new-space
2. Fill in:
   - **Owner**: Your username
   - **Space name**: `qwen3-eval`
   - **License**: Apache 2.0
   - **Select SDK**: Gradio
   - **Space hardware**: ZeroGPU (Nvidia H200)
   - **Visibility**: Public or Private

3. Click "Create Space"

**Option B: Via CLI**

```bash
# Create Space with ZeroGPU
huggingface-cli create-space qwen3-eval \
  --space_sdk gradio \
  --space_hardware zero-a100
```

### 4. Clone and Push Code

```bash
# From unified-intelligence-cli directory
cd hf_spaces/qwen3-eval

# Initialize git if needed
git init
git remote add origin https://huggingface.co/spaces/YOUR_USERNAME/qwen3-eval

# Add all files
git add .
git commit -m "Initial commit: ZeroGPU evaluation Space"

# Push to HuggingFace
git push -u origin main
```

### 5. Configure Space Settings

1. Go to your Space: `https://huggingface.co/spaces/YOUR_USERNAME/qwen3-eval`
2. Click **Settings** tab
3. Verify **Space hardware** = **ZeroGPU**
4. Click **Save**

### 6. Wait for Build

- Space will automatically build (2-3 minutes)
- Watch logs in **App** tab
- First run takes longer (downloading model, building llama.cpp)

### 7. Run Evaluation

1. Click **App** tab
2. Paste your test data (JSONL) into text box
   - Or use the included `test_sample.jsonl` (31 examples)
3. Select batch size: **5** (recommended)
4. Click **🚀 Run Evaluation**
5. Watch progress bar and results appear

## Expected Results

**First Run:**
- Setup time: ~2-3 minutes (downloading + building)
- Evaluation time: ~15-20 minutes (31 examples)
- Total: ~18-23 minutes

**Subsequent Runs:**
- Setup time: ~5 seconds (cached)
- Evaluation time: ~15-20 minutes
- Total: ~15-20 minutes

## Cost

**FREE** with HuggingFace Pro subscription!

- ZeroGPU included in Pro ($9/mo)
- 8x quota multiplier
- Unlimited evaluations
- No additional GPU charges

## Troubleshooting

### Space Won't Start

**Error**: "Space is sleeping"
- **Solution**: Click "Restart Space" button

### Build Fails

**Error**: "Failed to build llama.cpp"
- **Check**: Space logs for specific error
- **Solution**: May need to update llama.cpp clone command

### Evaluation Timeout

**Error**: "ZeroGPU timeout after 120s"
- **Solution**: Reduce batch size from 10 to 5
- **Cause**: Some examples taking >12s each

### Out of Memory

**Error**: "CUDA out of memory"
- **Solution**: Model is cached, try restarting Space
- **Alternative**: Use smaller batch size

## Advanced Configuration

### Custom Test Data

Replace test_sample.jsonl with your own:

```bash
# In Space repository
cp your_test_data.jsonl test_sample.jsonl
git add test_sample.jsonl
git commit -m "Update test data"
git push
```

### Different Models

Edit `app.py`:

```python
MODEL_REPO = "unsloth/Qwen3-8B-GGUF"
MODEL_FILE = "Qwen3-8B-Q4_K_M.gguf"  # Change to Q4_K_M
```

### Batch Size Tuning

- **Batch size 5**: Safer, more GPU calls, slower overall
- **Batch size 10**: Faster, fewer GPU calls, may timeout
- **Recommended**: Start with 5, increase if all examples <10s

## Monitoring

### Check Space Status

```bash
huggingface-cli space status YOUR_USERNAME/qwen3-eval
```

### View Logs

```bash
huggingface-cli space logs YOUR_USERNAME/qwen3-eval
```

### Download Results

Results are shown in UI. To download:

1. Click "Download JSON" in Gradio UI
2. Or copy from JSON output panel

## Performance Comparison

| Platform | Hardware | Time | Cost | Setup |
|----------|----------|------|------|-------|
| **ZeroGPU** | H200 | ~18min | **FREE** | 5 min |
| Local CPU | 96 cores | 5.1hrs | $0 | 0 min |
| Together.ai | H100 | ~18min | $32 | 30 min |
| HF Spaces A10G | A10G | ~48min | $86 | 45 min |

**Winner**: ZeroGPU (FREE, fast, easy setup)

## Next Steps

1. ✅ Create Space
2. ✅ Push code
3. ✅ Run evaluation
4. 📊 Analyze results
5. 🔄 Iterate on model/config
6. 📤 Share Space publicly

## Pro Tips

- **Cache Everything**: Model and llama.cpp cached after first run
- **Pro Priority**: Your Pro account gets priority queue
- **Batch Wisely**: 5-7 examples per batch is sweet spot
- **Monitor Usage**: Check ZeroGPU quota in HF dashboard
- **Share Results**: Make Space public for collaboration

## Support

- **HF Forums**: https://discuss.huggingface.co/
- **Spaces Docs**: https://huggingface.co/docs/hub/spaces
- **ZeroGPU Guide**: https://huggingface.co/docs/hub/spaces-gpus

---

**Ready to deploy?** Run the commands in Quick Setup section!
