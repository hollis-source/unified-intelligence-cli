# A/B Results Report v0.1

This draft summarizes early A/B evaluations comparing RAG-enhanced routing to baseline team routing.

## Methodology
- Metric: domain classification accuracy = 1 if routing_decisions.task_domain equals expected template domain
- Test: two-proportion z-test; 95% CIs via Wilson; difference CI via Newcombe (Wilson-based)
- Sampling: N templates per domain; daily small-N, weekly larger-N across frontend, research, backend
- Latency: average, p50, p95; histogram bins for both conditions

## Dataset
- Daily CI: per-domain=2 (small-N)
- Weekly CI: per-domain=10 (larger)
- Provider: qwen3 (fast adapter)

## Results (latest daily sample)
- p_baseline = 0.00 (95% CI Wilson [0.00, 0.658])
- p_rag = 0.00 (95% CI Wilson [0.00, 0.658])
- diff (rag - baseline) = 0.00 (95% CI Newcombe [-0.658, 0.658])
- z = 0.00, p-value = 1.00

### Latency
- baseline avg=34.12s, p50=30.69s, p95=37.55s
- rag avg=14.18s, p50=13.89s, p95=14.47s
- latency histograms available in JSON

### Source diagnostics
- source_counts, accuracy_by_source
- classifier_agreement overall and by source

## Artifacts
- JSON: logs/ab_eval_*.json
- CSV: logs/ab_eval_*.csv
- Diff CSV: logs/ab_eval_diff_*.csv
- Trends: logs/ab_trends_*.{md,json}

## Interpretation notes
- Prefer Wilson/Newcombe intervals for small-N
- Use weekly runs for significance; daily for liveness
- Investigate sources with low agreement or skew

## Next steps
- Gather next daily and weekly artifacts and populate Results
- Compare diff CI against 0 and p-value < 0.05
- Evaluate latency trade-offs

