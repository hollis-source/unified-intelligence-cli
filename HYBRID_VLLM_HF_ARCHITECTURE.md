# Hybrid vLLM + HuggingFace Architecture for Development

**Date**: 2025-10-06
**Scope**: Local vLLM + HF Inference Endpoints hybrid deployment
**Goal**: Optimize dev workflow with fast local inference + production HF deployment

---

## Executive Summary

Yes, you can create a **powerful hybrid architecture** that combines:
1. **HF Hub** for model storage/versioning
2. **Local vLLM** for fast development (3-5s latency)
3. **HF Inference Endpoint** for production/sharing

**Key Benefits**:
- 🚀 **10x faster local dev** (45s → 3-5s)
- 💰 **Cost control** (free local dev, pay only for production)
- 🔄 **Easy deployment** (one command from local → HF)
- 🎯 **No rate limits** during development
- 📦 **Version control** via HF Hub

---

## Architecture Options

### Option 1: Full Hybrid (Recommended)
**Flow**: HF Model Hub → Local vLLM (dev) + HF Inference Endpoint (prod)

```
┌─────────────────┐
│  HF Model Hub   │ ← Store/version Qwen3-8B
│  (Free)         │
└────────┬────────┘
         │
    ┌────┴─────┐
    │          │
    ▼          ▼
┌─────────┐  ┌──────────────────┐
│ Local   │  │ HF Inference     │
│ vLLM    │  │ Endpoint         │
│ (Dev)   │  │ (Production)     │
│         │  │                  │
│ 3-5s    │  │ $0.60-4/hour     │
│ Free    │  │ Auto-scaling     │
└─────────┘  └──────────────────┘
     │               │
     ▼               ▼
┌─────────────────────────────┐
│  unified-intelligence-cli   │
│  (Multi-provider routing)   │
└─────────────────────────────┘
```

**Use Cases**:
- Local dev: Use local vLLM (instant, free)
- Production: Use HF Endpoint (managed, scalable)
- Team sharing: HF Endpoint (no local setup needed)

### Option 2: Local-Only with HF Storage
**Flow**: HF Model Hub → Local vLLM only

```
┌─────────────────┐
│  HF Model Hub   │ ← Store model
│  (Free)         │
└────────┬────────┘
         │
         ▼
    ┌─────────┐
    │ Local   │
    │ vLLM    │
    │         │
    │ 3-5s    │
    │ Free    │
    └─────────┘
         │
         ▼
┌─────────────────────────────┐
│  unified-intelligence-cli   │
└─────────────────────────────┘
```

**Use Cases**:
- Solo dev work
- No production deployment needed
- Full local control

### Option 3: HF Dedicated Inference Endpoint Only
**Flow**: HF Model Hub → HF Dedicated Endpoint

```
┌─────────────────┐
│  HF Model Hub   │
│  (Free)         │
└────────┬────────┘
         │
         ▼
┌──────────────────────┐
│ HF Inference         │
│ Endpoint (Dedicated) │
│                      │
│ $0.60-4/hour         │
│ Always-on            │
│ 3-10s latency        │
└──────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  unified-intelligence-cli   │
└─────────────────────────────┘
```

**Use Cases**:
- Team development (shared endpoint)
- No local GPU available
- Need persistent deployment

---

## Benefits for Development Workflow

### 1. **10x Faster Local Development** 🚀

**Current (HF ZeroGPU)**:
- Latency: 45s average
- Network overhead: ~30s
- Rate limits: Unknown
- Cold starts: ~57s

**With Local vLLM**:
- Latency: **3-5s** (10x faster)
- No network overhead
- No rate limits
- No cold starts (model stays loaded)

**Impact on Dev Velocity**:
```
# Current workflow (ZeroGPU)
Test iteration: 45s × 20 tests/day = 15 minutes wasted
Week: 15 min/day × 5 days = 75 minutes wasted

# Local vLLM workflow
Test iteration: 4s × 20 tests/day = 1.3 minutes
Week: 1.3 min/day × 5 days = 6.5 minutes

Time saved: 68.5 minutes/week = 59 hours/year
```

### 2. **Cost Control** 💰

**Development Phase**:
- Local vLLM: **$0/month** (use existing GPU or rent hourly)
- No API costs
- No rate limit charges

**Production Phase**:
- HF Inference Endpoint: **$0.60-$4/hour** (only when needed)
- Auto-scaling: Pay only for active hours
- Option to pause when not in use

**Cost Comparison**:
| Scenario | ZeroGPU | Local vLLM | HF Dedicated |
|----------|---------|------------|--------------|
| Dev (40h/week) | Free (slow) | Free (fast) | $96-640/month |
| Production (24/7) | Not possible | $50-200/month* | $432-2880/month |
| Hybrid (dev local, prod HF) | - | **$50-100/month** | - |

*Local server costs (AWS p3.2xlarge ~$3/hour or own GPU)

### 3. **No Rate Limits** 🎯

**Current Limitations**:
- ZeroGPU: 60s allocation, unknown concurrent limits
- HF Spaces Free: Rate limited on high traffic

**Local vLLM**:
- Unlimited requests (only bound by GPU)
- Process 10-20 requests/second (batching)
- No throttling during development

**Development Impact**:
- Run large test suites: 100+ tests in minutes
- Parallel experiments: Test multiple prompts simultaneously
- Load testing: Stress test before production

### 4. **Easy Deployment Pipeline** 🔄

**Workflow**:
```bash
# 1. Develop locally with vLLM
vllm serve Qwen/Qwen3-8B --dtype half --port 8000

# 2. Test in CLI (local provider)
./bin/ui-cli --task "test" --provider qwen3_local

# 3. Deploy to HF when ready
huggingface-cli endpoint create qwen3-prod \
  --repository Qwen/Qwen3-8B \
  --accelerator gpu \
  --instance-type g5.xlarge

# 4. CLI auto-routes to production
./bin/ui-cli --task "prod query" --provider qwen3_hf_endpoint
```

**Benefits**:
- One-command deployment
- Same model, different runtime
- Easy rollback (switch provider)

### 5. **Version Control & Experimentation** 📦

**HF Hub as Source of Truth**:
```bash
# Push fine-tuned model
huggingface-cli upload qwen3-8b-finetuned ./model

# Tag versions
git tag v1.0.0 && git push --tags

# Pull specific version locally
vllm serve hollis-source/qwen3-8b-finetuned@v1.0.0

# Pull to HF Endpoint
huggingface-cli endpoint update qwen3-prod \
  --repository hollis-source/qwen3-8b-finetuned@v1.0.0
```

**Experiment Workflow**:
- Train locally or on HF
- Push to HF Hub with version tag
- Test locally with vLLM
- Deploy to HF Endpoint when validated
- Rollback via version tags

### 6. **Team Collaboration** 👥

**Local Dev + Shared Endpoint**:
```
Developer A          Developer B          Production
     │                    │                    │
     ▼                    ▼                    ▼
┌─────────┐          ┌─────────┐          ┌─────────┐
│ Local   │          │ Local   │          │ HF      │
│ vLLM    │          │ vLLM    │          │ Endpoint│
│ (v1.1)  │          │ (v1.2)  │          │ (v1.0)  │
└─────────┘          └─────────┘          └─────────┘
     │                    │                    │
     └────────────────────┴────────────────────┘
                         │
                         ▼
                 ┌────────────────┐
                 │  HF Model Hub  │
                 │  (All versions)│
                 └────────────────┘
```

**Benefits**:
- Each dev has fast local inference
- Share experiments via HF Hub
- Production stable on HF Endpoint
- No conflicts, isolated testing

---

## Implementation Guide

### Step 1: Setup Local vLLM

**Install vLLM**:
```bash
pip install vllm

# Or with specific version
pip install vllm==0.4.2
```

**Start vLLM Server**:
```bash
# Basic usage
vllm serve Qwen/Qwen3-8B \
  --dtype half \
  --port 8000 \
  --gpu-memory-utilization 0.9

# With optimizations
vllm serve Qwen/Qwen3-8B \
  --dtype half \
  --port 8000 \
  --gpu-memory-utilization 0.9 \
  --max-model-len 2048 \
  --tensor-parallel-size 1 \
  --enable-chunked-prefill
```

**Test Local Endpoint**:
```bash
curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-8B",
    "prompt": "Explain dependency injection",
    "max_tokens": 100
  }'
```

### Step 2: Create Local Provider in CLI

**File**: `src/adapters/llm/qwen3_local.py`
```python
"""Local vLLM provider for Qwen3-8B"""

import requests
from typing import Optional

class Qwen3LocalProvider:
    """vLLM local inference provider"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.model = "Qwen/Qwen3-8B"

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate response via local vLLM"""

        # Format prompt with system message
        if system_prompt:
            formatted_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
        else:
            formatted_prompt = f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"

        response = requests.post(
            f"{self.base_url}/v1/completions",
            json={
                "model": self.model,
                "prompt": formatted_prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stop": ["<|im_end|>"]
            },
            timeout=30
        )

        response.raise_for_status()
        return response.json()["choices"][0]["text"].strip()
```

**Integration in ModelOrchestrator**:
```python
# src/adapters/llm/model_orchestrator.py

def _create_provider(self, provider_name: str):
    """Create LLM provider instance"""

    if provider_name == "qwen3_local":
        from src.adapters.llm.qwen3_local import Qwen3LocalProvider
        return Qwen3LocalProvider(base_url="http://localhost:8000")

    elif provider_name == "qwen3_hf_endpoint":
        from src.adapters.llm.qwen3_hf_endpoint import Qwen3HFEndpointProvider
        return Qwen3HFEndpointProvider(endpoint_url=os.getenv("HF_ENDPOINT_URL"))

    # ... other providers
```

### Step 3: Deploy to HF Inference Endpoint

**Create Dedicated Endpoint**:
```bash
# Using HF CLI
huggingface-cli endpoint create qwen3-8b-prod \
  --repository "Qwen/Qwen3-8B" \
  --framework pytorch \
  --accelerator gpu \
  --instance-type "g5.xlarge" \
  --task text-generation \
  --min-replica 1 \
  --max-replica 3

# Get endpoint URL
huggingface-cli endpoint list
```

**Or via Python**:
```python
from huggingface_hub import HfApi, InferenceEndpoint

api = HfApi()

endpoint = api.create_inference_endpoint(
    name="qwen3-8b-prod",
    repository="Qwen/Qwen3-8B",
    framework="pytorch",
    task="text-generation",
    accelerator="gpu",
    instance_type="g5.xlarge",
    min_replica=1,
    max_replica=3,
    type="protected"  # Requires authentication
)

print(f"Endpoint URL: {endpoint.url}")
```

### Step 4: Create HF Endpoint Provider

**File**: `src/adapters/llm/qwen3_hf_endpoint.py`
```python
"""HF Inference Endpoint provider for Qwen3-8B"""

import os
import requests
from typing import Optional

class Qwen3HFEndpointProvider:
    """HF Dedicated Inference Endpoint provider"""

    def __init__(self, endpoint_url: str = None):
        self.endpoint_url = endpoint_url or os.getenv("HF_ENDPOINT_URL")
        self.token = os.getenv("HF_TOKEN")

        if not self.endpoint_url:
            raise ValueError("HF_ENDPOINT_URL not set")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate response via HF Endpoint"""

        # Format messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = requests.post(
            self.endpoint_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            },
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature,
                    "return_full_text": False
                }
            },
            timeout=30
        )

        response.raise_for_status()
        return response.json()[0]["generated_text"].strip()
```

### Step 5: Multi-Provider Routing

**Smart Routing in CLI**:
```python
# src/adapters/llm/model_orchestrator.py

def select_provider(self, task_description: str, context: dict = None) -> str:
    """Select provider based on environment and requirements"""

    # Development mode: Use local if available
    if os.getenv("ENV") == "development":
        if self._is_local_available():
            return "qwen3_local"

    # Production mode: Use HF Endpoint
    if os.getenv("ENV") == "production":
        if os.getenv("HF_ENDPOINT_URL"):
            return "qwen3_hf_endpoint"

    # Fallback to ZeroGPU (free tier)
    return "qwen3_zerogpu"

def _is_local_available(self) -> bool:
    """Check if local vLLM is running"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=1)
        return response.status_code == 200
    except:
        return False
```

**Environment-based Configuration**:
```bash
# .env.development
ENV=development
# Local vLLM auto-detected at localhost:8000

# .env.production
ENV=production
HF_ENDPOINT_URL=https://xxx.aws.endpoints.huggingface.cloud
HF_TOKEN=hf_xxxxxxxxxxxx
```

---

## Cost Analysis

### Local vLLM Costs

**Option 1: Use Existing GPU**
- Cost: **$0/month** (if you have GPU)
- Requirements: NVIDIA GPU with 16GB+ VRAM (RTX 4090, A6000, etc.)

**Option 2: Cloud VM with GPU**
- AWS p3.2xlarge (V100 16GB): **$3.06/hour** = $73/day (24/7) or $15/day (5h dev)
- GCP n1-standard-4 + T4: **$0.95/hour** = $23/day (24/7) or $5/day (5h dev)
- Paperspace: **$0.76/hour** (RTX 4000) = $18/day (24/7) or $4/day (5h dev)

**Option 3: Rent GPU Hourly (Dev Only)**
- RunPod: **$0.29/hour** (RTX 3090) = ~$50/month (5h/day × 30 days)
- Vast.ai: **$0.15/hour** (RTX 3080) = ~$25/month (5h/day × 30 days)

### HF Inference Endpoint Costs

**Dedicated Endpoints (Always-On)**:
| Instance | GPU | VRAM | Cost/Hour | Cost/Month (24/7) |
|----------|-----|------|-----------|-------------------|
| g5.xlarge | A10G | 24GB | $1.00 | $720 |
| g5.2xlarge | A10G | 24GB | $1.50 | $1,080 |
| p4d.24xlarge | A100 | 40GB | $4.00 | $2,880 |

**Serverless Endpoints (Pay-per-Request)**:
- Not yet available for custom models
- ZeroGPU remains free tier option

### Cost Comparison (Monthly)

| Scenario | Setup | Cost | Performance |
|----------|-------|------|-------------|
| **Current (ZeroGPU)** | Free HF Space | $0 | 45s latency |
| **Local Dev Only** | Own GPU | $0 | 3-5s latency |
| **Local Dev + HF Prod** | Vast.ai + g5.xlarge | $50 + $720 = $770 | 3-5s dev, 5-10s prod |
| **Hybrid Optimized** | Own GPU + g5.xlarge (8h/day) | $0 + $240 = $240 | 3-5s dev, 5-10s prod |
| **All-Local (24/7)** | AWS p3.2xlarge | $2,203 | 3-5s always |

**Recommended for Dev**:
- **Phase 1 (Solo)**: Local vLLM on own GPU ($0/month)
- **Phase 2 (Team)**: Local + HF Endpoint 8h/day ($240/month)
- **Phase 3 (Production)**: HF Endpoint 24/7 ($720/month)

---

## Benefits Summary

### Development Workflow Improvements

| Benefit | Current (ZeroGPU) | With Local vLLM | Improvement |
|---------|-------------------|-----------------|-------------|
| **Latency** | 45s | 3-5s | **10x faster** |
| **Iteration Speed** | 15 min/day wasted | 1.3 min/day | **59 hours/year saved** |
| **Rate Limits** | Unknown, limited | None | **Unlimited dev** |
| **Cost (Dev)** | Free (slow) | Free (fast) | **$0, 10x faster** |
| **Deployment** | Manual update | One command | **Automated** |
| **Team Sharing** | Requires HF Space | HF Endpoint | **Scalable** |
| **Version Control** | Manual | HF Hub tags | **Git-like workflow** |
| **Experimentation** | Slow iteration | Fast A/B testing | **10x more experiments** |

### Production Benefits

| Benefit | Description | Impact |
|---------|-------------|--------|
| **Easy Deployment** | `huggingface-cli endpoint create` | 5 min to production |
| **Auto-Scaling** | HF manages replicas | Handle traffic spikes |
| **Monitoring** | HF dashboard + logs | Built-in observability |
| **Rollback** | Version tags | Instant rollback |
| **Cost Control** | Pause when not in use | Pay only for active time |
| **Security** | Private endpoints | API key authentication |

---

## Recommended Architecture

### For unified-intelligence-cli Development

**Recommended Setup: Hybrid Local + HF**

```python
# config/providers.yaml
providers:
  qwen3_local:
    type: vllm
    url: http://localhost:8000
    enabled: ${LOCAL_VLLM_ENABLED:-true}

  qwen3_hf_endpoint:
    type: hf_endpoint
    url: ${HF_ENDPOINT_URL}
    token: ${HF_TOKEN}
    enabled: ${HF_ENDPOINT_ENABLED:-false}

  qwen3_zerogpu:
    type: gradio
    url: https://hollis-source-qwen3-inference.hf.space
    enabled: true  # Fallback

# Routing strategy
routing:
  strategy: auto
  priority:
    - qwen3_local      # Try local first (if available)
    - qwen3_hf_endpoint  # Then HF Endpoint (if configured)
    - qwen3_zerogpu    # Fallback to free tier
```

**Development Workflow**:
```bash
# 1. Start local vLLM (one-time setup)
vllm serve Qwen/Qwen3-8B --dtype half --port 8000 &

# 2. Develop with local inference (3-5s latency)
./bin/ui-cli --task "test" --provider auto  # Uses qwen3_local

# 3. Deploy to HF when ready
huggingface-cli endpoint create qwen3-prod --repository Qwen/Qwen3-8B

# 4. Test production endpoint
HF_ENDPOINT_ENABLED=true ./bin/ui-cli --task "prod test" --provider auto

# 5. Switch environments
ENV=development ./bin/ui-cli --task "dev"   # Uses local
ENV=production ./bin/ui-cli --task "prod"   # Uses HF Endpoint
```

---

## Implementation Checklist

### Phase 1: Local vLLM Setup (Today - 1 hour)
- [ ] Install vLLM: `pip install vllm`
- [ ] Start vLLM server with Qwen3-8B
- [ ] Create `qwen3_local.py` provider
- [ ] Test local inference: `./bin/ui-cli --provider qwen3_local`
- [ ] Benchmark latency (expect 3-5s)

### Phase 2: HF Endpoint Setup (Tomorrow - 2 hours)
- [ ] Create HF Inference Endpoint via CLI
- [ ] Get endpoint URL and save to `.env`
- [ ] Create `qwen3_hf_endpoint.py` provider
- [ ] Test HF Endpoint: `./bin/ui-cli --provider qwen3_hf_endpoint`
- [ ] Benchmark latency (expect 5-10s)

### Phase 3: Multi-Provider Routing (This Week - 3 hours)
- [ ] Update `model_orchestrator.py` with auto-routing
- [ ] Add environment detection (local vs HF)
- [ ] Implement fallback logic
- [ ] Add health checks for local vLLM
- [ ] Update CLI to support `--provider auto`

### Phase 4: Team Deployment (Next Week - 4 hours)
- [ ] Document local vLLM setup for team
- [ ] Share HF Endpoint credentials securely
- [ ] Create deployment guide
- [ ] Setup CI/CD for model updates
- [ ] Monitor costs and usage

---

## Next Steps

**Immediate Action (Today)**:
```bash
# 1. Install vLLM
pip install vllm

# 2. Start local server
vllm serve Qwen/Qwen3-8B --dtype half --port 8000

# 3. Test speed
time curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen3-8B", "prompt": "Hello", "max_tokens": 50}'
```

Expected result: **3-5 second response** vs 45s on ZeroGPU

**This Week**:
1. Create local provider in CLI
2. Benchmark local vs ZeroGPU
3. Evaluate HF Inference Endpoint costs
4. Design deployment strategy

**Recommendation**: Start with **Option 1 (Full Hybrid)** for maximum flexibility and speed during development, with easy path to production deployment.

Would you like me to start implementing the local vLLM provider?
