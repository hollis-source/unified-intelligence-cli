# RAG vs Baseline Routing A/B (Pilot)

This document summarizes a pilot A/B test comparing RAG-enabled routing against the baseline.

## Method
- Conditions:
  - Baseline: src.main without `--enable-rag`
  - RAG: src.main with `--enable-rag`
- Metric: Domain classification accuracy = 1 if `routing_decisions.task_domain` matches the expected domain inferred from the task template.
- Statistical test: Two-proportion z-test (two-sided) using normal approximation.
- Sampling: Small pilot (1 task per domain) across up to 3 domains.
- Implementation: `scripts/ab_routing_eval.py`

## Pilot Run (Small N)
Command:
```
python scripts/ab_routing_eval.py --domains frontend research backend --per-domain 1 --provider qwen3
```

Output (JSON):
```
{
  "domains": ["frontend", "research", "backend"],
  "per_domain": 1,
  "n_per_condition": 2,
  "baseline_hits": 0,
  "rag_hits": 0,
  "p_a": 0.0,
  "p_b": 0.0,
  "z": 0.0,
  "p_value": 1.0
}
```

Notes:
- Sample was very small (n=2 per condition in this run due to available templates), so results are not conclusive.
- The pipeline executed end-to-end and produced analyzable output.

## Next Steps
- Increase per-domain sample size to >= 5 (e.g., `--per-domain 5`) across at least 3 domains.
- Report confidence intervals alongside p-values.
- Consider alternative accuracy definitions (e.g., success-based) and additional metrics (latency, cost proxy, agent/role consistency).
- Archive experiment outputs (JSON + logs) in CI artifacts for traceability.


## Statistical Notes

- Proportion CIs: Normal approximation and Wilson score intervals (95%).
- Difference in proportions CI: Newcombe (1998) Method 10 using Wilson intervals per group.
  - If [l_a, u_a] and [l_b, u_b] are the Wilson 95% CIs for p_a and p_b respectively,
    then the 95% CI for (p_b − p_a) is [l_b − u_a, u_b − l_a].
- Reference: Newcombe, R.G. (1998). Two-sided confidence intervals for the single proportion: comparison of seven methods. Statistics in Medicine 17:857–872.


## Troubleshooting sparse routing_decisions

Symptom: routing_decisions has few rows; accuracy appears blank or inconsistent.

Why it happens:
- Baseline runs often do not persist routing_decisions (by design). The evaluator falls back to execution_log.routing_domain.
- Previously, RAG route_with_rag() did not track when no patterns were found. It now tracks a fallback decision (strategy="fallback", rag_used=false).

What to do:
- Inspect `source_counts` in the JSON report to see how many domains came from routing_decisions vs execution_log.
- Optionally enable baseline decision tracking (behind a flag) to persist baseline routing_decisions with strategy="baseline".
- Use `scripts/routing_decisions_summary.py` to view grouped counts by rag_used and routing_strategy.

## Domain normalization rules

**Critical**: Inconsistent domain strings can skew accuracy (e.g., "test" vs "testing" caused 0% accuracy in initial A/B test). The evaluator normalizes domains before comparison using `normalize_domain()` in `scripts/ab_routing_eval.py`.

### Normalization Mappings

**Synonym mappings**:
```python
"test"              → "testing"
"tests"             → "testing"
"quality"           → "qa"
"quality-assurance" → "qa"
```

**Canonical domains** (pass through unchanged):
```
testing, qa, frontend, backend, devops, research,
documentation, security, performance, category-theory,
dsl, architecture, general, unknown
```

**Case handling**: All domains are lowercased and whitespace-trimmed before normalization.

### Directory → Domain Mapping

Path-based inference (from `TaskTemplate._infer_domain()`):
```
tasks/test/         → testing
tasks/testing/      → testing
tasks/qa/           → qa
tasks/frontend/     → frontend
tasks/backend/      → backend
tasks/database/     → backend
tasks/python/       → backend
tasks/devops/       → devops
tasks/research/     → research
tasks/architect/    → architecture
```

### Tag-based Inference

When path doesn't match, tags are checked (in order of precedence):
```
Tags: [react, ui]              → frontend
Tags: [api, database]          → backend
Tags: [test, testing]          → testing
Tags: [qa, acceptance]         → qa
Tags: [ci, deployment]         → devops
Tags: [adr, benchmarking]      → research
Tags: [architecture]           → architecture
```

### Validation

Automated tests ensure consistency:
- `tests/unit/test_domain_normalization.py`: 35 tests for normalize_domain() and TaskTemplate inference
- `tests/unit/test_template_domain_consistency.py`: Validates all 118 task files
- `tests/unit/test_team_router_domain_mapping.py`: Ensures all classifier domains have team mappings

**Run validation**:
```bash
pytest tests/unit/test_domain_normalization.py -v
pytest tests/unit/test_template_domain_consistency.py -v
```

## Interpreting confidence intervals

### Overview

The A/B evaluator reports multiple types of confidence intervals (CIs) to handle small sample sizes robustly.

**Confidence intervals provided**:
- `p_a_ci95`: Normal approximation 95% CI for baseline accuracy
- `p_b_ci95`: Normal approximation 95% CI for RAG accuracy
- `p_a_ci95_wilson`: Wilson score 95% CI for baseline accuracy (better for small N)
- `p_b_ci95_wilson`: Wilson score 95% CI for RAG accuracy (better for small N)
- `diff_ci95`: Normal approximation CI for difference (RAG - baseline)
- `diff_ci95_wilson_newcombe`: Newcombe (1998) Wilson-based CI for difference (recommended)

### When to Use Which CI

**Small samples (n < 30 per condition)**:
- ✅ Use Wilson CIs for individual proportions (`p_a_ci95_wilson`, `p_b_ci95_wilson`)
- ✅ Use Newcombe CI for difference (`diff_ci95_wilson_newcombe`)
- ❌ Avoid normal approximation CIs (unreliable for small N)

**Large samples (n >= 30 per condition)**:
- ✅ Both Wilson and normal approximation CIs are acceptable
- ✅ Normal CIs may be slightly more conservative

### Interpreting Statistical Significance

**P-value interpretation**:
```
p < 0.01: Strong evidence of difference (99% confidence)
p < 0.05: Significant evidence of difference (95% confidence)
p < 0.10: Weak evidence of difference (90% confidence)
p >= 0.10: No significant evidence of difference
```

**Z-score interpretation**:
```
|z| > 2.58: Significant at 99% level (p < 0.01)
|z| > 1.96: Significant at 95% level (p < 0.05)
|z| > 1.64: Significant at 90% level (p < 0.10)
|z| ≤ 1.64: Not significant
```

**Confidence interval interpretation**:
```
Newcombe CI excludes 0: Significant difference at 95% level
Newcombe CI includes 0: No significant difference
CI width > 0.2: Large uncertainty (need more samples)
```

### Example Interpretation

**Scenario 1: Significant improvement**
```json
{
  "p_a": 0.65,
  "p_b": 0.82,
  "p_a_ci95_wilson": [0.52, 0.77],
  "p_b_ci95_wilson": [0.70, 0.91],
  "diff_p_b_minus_p_a": 0.17,
  "diff_ci95_wilson_newcombe": [0.03, 0.31],
  "z": 2.15,
  "p_value": 0.032
}
```
**Interpretation**:
- RAG accuracy (82%) is significantly higher than baseline (65%)
- Improvement: 17 percentage points (95% CI: [3%, 31%])
- p = 0.032 < 0.05 → statistically significant
- Newcombe CI excludes 0 → confirms significance

**Scenario 2: No significant difference**
```json
{
  "p_a": 0.70,
  "p_b": 0.75,
  "p_a_ci95_wilson": [0.55, 0.82],
  "p_b_ci95_wilson": [0.61, 0.86],
  "diff_p_b_minus_p_a": 0.05,
  "diff_ci95_wilson_newcombe": [-0.12, 0.22],
  "z": 0.58,
  "p_value": 0.562
}
```
**Interpretation**:
- RAG accuracy (75%) appears higher than baseline (70%)
- But difference (5%) is not statistically significant
- Newcombe CI includes 0 → inconclusive
- p = 0.562 >> 0.05 → need more samples

**Scenario 3: Wide CIs (underpowered)**
```json
{
  "p_a": 0.33,
  "p_b": 0.67,
  "p_a_ci95_wilson": [0.10, 0.65],
  "p_b_ci95_wilson": [0.35, 0.89],
  "diff_p_b_minus_p_a": 0.34,
  "diff_ci95_wilson_newcombe": [-0.05, 0.73],
  "z": 1.72,
  "p_value": 0.085
}
```
**Interpretation**:
- Large apparent improvement (34 percentage points)
- But CIs are very wide due to small sample (n=6)
- Difference is marginally significant (p = 0.085)
- **Action**: Increase sample size to n >= 15 per condition

### Latency Metrics

**Metrics provided**:
- `baseline_avg_latency_s`: Mean latency for baseline
- `baseline_p50_s`: Median latency (50th percentile)
- `baseline_p95_s`: 95th percentile latency (captures tail behavior)
- Same metrics for RAG condition

**Interpretation**:
- **P50 (median)**: Typical performance
- **P95**: Worst-case performance (important for SLAs)
- **Avg**: Overall average (can be skewed by outliers)

**Histogram bins** (via `--bins` flag):
- Default: 10 bins
- Increase for larger sample sizes (e.g., `--bins 20` for n > 50)
- Decrease for very small samples (e.g., `--bins 5` for n < 15)

## Reproducibility checklist

- Pin provider/model where possible for comparability
- Keep per-domain sample sizes balanced
- Save artifacts: JSON, CSV, diff CSV, routing summary
- Record domain source counts (routing_decisions vs execution_log)
