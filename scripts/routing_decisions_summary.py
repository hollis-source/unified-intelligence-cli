#!/usr/bin/env python3
"""
Summarize recent routing decisions from SurrealDB.

Outputs Markdown and JSON with counts and success rates grouped by:
- RAG usage (rag_used=true/false)
- Routing strategy (baseline, rag, fallback)
- Normalized domain (test→testing, quality→qa)

Saves to logs/routing_summary_<timestamp>.{md,json}
"""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.rag.surrealdb_store import SurrealDBStore
from scripts.ab_routing_eval import normalize_domain


async def fetch_recent(db: SurrealDBStore, limit: int) -> List[Dict[str, Any]]:
    q = "SELECT * FROM routing_decisions ORDER BY id DESC LIMIT $limit;"
    res = await db.query(q, {"limit": limit})
    if isinstance(res, list):
        if res and isinstance(res[0], dict) and "task_id" in res[0]:
            return res
        if res and hasattr(res[0], 'get') and res[0].get("result"):
            return res[0]["result"]
    return []


def group_by_rag(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Group routing decisions by rag_used metadata field."""
    out: Dict[str, Dict[str, Any]] = {
        "rag_true": {"count": 0, "success": 0},
        "rag_false": {"count": 0, "success": 0},
        "unknown": {"count": 0, "success": 0},
    }
    for r in rows:
        md = r.get("metadata") or {}
        rag_used = md.get("rag_used")
        key = "unknown"
        if rag_used is True:
            key = "rag_true"
        elif rag_used is False:
            key = "rag_false"
        out[key]["count"] += 1
        if r.get("success") is True:
            out[key]["success"] += 1
    # compute rates
    for k, v in out.items():
        c = v["count"] or 1
        v["success_rate"] = v["success"] / c
    return out


def group_by_strategy(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Group routing decisions by routing_strategy metadata field."""
    strategies: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        md = r.get("metadata") or {}
        strategy = md.get("routing_strategy", "unknown")
        if strategy not in strategies:
            strategies[strategy] = {"count": 0, "success": 0}
        strategies[strategy]["count"] += 1
        if r.get("success") is True:
            strategies[strategy]["success"] += 1

    # compute rates
    for k, v in strategies.items():
        c = v["count"] or 1
        v["success_rate"] = v["success"] / c
    return strategies


def group_by_domain(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Group routing decisions by normalized task_domain."""
    domains: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        raw_domain = r.get("task_domain", "unknown")
        normalized = normalize_domain(raw_domain) or "unknown"

        if normalized not in domains:
            domains[normalized] = {"count": 0, "success": 0, "raw_domains": set()}

        domains[normalized]["count"] += 1
        domains[normalized]["raw_domains"].add(raw_domain)

        if r.get("success") is True:
            domains[normalized]["success"] += 1

    # compute rates and convert sets to lists
    for k, v in domains.items():
        c = v["count"] or 1
        v["success_rate"] = v["success"] / c
        v["raw_domains"] = sorted(list(v["raw_domains"]))

    return domains


def render_markdown(
    rag_groups: Dict[str, Dict[str, Any]],
    strategies: Dict[str, Dict[str, Any]],
    domains: Dict[str, Dict[str, Any]],
    limit: int
) -> str:
    """Render comprehensive markdown summary with all groupings."""
    lines = [
        "# Routing Decisions Summary",
        f"**Analyzed**: Last {limit} routing decisions",
        "",
        "## By RAG Usage",
        "",
        "| RAG Used | Count | Success | Success Rate |",
        "|----------|-------|---------|--------------|",
    ]
    for k, v in rag_groups.items():
        lines.append(f"| {k} | {v['count']} | {v['success']} | {v['success_rate']:.2%} |")

    lines.extend([
        "",
        "## By Routing Strategy",
        "",
        "| Strategy | Count | Success | Success Rate |",
        "|----------|-------|---------|--------------|",
    ])
    for k in sorted(strategies.keys()):
        v = strategies[k]
        lines.append(f"| {k} | {v['count']} | {v['success']} | {v['success_rate']:.2%} |")

    lines.extend([
        "",
        "## By Normalized Domain",
        "",
        "| Domain (Normalized) | Count | Success | Success Rate | Raw Domains |",
        "|---------------------|-------|---------|--------------|-------------|",
    ])
    for k in sorted(domains.keys(), key=lambda x: -domains[x]['count']):
        v = domains[k]
        raw = ", ".join(v['raw_domains']) if len(v['raw_domains']) > 1 else v['raw_domains'][0]
        lines.append(f"| {k} | {v['count']} | {v['success']} | {v['success_rate']:.2%} | {raw} |")

    return "\n".join(lines)


async def main():
    ap = argparse.ArgumentParser(
        description="Summarize routing decisions by RAG usage, strategy, and normalized domain"
    )
    ap.add_argument("--limit", type=int, default=100, help="Number of recent decisions to analyze")
    ap.add_argument("--db-url", type=str, default="ws://localhost:8000", help="SurrealDB WebSocket URL")
    ap.add_argument("--ns", type=str, default="atado", help="SurrealDB namespace")
    ap.add_argument("--db", type=str, default="rag", help="SurrealDB database")
    args = ap.parse_args()

    db = SurrealDBStore(args.db_url, args.ns, args.db)
    await db.connect()

    rows = await fetch_recent(db, args.limit)

    # Generate all groupings
    rag_groups = group_by_rag(rows)
    strategies = group_by_strategy(rows)
    domains = group_by_domain(rows)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    logs = Path("logs"); logs.mkdir(parents=True, exist_ok=True)
    md_path = logs / f"routing_summary_{ts}.md"
    json_path = logs / f"routing_summary_{ts}.json"

    # Render and save markdown
    md = render_markdown(rag_groups, strategies, domains, args.limit)
    md_path.write_text(md, encoding="utf-8")

    # Save comprehensive JSON
    report = {
        "timestamp": ts,
        "limit": args.limit,
        "total_decisions": len(rows),
        "by_rag_usage": rag_groups,
        "by_strategy": strategies,
        "by_domain": domains,
    }
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(md)
    print(f"\nSaved: {md_path} and {json_path}")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())

