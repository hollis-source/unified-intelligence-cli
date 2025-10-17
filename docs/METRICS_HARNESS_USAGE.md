# Metrics Harness Usage Guide

**Status:** Baseline implementation complete (v0.1)
**Date:** 2025-10-16
**Based on:** docs/AGENT_METRICS_SYSTEM.md (Task 2, GPT-5)

---

## Overview

The metrics harness executes agent tasks, collects performance metrics, and tracks continuous improvement over time.

**Current Functionality:** ~40%
- ✅ Task execution via CLI
- ✅ Check validation (regex, cmd)
- ✅ Basic AutoChecks scoring
- ✅ Metrics collection (latency, tokens, specificity, quality)
- ✅ JSONL logging
- ✅ Rollup aggregation
- ⏳ Human evaluation integration (pending)
- ⏳ Advanced AutoChecks (lint, test, coverage) (pending)
- ⏳ Dashboard visualization (pending)

---

## Quick Start

### Execute Single Task

```bash
python scripts/metrics_harness.py \
    --tasks tasks/database/db-01.yaml \
    --verbose
```

### Execute Full Database Specialist Suite

```bash
python scripts/metrics_harness.py \
    --tasks "tasks/database/*.yaml" \
    --output metrics/database_baseline.jsonl
```

### Execute All Tasks

```bash
python scripts/metrics_harness.py \
    --tasks "tasks/**/*.yaml" \
    --output metrics/week1_baseline.jsonl
```

---

## Output

### JSONL Record Format

Each task execution produces one line in the JSONL file:

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

### Rollup Metrics

After execution, prints aggregate metrics per agent:

```
================================================================================
AGENT PERFORMANCE ROLLUP
================================================================================
Agent           Rate     Quality  P95(s)   Tokens   Spec%
--------------------------------------------------------------------------------
database         45.0%    6.8/10   89.2s    6234t    72.0%
python           30.0%    6.2/10  112.5s    7845t    68.5%
================================================================================
```

---

## Metrics Definitions

| Metric | Formula | Target (Week 0 → Week 4) |
|--------|---------|--------------------------|
| **Completion Rate (%)** | completed_tasks / attempted_tasks × 100 | 20% → 80%+ |
| **Quality Score (1-10)** | 0.6 × AutoChecks + 0.4 × Human | 5.0 → 8.0+ |
| **Latency P95 (seconds)** | 95th percentile of response times | ≤120s → ≤60s |
| **Cost (tokens)** | mean(prompt_tokens + completion_tokens) | ≤10k → ≤6k |
| **Specificity (%)** | responses with file:line refs / total × 100 | ≥70% (code), ≥40% (research) |

---

## AutoChecks Scoring (0-10)

### Current Implementation (Baseline)

Basic quality indicators:
- **Output length** (2 points): Substantial response (>200 chars)
- **Code blocks** (2 points): Contains code/examples
- **Specificity** (1 point): Has file:line references
- **Agent-specific** (5 points): Domain-specific indicators

### Planned Improvements

#### Python Engineer
- Lint/format pass (ruff/flake8/black): 0-2
- Static typing (mypy/pyright) pass: 0-2
- Tests pass on modified scope: 0-3
- Complexity/duplication improvement: 0-2
- Specificity (file:line, code excerpts): 0-1

#### Database Specialist
- Schema validity (SQLFluff, dbdiagram): 0-3
- Query performance (EXPLAIN ANALYZE): 0-2
- Migration safety (reversible, no data loss): 0-2
- Normalization (3NF+ compliance): 0-2
- Specificity (table/column/query refs): 0-1

#### Software Architect
- Clean Architecture alignment: 0-3
- Artifacts present (C4/ADRs): 0-2
- Traceability (decisions ↔ requirements): 0-2
- Feasibility (implementation-ready): 0-2
- Specificity (repo/file anchors): 0-1

#### Test Engineer
- New/updated tests run green: 0-4
- Coverage delta (+X%): 0-3
- Test quality (AAA, determinism, speed): 0-2
- Specificity (targeted files, lines): 0-1

#### DevOps Engineer
- CI config validity (actionlint/yamllint): 0-3
- Pipeline success (dry-run): 0-3
- Idempotency/safety checks: 0-2
- Observability (logs/alerts): 0-1
- Specificity (env/manifest refs): 0-1

---

## Acceptance Thresholds

Task counts as "completed" when:

| Agent | AutoChecks | Human | Required Checks |
|-------|-----------|-------|-----------------|
| Python Engineer | ≥6 | ≥6 | All must pass |
| Software Architect | ≥5 | ≥7 | All must pass |
| Test Engineer | ≥6 | ≥6 | All must pass |
| Database Specialist | ≥6 | ≥6 | All must pass |
| DevOps Engineer | ≥6 | ≥6 | All must pass |

---

## Human Evaluation (Pending)

Human evaluation dimensions (2 points each, 0-10 total):
1. **Correctness** - Factually accurate, solves the problem
2. **Completeness** - Addresses all requirements, no gaps
3. **Clarity/Structure** - Well-organized, easy to understand
4. **Specificity/Actionability** - Concrete, with file:line references
5. **Safety/Best Practices** - Follows conventions, avoids anti-patterns

### Workflow

1. Execute tasks with metrics harness
2. Sample 5 tasks per agent per week for human review
3. Rate each task on 5 dimensions
4. Record ratings in `metrics/human_ratings.csv`:

```csv
agent,task_id,correctness,completeness,clarity,specificity,safety,human_score
database,db-01,2,2,2,1,2,9
database,db-02,1,2,2,2,1,8
```

5. Re-run rollup to merge human scores:

```bash
python scripts/merge_human_ratings.py \
    --metrics metrics/week1_baseline.jsonl \
    --ratings metrics/human_ratings.csv \
    --output metrics/week1_complete.jsonl
```

---

## Continuous Improvement Workflow

### Week 1: Baseline (20% functionality)

```bash
# Execute 50 tasks (10 per agent)
python scripts/metrics_harness.py \
    --tasks "tasks/*/db-0[12].yaml tasks/*/py-01.yaml" \
    --output metrics/week1_baseline.jsonl

# Expected: 20% completion rate, 5.0 quality
```

### Week 2: First Iteration (40% functionality)

```bash
# Identify lowest-performing agents
python scripts/analyze_metrics.py metrics/week1_baseline.jsonl

# Improve prompts based on failure modes
# Add 10 more tasks per agent

# Re-measure
python scripts/metrics_harness.py \
    --tasks "tasks/**/*.yaml" \
    --output metrics/week2_iteration1.jsonl

# Expected: ≥1 agent reaches 40% completion rate
```

### Week 3: Measure and Evaluate (60% functionality)

```bash
# Run full 100-task suite
python scripts/metrics_harness.py \
    --tasks "tasks/**/*.yaml" \
    --output metrics/week3_full.jsonl

# Analyze where agents struggle
python scripts/failure_analysis.py metrics/week3_full.jsonl

# Decision: Add LangGraph? Add RAG? Keep iterating?
```

---

## Next Optimization Target

Use ROI heuristic to determine what to improve next:

```python
def next_target(rollup):
    goals = {"rate": 80, "p95": 60, "cost": 6000, "spec": 70}
    effort = {"rate": 3, "p95": 2, "cost": 2, "spec": 1}

    gaps = {
        k: max(0, goals[k] - v) if k != "p95" else max(0, v - goals[k])
        for k, v in rollup.items()
    }

    roi = {k: (gaps[k] / max(effort[k], 1)) for k in goals}

    return max(roi, key=roi.get)
```

**Example:**
- Completion rate: 30% (gap: 50, effort: 3, ROI: 16.7)
- Latency p95: 90s (gap: 30, effort: 2, ROI: 15.0)
- Cost: 8000 tokens (gap: 2000, effort: 2, ROI: 1000)
- Specificity: 50% (gap: 20, effort: 1, **ROI: 20.0** ← highest)

**Next target:** Specificity (prompt agents to include file:line references)

---

## Troubleshooting

### Issue: Tasks timeout

**Solution:** Increase timeout in CLI command:

```python
# In metrics_harness.py, line ~100
"--timeout", str(600)  # 10 minutes
```

### Issue: AutoChecks always return same score

**Solution:** Implement agent-specific checks. See `compute_auto_checks()` function.

### Issue: CLI command not found

**Solution:** Adapt CLI invocation in `run_agent_task()`:

```python
cmd = [
    "python3", "-m", "src.main",
    "--agent", agent,
    "--task", prompt,
    # ... adjust flags for your system
]
```

---

## Architecture

```
metrics_harness.py
├── load_task(path) → dict
├── run_agent_task(agent, prompt) → {ok, latency, output, usage}
├── run_check(check, output) → bool
├── compute_auto_checks(agent, output, dir) → float[0-10]
├── compute_quality(auto, human) → float[0-10]
├── is_completed(agent, quality, checks_ok) → bool
├── execute_task(path) → record
├── execute_suite(paths, output) → records[]
├── compute_rollup(records) → {agent: metrics}
└── print_rollup(rollup)
```

---

## Future Enhancements

1. **Dashboard** (Streamlit):
   - Real-time metrics visualization
   - Week-over-week trends
   - Agent comparison charts
   - Failure mode analysis

2. **Advanced AutoChecks**:
   - Integrate ruff, mypy, pytest
   - SQL validation with SQLFluff
   - YAML validation with yamllint
   - Coverage delta tracking

3. **Human Evaluation UI**:
   - Web interface for rating tasks
   - Inter-rater reliability tracking
   - Bulk rating tools

4. **Alerting**:
   - Slack notifications on regressions
   - GitHub issue creation for failures
   - Weekly rollup email reports

5. **Benchmarking**:
   - Compare against baseline
   - Track improvement velocity
   - Predict time to reach targets

---

**Current Status:** Baseline implementation complete (40% functionality)
**Next Steps:**
1. Test with existing 21 tasks (db-01 to db-20, py-01)
2. Implement human evaluation workflow
3. Add advanced AutoChecks (lint, test, coverage)
4. Build Streamlit dashboard

*Continuous improvement in action!*
