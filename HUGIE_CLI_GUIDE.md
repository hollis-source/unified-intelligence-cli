# Hugie CLI Guide - HuggingFace Inference Endpoints Management

**Date**: 2025-10-06
**Tool**: `hugie` - Third-party CLI for HF Inference Endpoints
**Purpose**: Manage Inference Endpoints without using Web UI

---

## Installation

### Option 1: Using pipx (recommended)
```bash
pipx install hugie
```

### Option 2: Using pip (in virtual environment)
```bash
source venv/bin/activate
pip install hugie
```

**Status**: ✅ Installed in `venv`

---

## Configuration

### 1. Set HuggingFace Token

**Environment Variable**:
```bash
export HUGGINGFACE_READ_TOKEN="hf_YOUR_TOKEN_HERE"
```

**For our project**:
```bash
export HUGGINGFACE_READ_TOKEN="hf_YOUR_TOKEN_HERE"
```

**Note**: Token needs **write permissions** for endpoint management (not just read)

### 2. Add to .env file

```bash
# .env
HUGGINGFACE_READ_TOKEN=hf_YOUR_TOKEN_HERE
```

---

## Commands

### General Usage

```bash
hugie --help
```

**Available commands**:
- `config` - Modify endpoint config files
- `endpoint` - Manage endpoints
- `ui` - Open HF Endpoints UI in browser
- `version` - Print hugie version

### Endpoint Commands

```bash
hugie endpoint --help
```

**Available subcommands**:
- `create` - Create an endpoint
- `delete` - Delete an endpoint
- `info` - Get info about an endpoint
- `list` (or `ls`) - List all deployed endpoints
- `logs` - Get logs about an endpoint
- `test` - Test an endpoint
- `update` - Update an endpoint

---

## Usage Examples

### 1. List Existing Endpoints

```bash
source venv/bin/activate
export HUGGINGFACE_READ_TOKEN="hf_YOUR_TOKEN_HERE"
hugie endpoint list
```

**Current Status**: ❌ Returns 404 (token may need write permissions)

### 2. Create Inference Endpoint

**Basic creation** (Qwen3-8B example):
```bash
hugie endpoint create \
  --account-id Jake-DevOps-KTP \
  --name qwen3-8b-production \
  --type private \
  --accelerator GPU \
  --instance-type nvidia-l4 \
  --instance-size x1 \
  --min-replica 0 \
  --max-replica 1 \
  --framework custom \
  --repository Qwen/Qwen3-8B \
  --revision main \
  --task text-generation \
  --image huggingface \
  --vendor aws \
  --region us-east-1 \
  --json
```

**Parameters explained**:
- `--account-id`: Organization name (Jake-DevOps-KTP)
- `--name`: Endpoint name
- `--type`: private (org billing), public (free), protected (auth required)
- `--accelerator`: GPU (for LLM inference)
- `--instance-type`: GPU instance (nvidia-l4, nvidia-a10g, etc.)
- `--instance-size`: Replicas per instance (x1, x2, x4)
- `--min-replica`: 0 for scale-to-zero (saves cost when idle)
- `--max-replica`: Maximum concurrent replicas
- `--repository`: HuggingFace model repo
- `--vendor`: Cloud provider (aws or gcp)
- `--region`: AWS/GCP region

**Advanced: Using JSON config file**:
```bash
# Create endpoint-config.json
cat > endpoint-config.json <<EOF
{
  "accountId": "Jake-DevOps-KTP",
  "compute": {
    "accelerator": "gpu",
    "instanceType": "nvidia-l4",
    "instanceSize": "x1",
    "scaling": {
      "minReplica": 0,
      "maxReplica": 1
    }
  },
  "model": {
    "framework": "custom",
    "repository": "Qwen/Qwen3-8B",
    "revision": "main",
    "task": "text-generation",
    "image": {
      "huggingface": {}
    }
  },
  "name": "qwen3-8b-production",
  "provider": {
    "region": "us-east-1",
    "vendor": "aws"
  },
  "type": "private"
}
EOF

# Create endpoint from config
hugie endpoint create endpoint-config.json --json
```

### 3. Get Endpoint Info

```bash
hugie endpoint info qwen3-8b-production --json
```

**Output includes**:
- Status (running, stopped, failed)
- URL for API calls
- Compute configuration
- Cost estimates
- Logs endpoint

### 4. Test Endpoint

```bash
hugie endpoint test qwen3-8b-production
```

**Sends test request to endpoint**

### 5. Get Endpoint Logs

```bash
hugie endpoint logs qwen3-8b-production
```

**View deployment and runtime logs**

### 6. Update Endpoint

**Scale up/down**:
```bash
hugie endpoint update qwen3-8b-production \
  --min-replica 0 \
  --max-replica 2
```

**Change instance type**:
```bash
hugie endpoint update qwen3-8b-production \
  --instance-type nvidia-a10g
```

### 7. Delete Endpoint

```bash
hugie endpoint delete qwen3-8b-production
```

---

## Integration with Our Project

### 1. Add Inference Endpoint Provider

Once endpoint is created via hugie, we can create a provider:

**File**: `src/adapters/llm/qwen3_inference_endpoint_adapter.py`
```python
from huggingface_hub import InferenceClient

class Qwen3InferenceEndpointAdapter(ITextGenerator):
    def __init__(self, endpoint_url: str, token: Optional[str] = None):
        self.client = InferenceClient(model=endpoint_url, token=token)

    def generate(self, messages, config):
        return self.client.chat_completion(
            messages=messages,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )
```

**Usage**:
```python
# Get endpoint URL from hugie endpoint info
endpoint_url = "https://xxx.aws.endpoints.huggingface.cloud"

adapter = Qwen3InferenceEndpointAdapter(endpoint_url=endpoint_url)
response = adapter.generate([{"role": "user", "content": "Hello"}])
```

### 2. CLI Integration

**Add to ProviderFactory**:
```python
class Qwen3EndpointCreator:
    def create(self, config):
        from src.adapters.llm.qwen3_inference_endpoint_adapter import Qwen3InferenceEndpointAdapter

        endpoint_url = config.get("endpoint_url") or os.getenv("QWEN3_ENDPOINT_URL")
        token = config.get("token") or os.getenv("HF_TOKEN")

        return Qwen3InferenceEndpointAdapter(endpoint_url, token)

# Register
factory._creators["qwen3_endpoint"] = Qwen3EndpointCreator()
```

**CLI usage**:
```bash
export QWEN3_ENDPOINT_URL="https://xxx.aws.endpoints.huggingface.cloud"

python3 -m src.main --provider qwen3_endpoint --task "test"
```

---

## Cost Management

### Pricing via hugie

**Scale-to-Zero Configuration**:
```bash
hugie endpoint create \
  --min-replica 0 \
  --max-replica 1 \
  ...
```

**Benefits**:
- **Idle cost**: $0 (when min-replica=0)
- **Active cost**: $1/hour (nvidia-l4 x1)
- **Budget**: $100/month = 100 hours/month available

**Cost tracking**:
```bash
# Monitor usage
hugie endpoint info qwen3-8b-production --json | jq '.status'

# Check logs for startup/shutdown events
hugie endpoint logs qwen3-8b-production | grep -i "scaled"
```

---

## Troubleshooting

### Issue 1: 404 Error on `hugie endpoint list`

**Symptom**:
```
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Cause**: Token might need **write permissions**, not just read

**Solution**:
1. Go to https://huggingface.co/settings/tokens
2. Create new token with `write` scope
3. Update HUGGINGFACE_READ_TOKEN environment variable

### Issue 2: Instance Type Not Found

**Symptom**:
```
Instance compute 'Gpu' - 'nvidia-l4' - 'x1' in 'aws' - 'us-east-1' not found
```

**Cause**: Instance type naming or availability issues

**Solutions**:
1. Check available instance types via Web UI
2. Try different instance types:
   - `nvidia-l4` (L4 GPU, $1/hour)
   - `nvidia-a10g` (A10G GPU, ~$2/hour)
   - `nvidia-t4` (T4 GPU, cheaper)
3. Try different regions (us-east-1, us-west-2, eu-west-1)

### Issue 3: Payment Method Required

**Symptom**:
```
Payment method required for namespace: Jake-DevOps-KTP
```

**Solution**:
1. Go to https://huggingface.co/organizations/Jake-DevOps-KTP/settings/billing
2. Add payment method (credit card)
3. Retry endpoint creation

---

## Comparison: hugie vs HF Web UI vs API

| Feature | hugie CLI | Web UI | Python API |
|---------|-----------|--------|------------|
| **Ease of use** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Automation** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Instance visibility** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Debugging** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **CI/CD integration** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ |

**Recommendation**:
- **Initial setup**: Use Web UI (easiest for first endpoint)
- **Management**: Use hugie CLI (scripting, automation)
- **Integration**: Use Python API (in our code)

---

## Next Steps

### For Our Project

1. **Get write-enabled token**:
   - Create new token with write scope
   - Update HUGGINGFACE_READ_TOKEN env var

2. **Create endpoint via hugie**:
   ```bash
   hugie endpoint create \
     --account-id Jake-DevOps-KTP \
     --name qwen3-8b-production \
     --type private \
     --accelerator GPU \
     --instance-type nvidia-l4 \
     --instance-size x1 \
     --min-replica 0 \
     --max-replica 1 \
     --repository Qwen/Qwen3-8B \
     --task text-generation \
     --vendor aws \
     --region us-east-1
   ```

3. **Get endpoint URL**:
   ```bash
   hugie endpoint info qwen3-8b-production --json | jq -r '.url'
   ```

4. **Create adapter**:
   - Implement `Qwen3InferenceEndpointAdapter`
   - Register in ProviderFactory
   - Test via CLI

5. **Benchmark**:
   - Compare hf-inference vs Inference Endpoint
   - Measure latency, cost, reliability
   - Update ModelSelector capabilities

---

## Resources

- **hugie GitHub**: https://github.com/huggingface/hugie
- **HF Inference Endpoints docs**: https://huggingface.co/docs/inference-endpoints
- **Pricing**: https://huggingface.co/pricing#endpoints
- **Instance types**: https://huggingface.co/docs/inference-endpoints/supported_hardware

---

**Created**: 2025-10-06
**Status**: Documented, ready for use
**Next**: Get write token, create endpoint, integrate adapter
