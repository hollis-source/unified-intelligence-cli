#!/usr/bin/env python3
"""
Routing A/B Evaluator: Baseline vs RAG routing accuracy.

- Metric: domain classification accuracy = 1 if routing_decisions.task_domain
  equals expected template domain inferred from the template path/tags
- Test: two-proportion z-test (two-sided) with normal approximation

Usage:
  python scripts/ab_routing_eval.py --domains frontend research backend --per-domain 1 --provider qwen3

This runs for each template (small N) in both conditions:
  A) Baseline: without --enable-rag
  B) RAG: with --enable-rag
and queries SurrealDB routing_decisions by task_description to obtain the router's domain.
"""

import argparse
import asyncio
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Ensure src on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.build_rag_patterns import TaskTemplate
from src.adapters.rag.surrealdb_store import SurrealDBStore


def phi(z: float) -> float:
    """Standard normal CDF via erf."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2)))


def two_proportion_z_test(success_a: int, n_a: int, success_b: int, n_b: int) -> Dict[str, float]:
    p_a = success_a / n_a if n_a else 0.0
    p_b = success_b / n_b if n_b else 0.0
    p_pool = (success_a + success_b) / (n_a + n_b) if (n_a + n_b) else 0.0
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b)) if n_a and n_b else float("inf")
    z = 0.0 if se == 0 or math.isinf(se) else (p_b - p_a) / se
    p_two_sided = 2 * (1 - phi(abs(z)))
    return {"p_a": p_a, "p_b": p_b, "z": z, "p_value": p_two_sided}


def normal_ci(p: float, n: int, z: float = 1.96) -> List[float]:
    if n <= 0:
        return [0.0, 1.0]
    se = math.sqrt(p * (1 - p) / n)
    lo = max(0.0, p - z * se)
    hi = min(1.0, p + z * se)
    return [lo, hi]


def wilson_ci(success: int, n: int, z: float = 1.96) -> List[float]:
    if n <= 0:
        return [0.0, 1.0]
    phat = success / n
    denom = 1 + z*z/n
    center = (phat + (z*z)/(2*n)) / denom
    half = (z * math.sqrt((phat*(1-phat)/n) + (z*z)/(4*n*n))) / denom
    lo = max(0.0, center - half)
    hi = min(1.0, center + half)
    return [lo, hi]


async def fetch_last_routing_domain(db: SurrealDBStore, task_description: str) -> str:
    # Query latest routing_decision by description match
    q = (
        "SELECT id, task_description, task_domain FROM routing_decisions "
        "WHERE string::contains(task_description, $needle) ORDER BY id DESC LIMIT 1;"
    )
    res = await db.query(q, {"needle": task_description[:100]})  # simple contains
    rows: List[Dict[str, Any]] = []
    if isinstance(res, list):
        if res and isinstance(res[0], dict) and "task_description" in res[0]:
            rows = res
        elif res and hasattr(res[0], 'get') and res[0].get("result"):
            rows = res[0]["result"]
    if rows:
        return rows[0].get("task_domain") or ""
    return ""


def run_once(prompt: str, provider: str, rag: bool) -> (int, float):
    cmd = [
        sys.executable, "-m", "src.main",
        "--task", prompt,
        "--provider", provider,
        "--agents", "scaled",
        "--routing", "team",
        "--verbose",
    ]
    if rag:
        cmd.append("--enable-rag")
    t0 = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    elapsed = time.monotonic() - t0
    return proc.returncode, elapsed


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains", nargs="+", default=["frontend", "research", "backend"])
    ap.add_argument("--per-domain", type=int, default=1)
    ap.add_argument("--provider", type=str, default="qwen3")
    args = ap.parse_args()

    tasks_dir = Path("tasks")
    templates: List[TaskTemplate] = []
    for d in args.domains:
        for p in sorted((tasks_dir / d).glob("*.yaml"))[: args.per_domain]:
            # Load YAML directly
            import yaml
            with p.open("r", encoding="utf-8") as f:
                y = yaml.safe_load(f)
            templates.append(TaskTemplate(p, y))

    if not templates:
        print("No templates found for given domains.")
        return

    db = SurrealDBStore("ws://localhost:8000", "atado", "rag")

    baseline_hits = 0
    rag_hits = 0
    baseline_lat_total = 0.0
    rag_lat_total = 0.0
    baseline_n = 0
    rag_n = 0
    baseline_lats: List[float] = []
    rag_lats: List[float] = []

    for t in templates:
        prompt = t.prompt.strip()
        expected = t.domain
        # Baseline
        rc, lat = run_once(prompt, args.provider, rag=False)
        if rc == 0:
            pred = await fetch_last_routing_domain(db, prompt)
            baseline_hits += int(pred == expected)
            baseline_lat_total += lat
            baseline_lats.append(lat)
            baseline_n += 1
        # RAG
        rc, lat = run_once(prompt, args.provider, rag=True)
        if rc == 0:
            pred = await fetch_last_routing_domain(db, prompt)
            rag_hits += int(pred == expected)
            rag_lat_total += lat
            rag_lats.append(lat)
            rag_n += 1

    # Use actual counts per condition
    stats = two_proportion_z_test(baseline_hits, baseline_n, rag_hits, rag_n)

    # Confidence intervals
    p_a_ci = normal_ci(stats["p_a"], baseline_n)
    p_b_ci = normal_ci(stats["p_b"], rag_n)
    p_a_wilson = wilson_ci(baseline_hits, baseline_n)
    p_b_wilson = wilson_ci(rag_hits, rag_n)

    diff = stats["p_b"] - stats["p_a"]
    se_diff = math.sqrt((stats["p_a"] * (1 - stats["p_a"]) / max(1, baseline_n)) + (stats["p_b"] * (1 - stats["p_b"]) / max(1, rag_n)))
    diff_ci = [diff - 1.96 * se_diff, diff + 1.96 * se_diff] if not math.isinf(se_diff) else [float("nan"), float("nan")]
    # Newcombe (1998) Method 10 using Wilson intervals per group
    la, ua = p_a_wilson
    lb, ub = p_b_wilson
    diff_ci_wilson_newcombe = [lb - ua, ub - la]

    baseline_avg_latency = (baseline_lat_total / baseline_n) if baseline_n else 0.0
    rag_avg_latency = (rag_lat_total / rag_n) if rag_n else 0.0

    def pctile(xs: List[float], p: float) -> float:
        if not xs:
            return 0.0
        ys = sorted(xs)
        idx = min(len(ys) - 1, max(0, int(round(p * (len(ys) - 1)))))
        return ys[idx]

    baseline_p50 = pctile(baseline_lats, 0.5)
    baseline_p95 = pctile(baseline_lats, 0.95)
    rag_p50 = pctile(rag_lats, 0.5)
    rag_p95 = pctile(rag_lats, 0.95)

    # Simple shared-bin histogram over combined range (10 bins)
    def make_hist(xs_a: List[float], xs_b: List[float], bins: int = 10):
        xs = list(xs_a) + list(xs_b)
        if not xs:
            return {"bins": [], "counts": []}, {"bins": [], "counts": []}
        lo, hi = min(xs), max(xs)
        if hi == lo:
            edges = [lo, hi]
        else:
            step = (hi - lo) / bins
            edges = [lo + i * step for i in range(bins + 1)]
        def counts(data):
            cs = [0] * (len(edges) - 1)
            for v in data:
                if v <= edges[0]:
                    cs[0] += 1
                elif v >= edges[-1]:
                    cs[-1] += 1
                else:
                    # find bin
                    idx = int((v - edges[0]) / (edges[-1] - edges[0]) * (len(edges) - 1))
                    idx = min(max(0, idx), len(cs) - 1)
                    cs[idx] += 1
            return cs
        return (
            {"bins": edges, "counts": counts(xs_a)},
            {"bins": edges, "counts": counts(xs_b)}
        )

    base_hist, rag_hist = make_hist(baseline_lats, rag_lats)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    logs_dir = Path("logs"); logs_dir.mkdir(parents=True, exist_ok=True)
    out_json = logs_dir / f"ab_eval_{ts}.json"
    out_csv = logs_dir / f"ab_eval_{ts}.csv"
    out_diff_csv = logs_dir / f"ab_eval_diff_{ts}.csv"

    report = {
        "domains": args.domains,
        "per_domain": args.per_domain,
        "n_baseline": baseline_n,
        "n_rag": rag_n,
        "baseline_hits": baseline_hits,
        "rag_hits": rag_hits,
        "p_a": stats["p_a"],
        "p_b": stats["p_b"],
        "p_a_ci95": p_a_ci,
        "p_b_ci95": p_b_ci,
        "p_a_ci95_wilson": p_a_wilson,
        "p_b_ci95_wilson": p_b_wilson,
        "diff_p_b_minus_p_a": diff,
        "diff_ci95": diff_ci,
        "diff_ci95_wilson_newcombe": diff_ci_wilson_newcombe,
        "z": stats["z"],
        "p_value": stats["p_value"],
        "baseline_avg_latency_s": round(baseline_avg_latency, 3),
        "baseline_p50_s": round(baseline_p50, 3),
        "baseline_p95_s": round(baseline_p95, 3),
        "rag_avg_latency_s": round(rag_avg_latency, 3),
        "rag_p50_s": round(rag_p50, 3),
        "rag_p95_s": round(rag_p95, 3),
        "baseline_latency_hist": base_hist,
        "rag_latency_hist": rag_hist,
        "baseline_cost_proxy": round(baseline_avg_latency, 3),
        "rag_cost_proxy": round(rag_avg_latency, 3),
        "saved_report_json": str(out_json),
        "saved_report_csv": str(out_csv),
        "saved_report_diff_csv": str(out_diff_csv),
        "timestamp_utc": ts,
    }

    with out_json.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Save compact CSV with per-condition aggregates and a diff row (Newcombe CI)
    import csv
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "condition","n","hits","p",
            "ci95_lo_norm","ci95_hi_norm",
            "ci95_lo_wilson","ci95_hi_wilson",
            "avg_s","p50_s","p95_s",
            "diff_ci95_lo_norm","diff_ci95_hi_norm",
            "diff_ci95_lo_wilson_newcombe","diff_ci95_hi_wilson_newcombe"
        ])
        # baseline row
        w.writerow([
            "baseline", baseline_n, baseline_hits, round(report["p_a"], 6),
            round(p_a_ci[0], 6), round(p_a_ci[1], 6),
            round(p_a_wilson[0], 6), round(p_a_wilson[1], 6),
            round(baseline_avg_latency,3), round(baseline_p50,3), round(baseline_p95,3),
            "","","",""
        ])
        # rag row
        w.writerow([
            "rag", rag_n, rag_hits, round(report["p_b"], 6),
            round(p_b_ci[0], 6), round(p_b_ci[1], 6),
            round(p_b_wilson[0], 6), round(p_b_wilson[1], 6),
            round(rag_avg_latency,3), round(rag_p50,3), round(rag_p95,3),
            "","","",""
        ])
        # diff row (no latencies)
        w.writerow([
            "diff", "", "", round(diff, 6),
            round(diff_ci[0], 6), round(diff_ci[1], 6),
            "","",
            "","","",
            round(diff_ci[0], 6), round(diff_ci[1], 6),
            round(diff_ci_wilson_newcombe[0], 6), round(diff_ci_wilson_newcombe[1], 6)
        ])

    # Save separate diff CSV for dashboards
    with out_diff_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["n_baseline","n_rag","baseline_hits","rag_hits","p_a","p_b","diff",
                    "diff_ci95_lo_norm","diff_ci95_hi_norm",
                    "diff_ci95_lo_wilson_newcombe","diff_ci95_hi_wilson_newcombe"])
        w.writerow([
            baseline_n, rag_n, baseline_hits, rag_hits,
            round(report["p_a"], 6), round(report["p_b"], 6), round(diff, 6),
            round(diff_ci[0], 6), round(diff_ci[1], 6),
            round(diff_ci_wilson_newcombe[0], 6), round(diff_ci_wilson_newcombe[1], 6)
        ])

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

