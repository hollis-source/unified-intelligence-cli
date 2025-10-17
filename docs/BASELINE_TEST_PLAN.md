# Baseline Test Plan (Week 1)

**Date:** 2025-10-16
**Status:** Ready to execute
**Philosophy:** Continuous improvement - measure with what we have, iterate

---

## Current State

**Tasks Available:** 21/100 (21%)
- ✅ Database Specialist: 20 tasks (db-01 to db-20)
- ✅ Python Engineer: 1 task (py-01)
- ⏳ Software Architect: 0 tasks (generating)
- ⏳ Test Engineer: 0 tasks (generating)
- ⏳ DevOps Engineer: 0 tasks (generating)

**Metrics Harness:** Ready (40% functionality)
- ✅ Task execution via CLI
- ✅ Basic AutoChecks scoring
- ✅ Metrics collection (latency, tokens, specificity, quality)
- ✅ JSONL logging
- ✅ Rollup aggregation

---

## Baseline Test (21 Tasks)

### Objective

Measure initial agent performance to establish baseline metrics for continuous improvement.

**Target:** 20% completion rate, 5.0 quality score (Week 1 baseline)

### Execution Plan

#### Phase 1: Database Specialist Baseline (20 tasks)

```bash
# Execute all database tasks
python scripts/metrics_harness.py \
    --tasks "tasks/database/*.yaml" \
    --output metrics/week1_database_baseline.jsonl \
    --verbose
```

**Expected Duration:** 20 tasks × ~60s average = ~20 minutes
**Expected Metrics:**
- Completion rate: 10-30% (target: 20%)
- Quality score: 4.0-6.0 (target: 5.0)
- Latency p95: 90-120s
- Cost per task: 6k-10k tokens
- Specificity: 50-70%

#### Phase 2: Python Engineer Baseline (1 task)

```bash
# Execute Python task
python scripts/metrics_harness.py \
    --tasks "tasks/python/py-01.yaml" \
    --output metrics/week1_python_baseline.jsonl \
    --verbose
```

**Expected Duration:** ~2 minutes
**Expected Metrics:**
- Completion rate: 0-50% (single task, binary outcome)
- Quality score: 4.0-7.0
- Latency: 60-120s

#### Phase 3: Combined Rollup

```bash
# Merge metrics and compute aggregate
cat metrics/week1_database_baseline.jsonl \
    metrics/week1_python_baseline.jsonl \
    > metrics/week1_combined.jsonl

# Analyze
python scripts/analyze_metrics.py metrics/week1_combined.jsonl
```

---

## Validation Criteria

### Success Criteria (Week 1 Baseline)

| Metric | Minimum Acceptable | Target | Stretch |
|--------|-------------------|--------|---------|
| Database completion rate | 10% (2/20 tasks) | 20% (4/20) | 30% (6/20) |
| Database quality score | 4.0/10 | 5.0/10 | 6.0/10 |
| Python completion rate | 0% (0/1) | 50% (1/1) | 100% (1/1) |
| Overall latency p95 | <180s | <120s | <90s |
| Cost per task | <12k tokens | <10k | <8k |

### Failure Criteria (Need Immediate Action)

- **All tasks fail** (0% completion): Agent routing broken, check CLI integration
- **All timeouts** (latency >300s): LLM provider issue, check API status
- **All low quality** (<3.0): Prompt quality issue, review agent prompts
- **Zero specificity** (0%): Missing file:line references, update prompt template

---

## Post-Baseline Actions

### If Baseline Meets Target (20% completion, 5.0 quality)

1. **Celebrate** - We're on track!
2. **Analyze failures** - Which tasks failed and why?
3. **Identify improvement targets** - Use ROI heuristic
4. **Iterate prompts** - Improve based on failure modes
5. **Run Week 2 test** - Target 40% completion, 6.0 quality

### If Baseline Below Target (<20% completion)

1. **Failure analysis** - Categorize failures:
   - Routing errors (task went to wrong agent)
   - Quality errors (task completed but low quality)
   - Timeout errors (task exceeded time limit)
   - Check errors (task passed but failed validation)

2. **Root cause investigation**:
   - Review failed task outputs
   - Check agent prompts for clarity
   - Validate CLI integration
   - Verify LLM provider status

3. **Quick fixes**:
   - Update agent prompts for common failures
   - Adjust timeout if needed
   - Fix routing issues

4. **Re-test** - Run baseline again with fixes

### If Baseline Above Target (>30% completion)

1. **Great!** - But don't get complacent
2. **Verify quality** - High completion doesn't mean high quality
3. **Check for false positives** - Are checks too lenient?
4. **Increase difficulty** - Add more challenging tasks
5. **Accelerate timeline** - Move to Week 2 targets faster

---

## Metrics Collection Format

### JSONL Record Example

```json
{
  "timestamp": "2025-10-16T12:00:00Z",
  "task_id": "db-01",
  "agent": "database",
  "ok": true,
  "latency": 42.1,
  "tokens": 5632,
  "specific": true,
  "auto_score": 7.2,
  "human_score": null,
  "quality": 7.1,
  "checks_ok": true,
  "completed": true,
  "output_length": 2456,
  "error": null
}
```

### Rollup Metrics Example

```
================================================================================
AGENT PERFORMANCE ROLLUP (Week 1 Baseline)
================================================================================
Agent           Rate     Quality  P95(s)   Tokens   Spec%
--------------------------------------------------------------------------------
database         25.0%    5.4/10   95.2s    7234t    65.0%
python           100.0%   7.8/10   78.5s    6845t    100.0%
--------------------------------------------------------------------------------
OVERALL          28.6%    5.6/10   94.8s    7198t    66.7%
================================================================================

Next optimization target: Completion rate (highest ROI)
```

---

## Timeline

**Phase 1 (Database):** ~20 minutes
**Phase 2 (Python):** ~2 minutes
**Phase 3 (Analysis):** ~5 minutes

**Total:** ~30 minutes end-to-end

**Recommendation:** Run baseline test NOW with 21 available tasks, don't wait for all 100.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| CLI integration broken | Low | High | Validate CLI manually first |
| LLM provider timeout | Medium | High | Use --timeout flag, retry logic |
| Tasks too difficult | Medium | Medium | Expected for baseline, iterate |
| AutoChecks too strict | Low | Medium | Review scoring logic |
| Agent routing fails | Low | High | Test routing with simple task first |

---

## Next Steps After Baseline

1. **Document results** - Create WEEK1_BASELINE_RESULTS.md
2. **Human evaluation** - Sample 5 database tasks for manual review
3. **Failure analysis** - Categorize and document failure modes
4. **Improvement iteration**:
   - Update agent prompts based on failures
   - Add more tasks for low-performing agents
   - Implement advanced AutoChecks
5. **Week 2 target** - 40% completion, 6.0 quality

---

**Ready to execute:** ✅
**Waiting for:** Python tasks generation (optional, can run with 21 tasks now)

*Continuous improvement: Measure → Analyze → Iterate → Improve*
