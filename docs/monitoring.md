# Monitoring & Adjustment

This guide outlines cadence and inputs for ongoing monitoring.

## Cadence
- Daily: Metrics Daily workflow builds trend + advanced snapshots
- Weekly: A/B evaluation runs larger-N experiment and uploads advanced metrics
- Monthly: DB audit of routing_decisions and agent_performance (manual)

## Inputs
- A/B: logs/ab_eval_*.{json,csv}, diff CSVs
- Trends: logs/ab_trends_*.{md,json}
- Advanced: logs/advanced_metrics_*.{md,json}
- Success criteria: logs/success_criteria_*.{md,json}

## Actions
- Investigate domains with negative drift diffs
- Check agent leaderboard for regressions in success_rate/latency
- Weekly success criteria snapshot: runs in A/B weekly workflow via scripts/success_criteria_check.py; artifacts uploaded as success-criteria-weekly

- Re-run weight optimization and measure before/after error rate
- Expand per-domain sample sizes when budget allows

