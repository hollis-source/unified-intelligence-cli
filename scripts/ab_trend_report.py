#!/usr/bin/env python3
"""
A/B Artifact Trend Report

Scans logs/ab_eval_*.json and aggregates key metrics over time.
Outputs Markdown and JSON under logs/.

Usage:
  PYTHONPATH=. python scripts/ab_trend_report.py [--pattern logs/ab_eval_*.json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from datetime import datetime
from typing import List, Dict, Any

DEFAULT_PATTERN = "logs/ab_eval_*.json"


def load_reports(pattern: str) -> List[Dict[str, Any]]:
    paths = sorted(glob.glob(pattern))
    reports: List[Dict[str, Any]] = []
    for p in paths:
        try:
            with open(p, "r") as f:
                data = json.load(f)
            data["_path"] = p
            reports.append(data)
        except Exception:
            continue
    return reports


def to_ts(path: str) -> str:
    # Extract timestamp from filename if present, else use mtime
    base = os.path.basename(path)
    # ab_eval_2025-10-19T06-01-03Z.json -> 2025-10-19T06:01:03Z
    try:
        stamp = base.split("ab_eval_")[1].split(".")[0]
        stamp = stamp.replace("-", ":", 2)  # first two '-' to ':' in time
        return stamp
    except Exception:
        return datetime.utcfromtimestamp(os.path.getmtime(path)).isoformat() + "Z"


def summarize(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = []
    for r in reports:
        rows.append({
            "ts": to_ts(r.get("_path", "")),
            "p_baseline": r.get("p_baseline"),
            "p_rag": r.get("p_rag"),
            "diff": r.get("diff_p_rag_minus_baseline"),
            "baseline_p95": r.get("baseline_p95_latency_s"),
            "rag_p95": r.get("rag_p95_latency_s"),
            "overall_agreement": (r.get("classifier_agreement") or {}).get("overall_rate"),
        })
    return {"rows": rows}


def write_outputs(summary: Dict[str, Any]) -> str:
    os.makedirs("logs", exist_ok=True)
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    md_path = f"logs/ab_trends_{ts}.md"
    json_path = f"logs/ab_trends_{ts}.json"

    # Markdown table (compact)
    lines = [
        "# A/B Trend Report",
        "",
        "| ts | p_baseline | p_rag | diff | baseline_p95_s | rag_p95_s | clf_agree |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary.get("rows", []):
        lines.append(
            f"| {row.get('ts','')} | {row.get('p_baseline')} | {row.get('p_rag')} | {row.get('diff')} | {row.get('baseline_p95')} | {row.get('rag_p95')} | {row.get('overall_agreement')} |"
        )

    with open(md_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)

    return md_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pattern", default=DEFAULT_PATTERN)
    args = ap.parse_args()

    reports = load_reports(args.pattern)
    if not reports:
        print("No reports found; nothing to summarize.")
        return 0
    summary = summarize(reports)
    out = write_outputs(summary)
    print(f"Wrote trend report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

