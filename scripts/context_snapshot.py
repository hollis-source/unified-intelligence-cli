#!/usr/bin/env python3
"""
Context Snapshot CLI
- Runs the analysis/context_aggregator to produce a unified system context
- Writes Markdown + JSON artifacts to logs/context_snapshot_<ts>.(md|json)

Usage:
  python scripts/context_snapshot.py --days 30 --no-tests --coverage-file coverage.xml
"""
from __future__ import annotations

import argparse, json, os
from datetime import datetime, UTC
from pathlib import Path
import asyncio


def utc_ts() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")


async def main_async(args) -> int:
    # Lazy import to avoid heavy deps at import time
    from src.analysis.context_aggregator import ContextAggregator

    outdir = Path("logs"); outdir.mkdir(parents=True, exist_ok=True)
    ts = utc_ts()
    md_path = outdir / f"context_snapshot_{ts}.md"
    json_path = outdir / f"context_snapshot_{ts}.json"

    # Optional DB store: integrate later if available
    db_store = None
    agg = ContextAggregator(repo_path=args.repo_path, coverage_file=args.coverage_file, db_store=db_store)

    test_pass_rate = 1.0
    if args.run_tests:
        # Try fast test run via pytest -q; non-fatal on failure
        try:
            import subprocess
            p = subprocess.run(["pytest", "-q"], cwd=args.repo_path, capture_output=True, text=True, timeout=600)
            out = p.stdout
            # Parse simple summary
            import re
            m = re.search(r"(\d+) passed.*?(\d+) failed.*? in ", out)
            if m:
                passed, failed = int(m.group(1)), int(m.group(2))
                total = max(1, passed + failed)
                test_pass_rate = passed / total
        except Exception:
            pass

    ctx = await agg.aggregate(analysis_days=args.days, test_pass_rate=test_pass_rate)

    # Write artifacts
    md_path.write_text(ctx.summary + "\n", encoding="utf-8")

    payload = {
        "timestamp": ctx.timestamp,
        "health": {
            "score": ctx.health_score.overall_score,
            "grade": ctx.health_score.grade,
            "factors": [
                {
                    "name": f.name,
                    "score": f.score,
                    "weight": f.weight,
                    "status": f.status,
                    "details": f.details,
                }
                for f in ctx.health_score.factors
            ],
            "top_opportunities": [
                {
                    "priority": o.priority,
                    "category": o.category,
                    "description": o.description,
                    "impact": o.impact,
                    "effort": o.effort,
                    "estimated_score_gain": o.estimated_score_gain,
                }
                for o in ctx.health_score.top_opportunities
            ],
        },
        "git": None if ctx.git_analysis is None else {
            "total_commits": ctx.git_analysis.total_commits,
            "high_churn_files": [
                {
                    "file_path": f.file_path,
                    "commit_count": f.commit_count,
                    "line_changes": f.line_changes,
                    "last_modified": f.last_modified,
                } for f in ctx.git_analysis.high_churn_files
            ],
        },
        "coverage": None if ctx.coverage_analysis is None else {
            "overall": ctx.coverage_analysis.overall_coverage,
            "low_coverage_modules": [
                {
                    "path": m.module_path,
                    "line_coverage": m.line_coverage,
                    "uncovered": m.uncovered_lines[:20],
                } for m in ctx.coverage_analysis.low_coverage_modules[:20]
            ],
        },
        "metrics": None if ctx.metrics_analysis is None else {
            "degrading": [
                {
                    "metric": t.metric_name,
                    "change_percent": t.change_percent,
                    "severity": t.severity,
                } for t in ctx.metrics_analysis.degrading_metrics
            ],
            "improving": [
                {
                    "metric": t.metric_name,
                    "change_percent": t.change_percent,
                } for t in ctx.metrics_analysis.improving_metrics
            ],
            "anomalies": [
                {
                    "metric": a.metric_name,
                    "timestamp": a.timestamp,
                    "severity": a.severity,
                } for a in ctx.metrics_analysis.anomalies
            ],
        },
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Wrote context snapshot:\n- {md_path}\n- {json_path}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-path", default=".")
    ap.add_argument("--coverage-file", default="coverage.xml")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--run-tests", dest="run_tests", action="store_true")
    ap.add_argument("--no-tests", dest="run_tests", action="store_false")
    ap.set_defaults(run_tests=False)
    args = ap.parse_args(argv)

    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())

