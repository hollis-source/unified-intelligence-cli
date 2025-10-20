# Switching from Thinking to Instruct Model

**Date**: October 14, 2025
**Status**: Scripts updated, endpoint needs manual switch

---

## Summary

Switched all test generation scripts from **Qwen3-Next-80B-A3B-Thinking** to **Qwen3-Next-80B-A3B-Instruct**.

**Reason for switch**:
- Instruct version is optimized for direct task execution
- Faster inference (no thinking overhead)
- More focused outputs
- Better for production workloads

---

## Changes Made

### 1. Updated Scripts (12 files)
All scripts now use:
```python
config = {
    "model": "Qwen/Qwen3-Next-80B-A3B-Instruct",
    "thinking_mode": False
}
```

**Updated files**:
- `scripts/qwen_generate_phase1_tests.py`
- `scripts/qwen_generate_phase2_tests.py`
- `scripts/qwen_generate_phase3_tests.py`
- `scripts/qwen_generate_phase4_htnnode_tests.py`
- `scripts/qwen_generate_task_tests.py`
- `scripts/qwen_quick_phase2.py`
- `scripts/qwen_simple_generate.py`
- `scripts/ai_first_workflow.py`
- `scripts/dogfood_single_task.py`
- `scripts/test_qwen_endpoint.py`
- `scripts/resume_qwen_endpoint.py`
- `scripts/switch_to_instruct_model.py`

### 2. Updated Configuration
- `.env`: Updated comment to reflect Instruct endpoint

### 3. Provider Factory Default
- Already configured for Instruct: `src/factories/provider_creators.py` line 170
- Default: `Qwen/Qwen3-Next-80B-A3B-Instruct`
- Previous overrides removed from all scripts

---

## HF Inference Endpoint Update Required

**Current Status**:
- **Endpoint Name**: `qwen3-next-80b-a3b-thinking-rvs`
- **Current Model**: `Qwen/Qwen3-Next-80B-A3B-Thinking` ❌
- **Target Model**: `Qwen/Qwen3-Next-80B-A3B-Instruct` ✅

### Manual Switch Instructions

**Option A: Via HuggingFace Web UI** (Recommended)

1. Go to https://ui.endpoints.huggingface.co/hollis-source/endpoints
2. Click on endpoint: `qwen3-next-80b-a3b-thinking-rvs`
3. Click **"Settings"** tab
4. Under **"Model Repository"**, change to:
   ```
   Qwen/Qwen3-Next-80B-A3B-Instruct
   ```
5. Click **"Update Endpoint"**
6. Wait for redeployment (2-5 minutes)
7. Verify status shows "Running"

**Option B: Via Python Script** (Automated, but may timeout)

```bash
python3 scripts/switch_to_instruct_model.py
```

**Note**: Script timed out during pause operation (endpoint was busy). Use Web UI if automation fails.

**Option C: Create New Endpoint**

If updating existing endpoint fails:
1. Create new endpoint with Instruct model
2. Update `.env` with new endpoint URL
3. Delete old endpoint to save costs

---

## Verification

After endpoint is switched, test with:

```bash
python3 -c "
from src.factories.provider_factory import ProviderFactory

factory = ProviderFactory()
provider = factory.create_provider('qwen-agent')

response = provider.generate('Say \"Instruct model active!\" if you can read this.')
print(response.content if hasattr(response, 'content') else response)
"
```

Expected output: `"Instruct model active!"`

---

## Performance Comparison

| Model | Generation Speed | Output Style | Use Case |
|-------|-----------------|--------------|----------|
| **Thinking** | Slower (reasoning overhead) | Verbose with thinking process | Debugging, complex reasoning |
| **Instruct** | Faster (direct response) | Concise, focused | Production, task execution |

**For P2 Testing Infrastructure**:
- Phase 1-3: Used Thinking (now complete)
- Phase 4+: Will use Instruct (faster iteration)

**Expected speedup**: 1.5-2x faster generation time with Instruct.

---

## Impact on Existing Tests

**No changes needed** for existing tests:
- `tests/unit/entity/test_agent_comprehensive.py` (23 tests)
- `tests/unit/entity/test_task_comprehensive.py` (26 tests)
- `tests/unit/entity/test_agent_team_comprehensive.py` (46 tests)

All tests remain valid regardless of generation model.

---

## Next Steps

1. **Manually switch HF endpoint** (Web UI or script)
2. **Verify endpoint** with test command above
3. **Continue Phase 4** (HTNNode tests) with Instruct model
4. **Monitor performance** - compare generation times vs Thinking

---

## Rollback Instructions

If Instruct model doesn't work well:

1. **Revert scripts**:
   ```bash
   find scripts -name "*.py" -exec sed -i 's/Qwen3-Next-80B-A3B-Instruct/Qwen3-Next-80B-A3B-Thinking/g' {} +
   find scripts -name "*.py" -exec sed -i 's/"thinking_mode": False/"thinking_mode": True/g' {} +
   ```

2. **Switch endpoint back** to Thinking model via Web UI

3. **Update .env comment**

---

**Status**: ✅ Scripts updated, ⏳ Endpoint switch pending
