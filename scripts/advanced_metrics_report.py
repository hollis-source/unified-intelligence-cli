#!/usr/bin/env python3
"""
Advanced RAG Metrics Report (Day 3-4)

Computes advanced RAG metrics from SurrealDB and writes Markdown+JSON
artifacts under logs/.

Metrics:
- Drift signals: per-domain routing accuracy change across two recent windows
- Agent performance snapshot: leaderboard by success_rate
- Feedback loop effectiveness: success/latency by agent_role and domain
- Cross-domain pattern transfer (heuristic): patterns' agent roles vs task domain

Notes:
- If DB is unavailable, script degrades gracefully and writes a minimal report.
- All computations are implemented via pure helpers to allow unit testing.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.adapters.llm.rag_config import RAGConfig
from src.adapters.rag.surrealdb_store import SurrealDBStore


@dataclass
class RoutingDecision:
    task_domain: str
    routing_strategy: str
    success: Optional[bool]
    metadata: Dict[str, Any]


@dataclass
class ExecLog:
    task_domain: str
    agent_role: str
    success: bool
    latency_seconds: float


def _role_to_domain_heuristic(role: str) -> Optional[str]:
    r = role.lower()
    mapping = [
        ("frontend", "frontend"),
        ("backend", "backend"),
        ("devops", "devops"),
        ("qa", "qa"), ("test", "qa"), ("testing", "qa"),
        ("research", "research"),
        ("arch", "architecture"), ("design", "architecture"),
        ("data", "data"),
    ]
    for needle, domain in mapping:
        if needle in r:
            return domain
    return None


def split_windows(items: List[Any]) -> Tuple[List[Any], List[Any]]:
    if not items:
        return [], []
    mid = max(1, len(items) // 2)
    return items[:mid], items[mid:]


def domain_accuracy(decisions: List[RoutingDecision]) -> Dict[str, float]:
    # Only count decisions with success != None
    by_domain: Dict[str, List[bool]] = {}
    for d in decisions:
        if d.success is None:
            continue
        key = (d.task_domain or "").strip().lower()
        by_domain.setdefault(key, []).append(bool(d.success))
    return {k: (sum(v) / len(v)) if v else 0.0 for k, v in by_domain.items()}


def drift_signals(decisions: List[RoutingDecision]) -> Dict[str, Any]:
    first, second = split_windows(decisions)
    acc1 = domain_accuracy(first)
    acc2 = domain_accuracy(second)
    domains = set(acc1) | set(acc2)
    diffs = {d: (acc2.get(d, 0.0) - acc1.get(d, 0.0)) for d in domains}
    return {"window_sizes": [len(first), len(second)], "acc_first": acc1, "acc_second": acc2, "diffs": diffs}


def performance_by_agent(execs: List[ExecLog]) -> Dict[str, Any]:
    from collections import defaultdict
    m = defaultdict(lambda: {"n": 0, "ok": 0, "latency_sum": 0.0})
    for e in execs:
        d = m[e.agent_role]
        d["n"] += 1
        d["ok"] += 1 if e.success else 0
        d["latency_sum"] += float(e.latency_seconds or 0.0)
    out = {}
    for role, d in m.items():
        n = max(1, d["n"])  # guard
        out[role] = {
            "n": d["n"],
            "success_rate": d["ok"] / n,
            "avg_latency_s": d["latency_sum"] / n,
        }
    return out


def performance_by_domain(execs: List[ExecLog]) -> Dict[str, Any]:
    from collections import defaultdict
    m = defaultdict(lambda: {"n": 0, "ok": 0, "latency_sum": 0.0})
    for e in execs:
        key = (e.task_domain or "").strip().lower()
        d = m[key]
        d["n"] += 1
        d["ok"] += 1 if e.success else 0
        d["latency_sum"] += float(e.latency_seconds or 0.0)
    out = {}
    for dom, d in m.items():
        n = max(1, d["n"])  # guard
        out[dom] = {
            "n": d["n"],
            "success_rate": d["ok"] / n,
            "avg_latency_s": d["latency_sum"] / n,
        }
    return out


def cross_domain_transfer(decisions: List[RoutingDecision]) -> Dict[str, Any]:
    # For rag_used decisions, compare top_patterns agent role inferred domain vs task_domain
    total = 0
    cross = 0
    examples: List[Dict[str, Any]] = []
    for d in decisions:
        meta = d.metadata or {}
        if not meta.get("rag_used"):
            continue
        task_dom = (d.task_domain or "").strip().lower()
        tops = meta.get("top_patterns") or []
        if not tops:
            continue
        total += 1
        # Heuristic: if any top agent role domain differs from task_dom → mark cross
        inferred = {_role_to_domain_heuristic((tp.get("agent") or "")) for tp in tops}
        inferred.discard(None)
        if inferred and (task_dom not in inferred):
            cross += 1
            if len(examples) < 5:
                examples.append({"task_domain": task_dom, "inferred": sorted(inferred), "top_patterns": tops})
    rate = (cross / total) if total else 0.0
    return {"sample": total, "cross_rate": rate, "examples": examples}


def summarize(decisions: List[RoutingDecision], execs: List[ExecLog], agent_perf_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "drift": drift_signals(decisions),
        "performance": {
            "by_agent": performance_by_agent(execs),
            "by_domain": performance_by_domain(execs),
            "agent_leaderboard": sorted(
                [
                    {
                        "agent_role": r.get("agent_role"),
                        "success_rate": r.get("success_rate"),
                        "avg_latency_ms": r.get("avg_latency_ms"),
                        "total_tasks": r.get("total_tasks"),
                    }
                    for r in agent_perf_rows
                ],
                key=lambda x: (x.get("success_rate") or 0), reverse=True,
            )[:10],
        },
        "cross_domain_transfer": cross_domain_transfer(decisions),
    }


def write_outputs(report: Dict[str, Any]) -> str:
    os.makedirs("logs", exist_ok=True)
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    md_path = f"logs/advanced_metrics_{ts}.md"
    json_path = f"logs/advanced_metrics_{ts}.json"

    drift = report.get("drift", {})
    perf = report.get("performance", {})
    xfer = report.get("cross_domain_transfer", {})

    def pct(x: Optional[float]) -> str:
        try:
            return f"{100.0*float(x):.1f}%"
        except Exception:
            return "-"

    lines = [
        "# Advanced RAG Metrics",
        "",
        "## Drift signals (domain accuracy)",
        f"Window sizes: {drift.get('window_sizes')}",
        "",
        "- First window accuracy: " + json.dumps(drift.get("acc_first", {})),
        "- Second window accuracy: " + json.dumps(drift.get("acc_second", {})),
        "- Diffs (second - first): " + json.dumps(drift.get("diffs", {})),
        "",
        "## Performance",
        "### By agent (top 5)",
        "| agent | n | success | avg_latency_s |",
        "| --- | --- | --- | --- |",
    ]
    for role, row in list(perf.get("by_agent", {}).items())[:5]:
        lines.append(f"| {role} | {row.get('n','-')} | {pct(row.get('success_rate'))} | {row.get('avg_latency_s', '-'):.2f} |")
    lines += [
        "",
        "### By domain (all)",
        "| domain | n | success | avg_latency_s |",
        "| --- | --- | --- | --- |",
    ]
    for dom, row in perf.get("by_domain", {}).items():
        lines.append(f"| {dom} | {row.get('n','-')} | {pct(row.get('success_rate'))} | {row.get('avg_latency_s', '-'):.2f} |")
    lines += [
        "",
        "### Agent leaderboard (agent_performance)",
        "| agent | success | avg_latency_ms | total_tasks |",
        "| --- | --- | --- | --- |",
    ]
    for r in perf.get("agent_leaderboard", [])[:10]:
        lines.append(f"| {r.get('agent_role','-')} | {pct(r.get('success_rate'))} | {r.get('avg_latency_ms','-')} | {r.get('total_tasks','-')} |")
    lines += [
        "",
        "## Cross-domain pattern transfer (heuristic)",
        f"Sample size: {xfer.get('sample', 0)}; Cross rate: {pct(xfer.get('cross_rate'))}",
        "Examples:",
        "",
        json.dumps(xfer.get("examples", []), indent=2),
        "",
    ]

    with open(md_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)

    return md_path


async def fetch_data(limit: int = 500) -> Tuple[List[RoutingDecision], List[ExecLog], List[Dict[str, Any]]]:
    # Initialize store from env or RAGConfig defaults
    cfg = RAGConfig()
    url = os.getenv("SURREALDB_URL", cfg.db_url)
    ns = cfg.db_namespace
    db = cfg.db_database
    user = cfg.db_user
    pwd = cfg.db_password

    store = SurrealDBStore(url=url, namespace=ns, database=db, user=user, password=pwd)

    # routing_decisions
    decisions_raw: List[Dict[str, Any]] = []
    try:
        rows = await store.get_recent_routing_decisions(limit=limit)
        decisions_raw = rows or []
    except Exception:
        decisions_raw = []

    # execution_log
    execs_raw: List[Dict[str, Any]] = []
    try:
        res = await store.query("SELECT task_domain, agent_role, success, latency_seconds FROM execution_log LIMIT $limit;", {"limit": limit})
        if res and isinstance(res, list):
            if isinstance(res[0], dict) and "task_domain" in res[0]:
                execs_raw = res
            elif hasattr(res[0], 'get') and res[0].get("result"):
                execs_raw = res[0]["result"]
    except Exception:
        execs_raw = []

    # agent_performance snapshot
    agent_perf_rows: List[Dict[str, Any]] = []
    try:
        agent_perf_rows = await store.get_top_performing_agents(limit=50)
    except Exception:
        agent_perf_rows = []

    # Convert
    decisions = [
        RoutingDecision(
            task_domain=(r.get("task_domain") or ""),
            routing_strategy=(r.get("routing_strategy") or ""),
            success=r.get("success"),
            metadata=(r.get("metadata") or {}),
        )
        for r in decisions_raw
    ]
    execs = [
        ExecLog(
            task_domain=(e.get("task_domain") or ""),
            agent_role=(e.get("agent_role") or ""),
            success=bool(e.get("success")),
            latency_seconds=float(e.get("latency_seconds") or 0.0),
        )
        for e in execs_raw
    ]

    return decisions, execs, agent_perf_rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=500)
    args = ap.parse_args()

    # Lazy import for asyncio to keep helper functions pure
    import asyncio
    try:
        decisions, execs, agent_perf = asyncio.get_event_loop().run_until_complete(fetch_data(limit=args.limit))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            decisions, execs, agent_perf = loop.run_until_complete(fetch_data(limit=args.limit))
        finally:
            loop.close()

    report = summarize(decisions, execs, agent_perf)
    out = write_outputs(report)
    print(f"Wrote advanced metrics report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

