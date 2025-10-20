# Advanced RAG Metrics (Day 3–4)

This document explains the advanced metrics reported by scripts/advanced_metrics_report.py and how to interpret them.

## Running the report

- Local:
  - PYTHONPATH=. python scripts/advanced_metrics_report.py --limit 500
  - Outputs: logs/advanced_metrics_<timestamp>.{md,json}
- Requirements: SurrealDB accessible via env SURREALDB_URL or RAGConfig defaults.
- Graceful degrade: If DB unavailable, the report still emits structure with empty sections.

## Sections

1) Drift signals (domain accuracy)
- Compares per-domain routing accuracy across two recent windows of routing_decisions.
- Use as a canary for changes in behavior; investigate large negative diffs.
- Note: Without explicit timestamps, windows are by retrieval order (approximate).

2) Performance snapshots
- By agent: n, success_rate, avg_latency_s from execution_log.
- By domain: same aggregation grouped by task_domain.
- Agent leaderboard: from agent_performance table (if populated by feedback loop).

3) Cross-domain pattern transfer (heuristic)
- For RAG-used decisions, infers domains for top_pattern agent roles and compares to task_domain.
- Reports proportion where inferred domains differ (possible cross-domain transfer) and a few examples.
- Heuristic mapping: role strings containing keywords (frontend, backend, qa/testing, research, devops, architecture, data).

## Interpreting results
- Drift < 0.0 for a domain: investigate routing hints, new patterns, or data distribution changes.
- Agent leaderboard: validate that optimization changes reflect in success_rate and latency.
- Cross-domain transfer: a moderate rate can indicate generalizable patterns; very high rate might flag domain leakage or misclassification.

## Next steps
- If drift detected: re-check domain normalization, classifier agreement, and pattern retrieval thresholds.
- If performance regressions occur: inspect recent optimization patterns and adjust weights.
- Consider scheduling this report post-weekly A/B to publish artifacts automatically.

