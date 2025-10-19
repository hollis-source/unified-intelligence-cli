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
