# Qwen3-Next-80B Inference Endpoint Configuration Guide

**Model**: Qwen/Qwen3-Next-80B-A3B-Instruct
**Hardware**: Nvidia H200 2 GPUs · 282 GB RAM
**Cost**: $10/hour when active

---

## Recommended Configuration

### 1. Hardware (REQUIRED)

**Only Option That Works**: H200 2 GPUs
```
Instance Type: nvidia-h200
Instance Size: x2 (2 GPUs)
RAM: 282 GB
Cost: $10/hour per replica
```

**Why H200 x2?**
- 80B parameter model requires ~160GB VRAM (FP16)
- Single H200 (141GB) insufficient
- 2 x H200 (282GB total) provides headroom for KV cache + batching

### 2. Autoscaling (CRITICAL for Cost Control)

**Recommended Settings**:
```yaml
Scale-to-Zero: Enabled
Timeout: 1 hour (after last request)
Min Replicas: 0
Max Replicas: 1
Autoscaling Strategy: Hardware Usage
Hardware Utilization Threshold: 80%
```

**Cost Impact**:
- **With scale-to-zero**: $0 when idle, $10/hour when active
- **Without scale-to-zero**: $10/hour = $7,200/month (!!!)
- **Budget-friendly**: $100/month = 10 hours active time

**Tradeoff**:
- ✅ Pro: Only pay when using (~$0-10/day depending on usage)
- ⚠️ Con: First request after idle takes 2-3 minutes (cold start)

### 3. Security Level

**Recommended**: Protected

**Options**:
- **Protected**: Requires HF token, accessible only by you
- **Public**: No auth required (NOT recommended for production)
- **HF Restricted**: Most secure, but limited access

**Why Protected?**
- Balance of security + usability
- Prevents unauthorized usage (cost control)
- Easy integration with our code (just pass HF_TOKEN)

### 4. Container Type

**Recommended**: vLLM

**Configuration**:
```yaml
Container Type: vLLM
Tensor Parallel Size: 2  # Split across 2 GPUs
Max Batched Tokens: 32768  # Optimize throughput
Max Sequences: (auto)  # Let vLLM decide
KV Cache Data Type: auto  # Memory optimization
```

**Why vLLM?**
- Optimized for large language models
- PagedAttention for memory efficiency
- Continuous batching for throughput
- 2-3x faster than default container

**Tensor Parallel Size = 2**:
- Splits model across 2 GPUs
- Required for 80B model to fit
- Enables parallel processing

### 5. Environment Variables

**Required**:
```bash
MODEL_ID=Qwen/Qwen3-Next-80B-A3B-Instruct
NUM_SHARD=2  # Tensor parallel size
HUGGING_FACE_HUB_TOKEN=hf_xxx  # Your token
```

**Optional (Performance Tuning)**:
```bash
MAX_BATCH_PREFILL_TOKENS=32768  # Max tokens in batch
MAX_INPUT_LENGTH=8192  # Max input context
MAX_TOTAL_TOKENS=32768  # Max total (input + output)
MAX_CONCURRENT_REQUESTS=128  # Max parallel requests
```

**Recommended for Cost Control**:
```bash
MAX_INPUT_LENGTH=4096  # Limit context (faster, cheaper)
MAX_TOTAL_TOKENS=8192  # Limit output (faster, cheaper)
```

### 6. Region & Vendor

**Recommended**:
```
Vendor: AWS
Region: us-east-1 (East US)
```

**Why us-east-1?**
- Lowest latency for most US users
- Best availability
- Matches catalog default

**Alternative**: us-west-2 (if West Coast preferred)

### 7. Advanced Settings

**Commit Revision**: `main` (default)
- Use latest model version
- Or specify commit hash for reproducibility

**Task**: `text-generation` (auto-set for catalog model)

**Container Arguments**: (leave default)
- vLLM will auto-configure

---

## Configuration Comparison

### Option A: Cost-Optimized (Recommended for $100/month budget)

```yaml
Hardware: H200 x2 ($10/hour)
Scale-to-Zero: 1 hour timeout
Min/Max Replicas: 0/1
Container: vLLM
Tensor Parallel: 2
Max Input: 4096 tokens
Max Total: 8192 tokens

Monthly Cost: $0-100 (0-10 hours active)
Latency (cold): 2-3 minutes
Latency (warm): 5-10 seconds
Best For: High-quality tasks, batch processing
```

### Option B: Performance-Optimized (If budget allows)

```yaml
Hardware: H200 x2 ($10/hour)
Scale-to-Zero: Disabled
Min/Max Replicas: 1/1
Container: vLLM
Tensor Parallel: 2
Max Input: 8192 tokens
Max Total: 32768 tokens

Monthly Cost: $7,200/month (!!)
Latency: 5-10 seconds (always warm)
Best For: Production API, real-time applications
```

### Option C: Hybrid (Best of Both)

```yaml
Hardware: H200 x2 ($10/hour)
Scale-to-Zero: 15 minutes timeout (faster warmup)
Min/Max Replicas: 0/1
Container: vLLM
Tensor Parallel: 2
Max Input: 8192 tokens
Max Total: 16384 tokens

Monthly Cost: $10-200 (depends on usage pattern)
Latency (cold): 2-3 minutes
Latency (warm): 5-10 seconds
Best For: Moderate usage, balance cost/performance
```

---

## Recommended Configuration for Your Use Case

Based on $100/month budget + need for high-quality inference:

```yaml
# Basic
name: qwen3-next-80b-production
namespace: hollis-source  # Or Jake-DevOps-KTP for org billing
repository: Qwen/Qwen3-Next-80B-A3B-Instruct
revision: main

# Hardware (Only option that works)
accelerator: gpu
instance_type: nvidia-h200
instance_size: x2  # 2 GPUs, 282 GB RAM
vendor: aws
region: us-east-1

# Autoscaling (Cost Control)
min_replica: 0  # Scale-to-zero
max_replica: 1
scale_to_zero_timeout: 3600  # 1 hour
autoscaling_strategy: hardware_usage
utilization_threshold: 80

# Security
type: protected  # Requires HF token

# Container (vLLM Optimization)
container_type: vllm
tensor_parallel_size: 2  # Split across 2 GPUs
max_batch_prefill_tokens: 32768
max_input_length: 4096  # Reasonable limit
max_total_tokens: 8192  # Limits output length
kv_cache_dtype: auto

# Environment Variables
env:
  MODEL_ID: Qwen/Qwen3-Next-80B-A3B-Instruct
  NUM_SHARD: 2
  MAX_INPUT_LENGTH: 4096
  MAX_TOTAL_TOKENS: 8192
  HUGGING_FACE_HUB_TOKEN: ${HF_TOKEN}
```

**Cost Estimate**:
- Idle: $0/hour
- Active: $10/hour
- Budget: $100/month = 10 hours/month
- Recommended Usage Pattern:
  - Morning batch: 1-2 hours (research, analysis)
  - Afternoon queries: 0.5-1 hour (as needed)
  - Total: ~10-15 hours/month active = $100-150/month

**Usage Strategy**:
1. **Simple queries** → qwen3_hf_inference ($0-2/month, 0.6s latency)
2. **Complex reasoning** → qwen3-next-80b-endpoint ($10/hour, 5-10s warm)
3. **Fallback** → qwen3_zerogpu (free, 14s latency)

---

## Creation Steps

### Option 1: Using Web UI (Recommended for First Endpoint)

1. Go to: https://ui.endpoints.huggingface.co/
2. Click "New Endpoint"
3. Search: "Qwen3-Next-80B-A3B-Instruct"
4. Select from catalog
5. Configure:
   - Hardware: H200 x2 (only option shown)
   - Autoscaling: Enable scale-to-zero, 1 hour timeout
   - Security: Protected
   - Container: vLLM (default for catalog)
   - Advanced: Set env vars (NUM_SHARD=2, etc.)
6. Click "Create Endpoint"
7. Wait 3-5 minutes for deployment

### Option 2: Using Python Script (Automated)

```bash
source venv/bin/activate
source .env
python3 create_qwen3_next_80b_endpoint.py
```

**Follow prompts to confirm configuration**

### Option 3: Using hugie CLI (If available)

```bash
export HUGGINGFACE_READ_TOKEN="hf_xxx"

hugie endpoint create \
  --account-id hollis-source \
  --name qwen3-next-80b-production \
  --type protected \
  --accelerator GPU \
  --instance-type nvidia-h200 \
  --instance-size x2 \
  --min-replica 0 \
  --max-replica 1 \
  --repository Qwen/Qwen3-Next-80B-A3B-Instruct \
  --task text-generation \
  --vendor aws \
  --region us-east-1
```

---

## Integration After Creation

### 1. Get Endpoint URL

```python
from huggingface_hub import HfApi
api = HfApi(token=HF_TOKEN)
endpoint = api.get_inference_endpoint("qwen3-next-80b-production", namespace="hollis-source")
print(endpoint.url)  # https://xxx.aws.endpoints.huggingface.cloud
```

### 2. Create Adapter

**File**: `src/adapters/llm/qwen3_next_80b_endpoint_adapter.py`
```python
from huggingface_hub import InferenceClient
from src.interfaces import ITextGenerator, LLMConfig

class Qwen3Next80BEndpointAdapter(ITextGenerator):
    def __init__(self, endpoint_url: str, token: str):
        self.client = InferenceClient(model=endpoint_url, token=token)
        self.model_name = "Qwen3-Next-80B-Endpoint"

    def generate(self, messages, config):
        response = self.client.chat_completion(
            messages=messages,
            max_tokens=config.max_tokens or 2048,
            temperature=config.temperature or 0.7
        )
        return response.choices[0].message.content
```

### 3. Register Provider

```python
# src/factories/provider_creators.py
class Qwen3Next80BEndpointCreator:
    def create(self, config):
        endpoint_url = os.getenv("QWEN3_NEXT_ENDPOINT_URL")
        token = os.getenv("HF_TOKEN")
        return Qwen3Next80BEndpointAdapter(endpoint_url, token)

# Register
factory._creators["qwen3_next_80b"] = Qwen3Next80BEndpointCreator()
```

### 4. Add to ModelSelector

```python
# src/routing/model_selector.py
"qwen3_next_80b": ModelCapabilities(
    name="Qwen3-Next-80B-Endpoint",
    success_rate=1.0,
    avg_latency=7.0,  # Warm latency
    cost_per_month=100.0,  # Budget allocation
    requires_internet=True,
    max_tokens=8192,
    supports_tools=True
)
```

### 5. Use in CLI

```bash
export QWEN3_NEXT_ENDPOINT_URL="https://xxx.aws.endpoints.huggingface.cloud"

python3 -m src.main \
  --provider qwen3_next_80b \
  --task "Complex reasoning task requiring 80B model"
```

---

## Monitoring & Cost Control

### 1. Check Status

```python
python3 check_endpoint_status.py
```

### 2. Monitor Costs

- Dashboard: https://huggingface.co/settings/billing
- Check usage: Hours active × $10/hour
- Set alert: If monthly > $100

### 3. Pause Endpoint (If Exceeding Budget)

```python
from huggingface_hub import HfApi
api = HfApi(token=HF_TOKEN)
api.pause_inference_endpoint("qwen3-next-80b-production", namespace="hollis-source")
```

### 4. Resume When Needed

```python
api.resume_inference_endpoint("qwen3-next-80b-production", namespace="hollis-source")
```

---

## Questions to Consider

1. **Namespace**: Use personal (`hollis-source`) or organization (`Jake-DevOps-KTP`)?
   - Personal: Billed to your account
   - Organization: Billed to org, shared quota

2. **Scale-to-zero timeout**: 1 hour or 15 minutes?
   - 1 hour: More aggressive cost saving, longer cold starts
   - 15 min: Faster warmup, slightly higher costs

3. **Max input/output**: 4K/8K or 8K/16K?
   - Smaller: Faster, cheaper, sufficient for most tasks
   - Larger: Slower, more expensive, needed for long documents

4. **Should we create this endpoint?**
   - Do you have tasks requiring 80B model quality?
   - Can you stay within $100/month budget (10 hours)?
   - Or should we stick with qwen3_hf_inference (cheaper) + ZeroGPU (free)?

---

## My Recommendation

**For now**: Don't create the endpoint yet.

**Reasoning**:
1. **qwen3_hf_inference** already working (0.6-1.2s, FREE)
2. **qwen3_zerogpu** available as fallback (14s, FREE)
3. $100/month = only 10 hours with 80B model
4. Can always create endpoint later when specific need arises

**When to create**:
- Need high-quality reasoning beyond Qwen3-8B capabilities
- Have budget allocated for premium inference
- Workload justifies $10/hour cost (research, production API)

**Alternative**:
- Test quality difference: Qwen3-8B vs Qwen3-Next-80B via free methods
- If 8B sufficient → stick with hf-inference
- If 80B needed → create endpoint for specific high-value tasks

Want to proceed with creation anyway, or wait until specific need?
