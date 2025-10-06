# Create Qwen3-Next-80B Endpoint via Web UI - Step by Step

**You already have the catalog page open** - let's configure it!

---

## Configuration Checklist

### 1. Hardware Configuration ✅

**Already Selected**: Nvidia H200 2 GPUs · 282 GB · $10/h

This is the only option that works for this model.

### 2. Security Level

**Select**: **Protected**

Why: Requires HF token, prevents unauthorized usage

### 3. Autoscaling (CRITICAL)

**Configure**:
- ✅ Enable "Automatic Scale-to-Zero"
- Timeout: **After 1 hour with no activity**
- Min replicas: **0**
- Max replicas: **1**

**Autoscaling Strategy**:
- Select: **Hardware Usage**
- Hardware Utilization Threshold: **80%**

**This saves you $7,200/month!** ($0 when idle vs always-on)

### 4. Container Configuration

**Container Type**: **vLLM** (should be auto-selected for catalog model)

**Configuration**:
- **Tensor Parallel Size**: `2` (splits across 2 GPUs)
- **Max Batched Tokens**: Leave default (or set to `32768`)
- **Max Sequences**: Leave default (auto)
- **KV Cache Data Type**: Leave as `Auto`

### 5. Environment Variables (Optional but Recommended)

**Default Env** (click "+" to add):

| Key | Value |
|-----|-------|
| `MAX_INPUT_LENGTH` | `4096` |
| `MAX_TOTAL_TOKENS` | `8192` |

**Why**: Limits context/output → faster responses, lower costs

### 6. Advanced Settings

**Commit Revision**: Leave as default (`main`)

**Task**: `Text Generation` (auto-selected)

**Endpoint Tags**: (optional) Add `priority-inference` or `80b-model`

### 7. Name

**Suggested**: `qwen3-next-80b-production`

Or keep default if you prefer

---

## Step-by-Step Clicks

1. ✅ **Hardware**: Already selected (H200 2 GPUs)

2. **Security**: Click **"Protected"**

3. **Autoscaling**:
   - Toggle **ON**: "Automatic Scale-to-Zero"
   - Select: "After **1 hour** with no activity"
   - Min: `0`
   - Max: `1`
   - Strategy: **Hardware Usage**
   - Threshold: `80`

4. **Container**:
   - Type: **vLLM** (should be default)
   - Tensor Parallel: `2`
   - (Optional) Max Batched Tokens: `32768`

5. **Environment Variables** (Optional):
   - Click "+ Add" under Default Env
   - Add `MAX_INPUT_LENGTH` = `4096`
   - Add `MAX_TOTAL_TOKENS` = `8192`

6. **Name**: `qwen3-next-80b-production`

7. Click **"Deploy"** button at bottom

---

## After Deployment

### Wait for Deployment (3-5 minutes)

**Status will show**:
- Initializing → Building → Deploying → Running → Scaled to Zero

### Get Endpoint URL

**Location**: Endpoint details page

**Format**: `https://xxx-xxx.aws.endpoints.huggingface.cloud`

**Copy this URL** - we'll need it for integration!

### Test the Endpoint

Once status = "Running" or "Scaled to Zero":

1. Go to endpoint details page
2. Click "Test" tab
3. Send test message:
   ```json
   {
     "inputs": "What is Clean Architecture?",
     "parameters": {
       "max_new_tokens": 100,
       "temperature": 0.7
     }
   }
   ```

4. Should see response (first request takes 2-3 min if scaled to zero)

---

## What to Send Me After Creation

Please provide:

1. **Endpoint URL**: `https://xxx.aws.endpoints.huggingface.cloud`
2. **Status**: "Running" or "Scaled to Zero"
3. **Any errors**: If deployment failed

I'll then:
1. Create the adapter (`qwen3_next_80b_endpoint_adapter.py`)
2. Register it in ProviderFactory
3. Test with a complex architectural task
4. Compare with qwen3_hf_inference (8B model)

---

## Cost Monitoring

**Dashboard**: https://huggingface.co/settings/billing

**Track**:
- Hours active × $10/hour
- Should see $0 charges while scaled to zero
- First charge after first request wakes it up

**Alert**: If monthly cost > $100, pause the endpoint:
```python
from huggingface_hub import HfApi
api = HfApi(token=HF_TOKEN)
api.pause_inference_endpoint("qwen3-next-80b-production", namespace="hollis-source")
```

---

Ready to deploy? Click that **Deploy** button! 🚀

Then send me the endpoint URL and we'll test it with a priority architectural task.
