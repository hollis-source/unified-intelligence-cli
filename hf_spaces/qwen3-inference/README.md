---
title: Qwen3-8B Production Inference
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 5.48.0
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-a10g
---

# Qwen3-8B Production Inference

Production-ready inference for fine-tuned Qwen3-8B running on ZeroGPU H200.

## Performance Metrics

- ✅ **Success Rate**: 100% (evaluated on 31 examples)
- ⚡ **Avg Latency**: 13.8s (31% faster than baseline)
- 🔥 **Hardware**: ZeroGPU H200 (70GB VRAM, FREE with HF Pro)

## Usage

### Web Interface
Visit the Space URL and interact via chat interface.

### Python API
```python
from gradio_client import Client

client = Client("hollis-source/qwen3-inference")
response = client.predict(
    user_message="What is Clean Architecture?",
    system_prompt="You are a helpful AI assistant.",
    temperature=0.7,
    max_tokens=512,
    history=None,
    api_name="/predict"
)
print(response)
```

### unified-intelligence-cli Integration
```bash
python src/main.py --provider qwen3_zerogpu --query "Explain SOLID principles"
```

## Model Information

- **Model**: Qwen3-8B (fine-tuned with LoRA)
- **Precision**: FP16 (torch.float16)
- **Parameters**: 8B
- **Training**: LoRA fine-tuning on 298 examples
- **Evaluation**: 100% success, 13.8s avg latency

## Architecture

- **Pattern**: Lazy model loading to avoid startup timeouts
- **GPU Allocation**: 60s ZeroGPU duration per request
- **Framework**: Transformers + PyTorch + ZeroGPU decorator

## Links

- [Evaluation Space](https://huggingface.co/spaces/hollis-source/qwen3-eval)
- [Model Card](https://huggingface.co/Qwen/Qwen3-8B)
- [GitHub](https://github.com/hollis-source/unified-intelligence-cli)

## Cost

**FREE** with HuggingFace Pro subscription ($9/month).
