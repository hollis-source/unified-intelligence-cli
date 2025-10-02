# Model Selection Analysis - Qwen2.5-Coder vs General Model

**Issue Identified**: Training mixed-agent dataset on code-specialized model

---

## The Problem

### Training Data Distribution (Actual)

```
Total: 298 examples
- Coder:       174 (58%) ✅ Code generation tasks
- Tester:       76 (26%) ⚠️  Test writing (code-adjacent)
- Researcher:   26 (9%)  ⚠️  Analysis/investigation
- Coordinator:  20 (7%)  ⚠️  Planning/organization
- Reviewer:      2 (1%)  ⚠️  Code critique
```

**42% of training data is non-coding tasks** but we're using a **code-specialized model**.

### Model Selected

**Qwen2.5-Coder-7B-Instruct**
- Optimized for: Code generation, code completion, code explanation
- Training: Pre-trained on large code corpus (GitHub, Stack Overflow, etc.)
- Strength: Excellent at generating syntactically correct, well-structured code
- Weakness: May underperform on non-coding tasks (planning, research, critique)

---

## Why This Choice Was Made

### 1. Original Pipeline Recommendation

From `MODEL_TRAINING_STRATEGY_PIPELINE_ULTRATHINK.md`:

| Agent | Recommended Model |
|-------|-------------------|
| **Coder** | **Qwen2.5-Coder-7B** |
| Tester | Qwen2.5-7B (general) |
| Reviewer | Qwen2.5-14B (general) |
| Researcher | Tongyi-30B |
| Coordinator | Qwen2.5-14B (general) |

**Original plan**: Agent-specific fine-tuning (one model per agent type)
**Actual implementation**: Single model for all agents (mixed dataset)

### 2. Majority is Coder Tasks

- 58% of training data is coder tasks
- Seemed reasonable to optimize for the majority use case

### 3. All Tasks Are Software-Related

Even non-coder tasks are in the software engineering domain:
- Tester: Writing pytest tests (code-adjacent)
- Researcher: Investigating frameworks, comparing approaches (technical)
- Coordinator: Planning sprints, breaking down features (technical planning)
- Reviewer: Code review, SOLID analysis (technical critique)

**Assumption**: Code-specialized model might still handle these well since they're all software-eng tasks.

---

## Alternative: Qwen2.5-7B-Instruct (General Model)

### What Would Be Different

**Qwen2.5-7B-Instruct** (without -Coder):
- General instruction-following model
- Trained on diverse tasks: writing, reasoning, analysis, planning, coding
- **Better for**: Mixed workloads across different task types
- **Trade-off**: Slightly less optimized for pure code generation

### Comparison

| Aspect | Qwen2.5-Coder-7B | Qwen2.5-7B-Instruct |
|--------|------------------|---------------------|
| **Code generation** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Very Good |
| **Test writing** | ⭐⭐⭐⭐ Very Good | ⭐⭐⭐⭐ Very Good |
| **Research tasks** | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Very Good |
| **Planning tasks** | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Very Good |
| **Code review** | ⭐⭐⭐⭐ Very Good | ⭐⭐⭐⭐ Very Good |
| **Mixed workload** | ⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Excellent |

**Verdict**: Qwen2.5-7B-Instruct would have been **more appropriate** for our mixed dataset.

---

## Impact Assessment

### Potential Issues

1. **Tester Tasks (26%)**: May be fine since test writing is code generation
2. **Researcher Tasks (9%)**: May underperform on analysis/investigation tasks
3. **Coordinator Tasks (7%)**: May underperform on planning/organization
4. **Reviewer Tasks (1%)**: Small sample, impact minimal

**Estimated impact**: 16% of dataset (researcher + coordinator) may see degraded performance.

### Mitigating Factors

✅ **Instruct variant**: Qwen2.5-Coder-**Instruct** has general instruction-following tuning
✅ **LoRA fine-tuning**: Will adapt to our specific task distribution
✅ **Software domain**: All tasks are software-eng related, within -Coder's domain
✅ **Small sample**: Only 46 non-coding examples (researcher + coordinator)

**Likely outcome**: Model will still perform reasonably well, but may show weakness on research/planning tasks.

---

## What To Watch During Evaluation

After training completes, **evaluate separately by agent type**:

```bash
# Evaluate by agent (when we create the script)
python3 training/scripts/evaluate_by_agent.py \
  --model training/models/qwen2.5-coder-7b-lora/final_model \
  --test-data training/data/test.jsonl
```

**Expected results**:
- ✅ **Coder tasks**: Excellent (model strength + 58% of training data)
- ✅ **Tester tasks**: Very good (code-adjacent)
- ⚠️  **Researcher tasks**: May be weaker (only 9% of data, model not optimized)
- ⚠️  **Coordinator tasks**: May be weaker (only 7% of data, model not optimized)
- ⚠️  **Reviewer tasks**: Unknown (only 1% of data)

---

## Decision Tree: What To Do If Performance Is Poor

### Scenario 1: Overall Performance Meets Targets (≥98% success, <12s avg)

**Action**: ✅ **Deploy as-is**
- Even if some agent types underperform, overall target met
- Can iterate later if specific issues arise

### Scenario 2: Researcher/Coordinator Tasks Fail, Coder/Tester Succeed

**Action**: 🔄 **Hybrid approach**
- Deploy Qwen2.5-Coder-7B-LoRA for coder/tester tasks
- Use baseline (Llama 3.1) for researcher/coordinator tasks
- Agent-specific routing

### Scenario 3: Overall Performance Below Targets

**Action**: 🔄 **Retrain with general model**
- Train new LoRA on **Qwen2.5-7B-Instruct** (general, not -Coder)
- Same training data, same config
- Estimated time: Another 6-8 hours
- Compare both models

### Scenario 4: Code Tasks Also Underperform

**Issue**: Not model selection, likely data quality or config
**Action**:
- Review training data quality
- Check for overfitting (validation loss)
- Try different LoRA hyperparameters

---

## Recommendation: Let Training Complete

**Current status**: 18% complete (8/45 steps), ~5 hours remaining

**Recommendation**:
1. ✅ **Let current training finish** (sunk cost: 1.5 hours)
2. 📊 **Evaluate comprehensively** by agent type
3. 🤔 **Make data-driven decision**:
   - If targets met → Deploy
   - If researcher/coordinator weak → Hybrid or retrain
   - If all weak → Retrain with Qwen2.5-7B-Instruct

**Alternative if you want to stop now**:
- Kill training: `kill $(cat training/training.pid)`
- Change model to `Qwen2.5-7B-Instruct` in training script
- Restart training (~7-8 hours)
- Total time saved: ~1 hour (not significant)

---

## Lessons Learned

### For Future Training Runs

1. **Match model specialization to data distribution**:
   - Mixed dataset (40%+ non-coding) → General model
   - Pure coding dataset (>80% coding) → Code-specialized model

2. **Agent-specific training is better**:
   - Train separate LoRA adapters per agent type
   - Use appropriate base model for each
   - More complex but higher quality

3. **Evaluate model capabilities first**:
   - Test base model on sample tasks before committing to training
   - Check if specialization aligns with actual data

---

## Summary

**Issue**: Using code-specialized model (Qwen2.5-Coder-7B) on mixed dataset (42% non-coding)

**Why**: Original pipeline recommended agent-specific training; we implemented single-model approach

**Impact**: Potentially reduced performance on researcher (9%) and coordinator (7%) tasks

**Mitigation**:
- Instruct variant has general capabilities
- LoRA will adapt to our data
- Software-eng domain alignment

**Recommendation**:
- ✅ Complete current training (5 hours remaining)
- 📊 Evaluate by agent type
- 🤔 Decide based on results:
  - Deploy if targets met
  - Retrain with Qwen2.5-7B-Instruct if non-coding tasks fail

**Best practice**: For mixed workloads, use general instruction model, not specialized.

---

**Status**: Issue documented, training continues
**Next action**: Comprehensive evaluation after training (by agent type)
