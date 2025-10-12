---
title: Qwen3-8B Q5_K_M Evaluation
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: apache-2.0
---

# Qwen3-8B Q5_K_M Evaluation on ZeroGPU

Evaluate Qwen3-8B GGUF models using llama.cpp on **HuggingFace ZeroGPU** (H200 GPU).

## Features

- **H200 GPU**: Runs on Nvidia H200 (FREE with HF Pro subscription)
- **Batched Processing**: Evaluates 5-10 examples per GPU call
- **llama.cpp**: CUDA-accelerated inference for GGUF models
- **Real-time Progress**: Track evaluation progress in UI
- **Detailed Metrics**: Success rate, latency, agent-level breakdown

## How It Works

1. **Setup** (CPU): Downloads Qwen3-8B-Q5_K_M GGUF and builds llama.cpp (cached)
2. **Batch Evaluation** (GPU): Runs inference on batches using ZeroGPU decorator
3. **Aggregation** (CPU): Combines results and computes metrics

## Usage

1. Paste your test data (JSONL format) into the text box
2. Select batch size (5-10 recommended)
3. Click "Run Evaluation"
4. View results in real-time

## Requirements

- HuggingFace Pro account (for ZeroGPU access)
- Test data in JSONL format with `text`, `agent`, `task_id` fields

## Technical Details

- **Model**: Qwen3-8B-Q5_K_M (5.5GB GGUF from unsloth/Qwen3-8B-GGUF)
- **Hardware**: ZeroGPU H200 (80GB VRAM)
- **Framework**: llama.cpp with CUDA support
- **Timeout**: 120s per batch (ZeroGPU limit)
- **Success Metric**: Generated length within 50-200% of expected

## Benefits

- **FREE** with HF Pro ($9/mo)
- **Reproducible**: Docker-based environment
- **Shareable**: Public Space for collaboration
- **Persistent**: Re-run anytime without setup

## Performance

- **Setup time**: ~2-3 min (first run only, then cached)
- **Inference speed**: ~2-5s per example on H200
- **Total time**: ~15-30 min for 31 examples (vs 5 hours on CPU)

---

Built with ❤️ using Category Theory DSL workflows
