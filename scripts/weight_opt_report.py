#!/usr/bin/env python3
"""
Weight Optimization Before/After Report

Heuristically estimates error-rate reduction by comparing the first half vs second half
of execution_log entries. Outputs Markdown/JSON under logs/.

Notes:
- Purely heuristic unless a true "optimization timestamp" is provided later
- Requires DB access; degrades gracefully if DB or data not available
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional


@dataclass
class Summary:
    n_first: int
    n_second: int
    error_before: float
    error_after: float
    relative_reduction: float


def _try_db_imports():
    try:
        from src.adapters.llm.rag_config import RAGConfig  # type: ignore
        from src.adapters.rag.surrealdb_store import SurrealDBStore  # type: ignore
        return RAGConfig, SurrealDBStore
    except Exception:
        return None, None


async def _load_exec_successes(limit: int = 2000) -> List[bool]:
    RAGConfig, SurrealDBStore = _try_db_imports()
    if not RAGConfig or not SurrealDBStore:
        return []
    cfg = RAGConfig()
    store = SurrealDBStore(
        url=os.getenv("SURREALDB_URL", cfg.db_url),
        namespace=cfg.db_namespace,
        database=cfg.db_database,
        user=cfg.db_user,
        password=cfg.db_password,
    )
    try:
        res = await store.query("SELECT success FROM execution_log LIMIT $limit;", {"limit": limit})
        if res and isinstance(res, list):
            if isinstance(res[0], dict) and "success" in res[0]:
                rows = res
            elif hasattr(res[0], 'get') and res[0].get("result"):
                rows = res[0]["result"]
            else:
                rows = []
        else:
            rows = []
        return [bool(r.get("success")) for r in rows if r.get("success") is not None]
    except Exception:
        return []


def _split_windows(bools: List[bool]):
    if not bools:
        return [], []
    mid = max(1, len(bools) // 2)
    return bools[:mid], bools[mid:]


def summarize(success_flags: List[bool], min_per_window: int = 50) -> Optional[Summary]:
    first, second = _split_windows(success_flags)
    if len(first) < min_per_window or len(second) < min_per_window:
        return None
    def err(arr: List[bool]) -> float:
        if not arr:
            return 0.0
        s = sum(1 for x in arr if x)
        p = s / len(arr)
        return 1 - p
    e1, e2 = err(first), err(second)
    if e1 <= 0.0:
        return None
    rr = (e1 - e2) / e1
    return Summary(n_first=len(first), n_second=len(second), error_before=e1, error_after=e2, relative_reduction=rr)


def main() -> int:
    try:
        successes = asyncio.run(_load_exec_successes())
    except Exception:
        successes = []
    summ = summarize(successes)
    os.makedirs("logs", exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    md = f"logs/weight_opt_report_{ts}.md"
    js = f"logs/weight_opt_report_{ts}.json"
    if not summ:
        open(md, "w").write("# Weight Optimization Report\n\nInsufficient data to compute before/after error rates.\n")
        json.dump({"available": False}, open(js, "w"))
        print(f"Wrote weight optimization report: {md}")
        return 0
    lines = [
        "# Weight Optimization Report",
        f"n_first={summ.n_first}",
        f"n_second={summ.n_second}",
        f"error_before={summ.error_before:.3f}",
        f"error_after={summ.error_after:.3f}",
        f"relative_reduction={summ.relative_reduction:.3f}",
    ]
    open(md, "w").write("\n".join(lines)+"\n")
    json.dump({
        "available": True,
        "n_first": summ.n_first,
        "n_second": summ.n_second,
        "error_before": summ.error_before,
        "error_after": summ.error_after,
        "relative_reduction": summ.relative_reduction,
    }, open(js, "w"), indent=2)
    print(f"Wrote weight optimization report: {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

