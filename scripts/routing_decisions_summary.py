#!/usr/bin/env python3
"""
Summarize recent routing decisions from SurrealDB.

Outputs Markdown and JSON with counts and success rates grouped by RAG usage.
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


def render_markdown(groups: Dict[str, Dict[str, Any]], limit: int) -> str:
    lines = [
        "# Routing Decisions Summary",
        f"Limit: last {limit} decisions",
        "",
        "| Group | Count | Success | Success Rate |",
        "|-------|-------|---------|--------------|",
    ]
    for k, v in groups.items():
        lines.append(f"| {k} | {v['count']} | {v['success']} | {v['success_rate']:.2%} |")
    return "\n".join(lines)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--db-url", type=str, default="ws://localhost:8000")
    ap.add_argument("--ns", type=str, default="atado")
    ap.add_argument("--db", type=str, default="rag")
    args = ap.parse_args()

    db = SurrealDBStore(args.db_url, args.ns, args.db)
    rows = await fetch_recent(db, args.limit)
    groups = group_by_rag(rows)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    logs = Path("logs"); logs.mkdir(parents=True, exist_ok=True)
    md_path = logs / f"routing_summary_{ts}.md"
    json_path = logs / f"routing_summary_{ts}.json"

    md = render_markdown(groups, args.limit)
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(json.dumps({"limit": args.limit, "groups": groups}, indent=2), encoding="utf-8")

    print(md)
    print(f"\nSaved: {md_path} and {json_path}")


if __name__ == "__main__":
    asyncio.run(main())

