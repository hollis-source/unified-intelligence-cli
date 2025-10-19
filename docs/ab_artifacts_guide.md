# A/B Evaluation Artifacts Guide

This quick guide explains what artifacts the evaluator produces and how to inspect them.

## Files produced

- logs/ab_eval_<timestamp>.json
  - Main report for a single run (daily/weekly/smoke)
  - Contains fields: p_baseline, p_rag, diff_p_rag_minus_baseline, CIs, latency stats, histograms, source diagnostics, classifier agreement
- logs/ab_eval_<timestamp>.csv
  - Flat summary: counts and proportions per run
- logs/ab_eval_diff_<timestamp>.csv
  - Diff summary: baseline vs RAG with Newcombe CI for the difference

## Key JSON fields

- p_baseline, p_rag (aliases: p_a, p_b)
- p_baseline_ci95_wilson, p_rag_ci95_wilson
- diff_p_rag_minus_baseline, diff_ci95_wilson_newcombe
- baseline_avg_latency_s, rag_avg_latency_s, p50/p95
- baseline_latency_hist, rag_latency_hist (bins + counts)
- source_counts: domain source counts by condition and total
- accuracy_by_source: per-source accuracy for baseline, rag, and total
- classifier_agreement: by_source and overall_rate

## Quick checks with jq

Show headline metrics:

- jq '.p_baseline, .p_rag, .diff_p_rag_minus_baseline' logs/ab_eval_*.json | paste - - -

Source counts and accuracies:

- jq '.source_counts, .accuracy_by_source' logs/ab_eval_*.json | less

Classifier agreement rates:

- jq '.classifier_agreement' logs/ab_eval_*.json | less

Latency distributions:

- jq '.baseline_latency_hist, .rag_latency_hist' logs/ab_eval_*.json | less

## Tips

- For small-N runs, prefer Wilson/Newcombe intervals for interpretation.
- Use --bins to adjust histogram resolution (default 10).
- Baseline decision tracking is enabled in CI; domain sources will show more routing_decisions entries over time.

