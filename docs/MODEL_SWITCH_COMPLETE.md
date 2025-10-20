# Model Switch: Thinking → Instruct - Complete

**Date**: October 14, 2025
**Status**: ✅ Code updated, ⏳ Endpoint switch required

---

## Summary

Successfully updated all scripts and configuration from **Qwen3-Next-80B-A3B-Thinking** to **Qwen3-Next-80B-A3B-Instruct**.

---

## Changes Applied

### 1. Scripts Updated: 12 files

All test generation and development scripts now use:
```python
config = {
    "model": "Qwen/Qwen3-Next-80B-A3B-Instruct",
    "thinking_mode": False
}
```

**Updated files**:
1. `scripts/qwen_generate_phase1_tests.py`
2. `scripts/qwen_generate_phase2_tests.py`
3. `scripts/qwen_generate_phase3_tests.py`
4. `scripts/qwen_generate_phase4_htnnode_tests.py`
5. `scripts/qwen_generate_task_tests.py`
6. `scripts/qwen_quick_phase2.py`
7. `scripts/qwen_simple_generate.py`
8. `scripts/ai_first_workflow.py`
9. `scripts/dogfood_single_task.py`
10. `scripts/test_qwen_endpoint.py`
11. `scripts/resume_qwen_endpoint.py`
12. `scripts/switch_to_instruct_model.py`

### 2. Configuration Files
- ✅ `.env`: Comment updated to "Qwen3-Next-80B-A3B-Instruct Endpoint"
- ✅ `src/factories/provider_creators.py`: Already defaulted to Instruct (line 170)

### 3. Documentation
- ✅ Created `docs/SWITCH_TO_INSTRUCT_GUIDE.md` (comprehensive guide)
- ✅ Created `docs/MODEL_SWITCH_COMPLETE.md` (this file)

### 4. Helper Scripts
- ✅ Created `scripts/switch_to_instruct_model.py` (automated endpoint update)
- ✅ Created `scripts/update_to_instruct.sh` (bulk script updater)

---

## Verification Results

```bash
✅ 12 scripts updated with Instruct model
✅ 12 scripts have thinking_mode=False
✅ 0 remaining Thinking model references
✅ All imports use correct model name
```

---

## HF Inference Endpoint - Action Required

**Current State**:
- Endpoint: `qwen3-next-80b-a3b-thinking-rvs`
- URL: `https://crlqq5n5zwaz4rnh.us-east-2.aws.endpoints.huggingface.cloud/v1`
- Model: **Qwen/Qwen3-Next-80B-A3B-Thinking** ❌ (needs update)

**Required Action**: Manually switch endpoint to Instruct model

### Option 1: HuggingFace Web UI (Recommended)

1. Visit: https://ui.endpoints.huggingface.co/hollis-source/endpoints
2. Select endpoint: `qwen3-next-80b-a3b-thinking-rvs`
3. Settings → Model Repository → Change to:
   ```
   Qwen/Qwen3-Next-80B-A3B-Instruct
   ```
4. Click "Update Endpoint"
5. Wait 2-5 minutes for redeployment

### Option 2: Python Script (If Web UI unavailable)

```bash
python3 scripts/switch_to_instruct_model.py
```

**Note**: Script may timeout if endpoint is busy. Use Web UI in that case.

---

## Testing After Switch

Once endpoint is updated, verify with:

```bash
python3 -c "
from src.factories.provider_factory import ProviderFactory

factory = ProviderFactory()
provider = factory.create_provider('qwen-agent')

response = provider.generate('Say exactly: Instruct model active!')
print(response.content if hasattr(response, 'content') else response)
"
```

**Expected output**: `"Instruct model active!"`

---

## Performance Expectations

| Aspect | Thinking Model | Instruct Model | Change |
|--------|---------------|----------------|--------|
| **Generation Time** | 46-53 seconds | 30-40 seconds (est.) | ~30% faster |
| **Output Style** | Verbose (thinking + code) | Concise (direct code) | Cleaner |
| **Token Usage** | Higher (thinking overhead) | Lower (no thinking) | ~50% reduction |
| **Quality** | Very high (reasoning visible) | High (optimized) | Comparable |
| **Debugging** | Easy (see reasoning) | Harder (no reasoning) | Trade-off |

**For P2 Testing**:
- Phases 1-3: Used Thinking (completed, 95 tests)
- Phases 4+: Will use Instruct (faster iteration)

---

## Impact Assessment

### ✅ Positive Impacts
1. **Faster iteration**: ~30% reduction in generation time
2. **Cleaner output**: No thinking contamination in code
3. **Lower costs**: ~50% fewer tokens per request (flat rate, but better efficiency)
4. **Production-ready**: Instruct optimized for task execution

### ⚠️ Trade-offs
1. **Less transparency**: No visible reasoning process
2. **Harder debugging**: Can't see model's thinking when errors occur
3. **Possibly lower quality**: Thinking mode may catch more edge cases

### ℹ️ Neutral
- Existing tests unchanged (still valid)
- API compatibility maintained
- No code refactoring needed

---

## Rollback Plan

If Instruct model underperforms:

1. **Revert scripts** (automated):
   ```bash
   find scripts -name "*.py" -exec sed -i 's/Instruct/Thinking/g' {} +
   find scripts -name "*.py" -exec sed -i 's/False/True/g' {} +
   ```

2. **Switch endpoint back** via Web UI or script

3. **Monitor quality** for 2-3 test generations before deciding

---

## Next Steps

1. ✅ **Code updated** (complete)
2. ⏳ **Switch endpoint** (manual action required)
3. ⏳ **Verify with test** (after endpoint switch)
4. ⏳ **Continue Phase 4** (HTNNode tests) with Instruct
5. ⏳ **Monitor quality** (compare vs Thinking results)

---

## Files Created/Modified

**Created**:
- `docs/SWITCH_TO_INSTRUCT_GUIDE.md` (detailed guide)
- `docs/MODEL_SWITCH_COMPLETE.md` (this summary)
- `scripts/switch_to_instruct_model.py` (automation script)
- `scripts/update_to_instruct.sh` (bulk updater)

**Modified**:
- `.env` (comment update)
- 12 test generation scripts (model + thinking_mode)

---

**Status**: ✅ **Code changes complete**, ready for endpoint switch
**Estimated time to switch**: 5 minutes (Web UI) or 10 minutes (script)
**Total impact**: 12 scripts, 0 test changes, minimal risk
