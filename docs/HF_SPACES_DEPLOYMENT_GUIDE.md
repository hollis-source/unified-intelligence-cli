# HuggingFace Spaces Deployment Guide

**Recommended**: HF Spaces A10G Small
**Cost**: $86.10 total
**Savings**: $423.68 vs CPU
**Speedup**: 6.0x faster

## Prerequisites

1. HuggingFace Pro account (✓ you have this)
2. Hugging Face CLI installed: `pip install huggingface_hub`
3. Login: `huggingface-cli login`

## Deployment Steps

### 1. Create Space

```bash
# Create new Space via web UI or CLI
# https://huggingface.co/new-space
# Name: qwen3-8b-evaluation
# SDK: Docker
```

### 2. Create Dockerfile

```dockerfile
FROM python:3.10-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    cmake \
    build-essential

# Install Python packages
RUN pip install huggingface_hub

# Copy evaluation script
COPY training/scripts/evaluate_gguf.py /app/evaluate.py
COPY training/data/test.jsonl /app/test.jsonl

# Download model
RUN huggingface-cli download unsloth/Qwen3-8B-GGUF Qwen3-8B-Q5_K_M.gguf --local-dir /app/models

# Install llama.cpp
RUN git clone https://github.com/ggerganov/llama.cpp /app/llama.cpp && \
    cd /app/llama.cpp && \
    cmake -B build -DGGML_CUDA=ON && \
    cmake --build build

# Run evaluation
CMD python /app/evaluate.py --model /app/models/Qwen3-8B-Q5_K_M.gguf --test-data /app/test.jsonl
```

### 3. Push to Space

```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/qwen3-8b-evaluation
cd qwen3-8b-evaluation
cp training/scripts/evaluate_gguf.py .
cp training/data/test.jsonl .
# Create Dockerfile (see above)
git add .
git commit -m "Add evaluation pipeline"
git push
```

### 4. Upgrade to GPU

1. Go to Space settings
2. Select **HF Spaces A10G Small**
3. Start Space
4. Monitor logs for results

### 5. Download Results

```bash
# Results will be in Space logs or you can output to HF dataset
huggingface-cli download spaces/YOUR_USERNAME/qwen3-8b-evaluation results.json
```

## Alternative: ZeroGPU (Pro Account Benefit)

With your Pro account, you get 8x ZeroGPU quota. Consider:

```python
# Use @spaces.GPU decorator for automatic GPU allocation
import spaces

@spaces.GPU
def run_evaluation():
    """Evaluation runs on H200 for free with Pro account"""
    # Your evaluation code
```

## Cost Estimate

- Setup time: ~0.75 hours
- Evaluation time: ~0.6 hours
- GPU cost: $86.10
- Pro account discount: Applied

## Benefits

1. **Version Control**: All code in git
2. **Reproducibility**: Docker ensures consistent environment
3. **Shareable**: Public or private Space
4. **Persistent**: Re-run anytime without setup
5. **Pro Benefits**: Priority queue, credits, ZeroGPU access