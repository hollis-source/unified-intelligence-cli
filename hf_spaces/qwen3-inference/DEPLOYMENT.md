# Qwen3-8B Inference Space - Deployment Guide

## Quick Deployment

### 1. Create Space on HuggingFace

```bash
# Option A: Via Web UI
# 1. Go to https://huggingface.co/new-space
# 2. Choose:
#    - Owner: hollis-source (or your username)
#    - Space name: qwen3-inference
#    - SDK: Gradio
#    - Hardware: zero-a10g (ZeroGPU)
#    - Public/Private: Your choice

# Option B: Via huggingface_hub CLI
pip install huggingface_hub
huggingface-cli login  # Enter your HF token

# Create Space
python3 << 'SCRIPT'
from huggingface_hub import HfApi

api = HfApi()
api.create_repo(
    repo_id="hollis-source/qwen3-inference",
    repo_type="space",
    space_sdk="gradio",
    space_hardware="zero-a10g"
)
SCRIPT
```

### 2. Upload Files

```bash
cd hf_spaces/qwen3-inference

# Upload all files
huggingface-cli upload hollis-source/qwen3-inference . --repo-type=space
```

### 3. Verify Deployment

```bash
# Check Space status
python3 << 'SCRIPT'
from huggingface_hub import HfApi

api = HfApi()
info = api.space_info("hollis-source/qwen3-inference")
print(f"Stage: {info.runtime.stage}")
print(f"URL: https://huggingface.co/spaces/hollis-source/qwen3-inference")
SCRIPT
```

### 4. Test Inference

```python
from gradio_client import Client

client = Client("hollis-source/qwen3-inference")
response, history = client.predict(
    user_message="What is Clean Architecture?",
    system_prompt="You are a helpful AI assistant.",
    temperature=0.7,
    max_tokens=512,
    history=None,
    api_name="/generate_response"
)
print(response)
```

### 5. Update CLI Configuration

```bash
# Edit src/factories/provider_factory.py (already done!)
# Test via CLI:
python src/main.py --provider qwen3_zerogpu --query "Explain SOLID principles"
```

## Performance Expectations

- **Success Rate**: 100% (validated via eval Space)
- **Latency**: ~13.8s avg (target: <10s with optimization)
- **Cost**: FREE with HF Pro ($9/month)

## Next Steps

1. **Monitor Performance**: Check latency and success rate in production
2. **Optimize if Needed**: Try INT8 quantization for <10s latency
3. **Scale Usage**: Integrate with all CLI workflows
4. **Documentation**: Update README with Qwen3 examples

## Troubleshooting

### Space Build Fails
- Check that all dependencies in requirements.txt are valid
- Verify ZeroGPU hardware is selected
- Check build logs in Space settings

### Model Load Timeout
- Lazy loading is implemented (loads on first call)
- First inference will take ~3-5 min (model download)
- Subsequent calls: fast (<15s)

### Inference Errors
- Verify Space is RUNNING (not BUILDING or STOPPED)
- Check that HF Pro subscription is active
- Test with simple query first

## Files Structure

```
hf_spaces/qwen3-inference/
├── app.py              # Gradio app with ZeroGPU integration
├── requirements.txt    # Dependencies
├── README.md          # Space description (shows on HF)
└── DEPLOYMENT.md      # This file
```

## Architecture

- **Pattern**: Clean Architecture (Adapter + Interface)
- **Adapter**: `src/adapters/llm/qwen3_zerogpu_adapter.py`
- **Factory**: `src/factories/provider_factory.py` (qwen3_zerogpu provider)
- **Interface**: `ITextGenerator` (DIP compliance)
