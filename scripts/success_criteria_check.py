#!/usr/bin/env python3
"""
Success Criteria Validation Checker

Evaluates Option 1 success criteria using available artifacts/logs and optionally SurrealDB.
Outputs a Markdown and JSON status report under logs/.

Criteria:
1) ≥50 patterns stored across all domains
2) RAG accuracy > 70% vs baseline
3) A/B p-value < 0.05 (statistical significance)
4) Weight optimization reduces errors by 20%+
5) Drift detection identifies pattern changes

Notes:
- Where data is insufficient, marks status = "unknown" with a reason
- Uses latest ab_eval_*.json for accuracy & p-value
- Tries DB-backed counts from execution_log; falls back to logs/pattern_collection_results.json
- Estimates before/after error reduction via execution_log first-half vs second-half windows
- Optionally inspects advanced_metrics_*.json for drift signals
"""
from __future__ import annotations

import asyncio
import glob
import json
import os
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, Dict, Optional, List, Tuple


@dataclass
class CriteriaStatus:
    status: str  # met, not_met, unknown
    details: str


def latest(path_glob: str) -> Optional[str]:
    paths = sorted(glob.glob(path_glob))
    return paths[-1] if paths else None


def check_ab_eval() -> Dict[str, Any]:
    path = latest("logs/ab_eval_*.json")
    if not path:
        return {"available": False}
    data = json.load(open(path))
    # Provide robust keys: support aliases
    p_baseline = data.get("p_rag" if "p_baseline" not in data else "p_baseline")
    p_rag = data.get("p_b" if "p_rag" not in data else "p_rag")
    p_value = data.get("p_value")
    return {
        "available": True,
        "path": path,
        "p_baseline": p_baseline,
        "p_rag": p_rag,
        "p_value": p_value,
    }


def check_advanced_metrics() -> Dict[str, Any]:
    path = latest("logs/advanced_metrics_*.json")
    if not path:
        return {"available": False}
    data = json.load(open(path))
    drift = data.get("drift") or {}
    return {"available": True, "path": path, "drift": drift}


# -------------------------
# Optional DB-backed helpers
# -------------------------

def _try_db_imports():
    try:
        from src.adapters.llm.rag_config import RAGConfig  # type: ignore
        from src.adapters.rag.surrealdb_store import SurrealDBStore  # type: ignore
        return RAGConfig, SurrealDBStore
    except Exception:
        return None, None


async def _db_count_patterns() -> Optional[int]:
    RAGConfig, SurrealDBStore = _try_db_imports()
    if not RAGConfig or not SurrealDBStore:
        return None
    cfg = RAGConfig()
    store = SurrealDBStore(
        url=os.getenv("SURREALDB_URL", cfg.db_url),
        namespace=cfg.db_namespace,
        database=cfg.db_database,
        user=cfg.db_user,
        password=cfg.db_password,
    )
    try:
        res = await store.query("SELECT count() AS c FROM execution_log;")
        # Handle SurrealDB result shapes
        if res and isinstance(res, list):
            if isinstance(res[0], dict) and "c" in res[0]:
                return int(res[0].get("c", 0))
            if hasattr(res[0], "get") and res[0].get("result"):
                arr = res[0]["result"]
                if arr:
                    return int(arr[0].get("c", 0))
    except Exception:
        pass
    return None


def _split_windows(bools: List[bool]) -> Tuple[List[bool], List[bool]]:
    if not bools:
        return [], []
    mid = max(1, len(bools) // 2)
    return bools[:mid], bools[mid:]


async def _db_exec_error_reduction(min_per_window: int = 30) -> Optional[Dict[str, float]]:
    """Compute relative error reduction from first half to second half of execution_log."""
    RAGConfig, SurrealDBStore = _try_db_imports()
    if not RAGConfig or not SurrealDBStore:
        return None
    cfg = RAGConfig()
    store = SurrealDBStore(
        url=os.getenv("SURREALDB_URL", cfg.db_url),
        namespace=cfg.db_namespace,
        database=cfg.db_database,
        user=cfg.db_user,
        password=cfg.db_password,
    )
    try:
        res = await store.query("SELECT success FROM execution_log LIMIT 1000;")
        rows: List[Dict[str, Any]] = []
        if res and isinstance(res, list):
            if isinstance(res[0], dict) and "success" in res[0]:
                rows = res
            elif hasattr(res[0], 'get') and res[0].get("result"):
                rows = res[0]["result"]
        successes = [bool(r.get("success")) for r in rows if r.get("success") is not None]
        first, second = _split_windows(successes)
        if len(first) < min_per_window or len(second) < min_per_window:
            return None
        def err(arr: List[bool]) -> float:
            if not arr:
                return 0.0
            s = sum(1 for x in arr if x)
            p = s / len(arr)
            return 1.0 - p
        e1, e2 = err(first), err(second)
        if e1 <= 0.0:
            return None
        rel = (e1 - e2) / e1
        return {"error_before": e1, "error_after": e2, "relative_reduction": rel, "n_first": len(first), "n_second": len(second)}
    except Exception:
        return None


def check_patterns_count() -> CriteriaStatus:
    # Prefer DB-backed count
    try:
        count = asyncio.run(_db_count_patterns())
    except Exception:
        count = None
    if isinstance(count, int):
        return CriteriaStatus("met" if count >= 50 else "not_met", f"execution_log count={count}")

    # Fallback to log file
    paths = glob.glob("logs/pattern_collection_results.json")
    if paths:
        try:
            rows = json.load(open(paths[0]))
            count = len(rows)
            if count >= 50:
                return CriteriaStatus("met", f"Found {count} pattern entries in pattern_collection_results.json")
            else:
                return CriteriaStatus("not_met", f"Found {count} pattern entries (<50) in pattern_collection_results.json")
        except Exception as e:
            return CriteriaStatus("unknown", f"Failed to parse pattern_collection_results.json: {e}")
    return CriteriaStatus("unknown", "No pattern count source available (DB not available)")


def criteria_report() -> Dict[str, Any]:
    ab = check_ab_eval()
    adv = check_advanced_metrics()

    # 1) Pattern count
    c1 = check_patterns_count()

    # 2) RAG accuracy > 70%
    if ab.get("available") and ab.get("p_rag") is not None:
        try:
            rag_acc = float(ab["p_rag"])  # proportion 0..1
            c2 = CriteriaStatus("met" if rag_acc > 0.70 else "not_met", f"RAG accuracy={rag_acc:.2f}")
        except Exception as e:
            c2 = CriteriaStatus("unknown", f"Could not parse p_rag: {e}")
    else:
        c2 = CriteriaStatus("unknown", "A/B JSON not available or missing p_rag")

    # 3) p-value < 0.05
    if ab.get("available") and ab.get("p_value") is not None:
        try:
            pv = float(ab["p_value"])
            c3 = CriteriaStatus("met" if pv < 0.05 else "not_met", f"p_value={pv:.3f}")
        except Exception as e:
            c3 = CriteriaStatus("unknown", f"Could not parse p_value: {e}")
    else:
        c3 = CriteriaStatus("unknown", "A/B JSON not available or missing p_value")

    # 4) Weight optimization reduces errors by 20%+
    # Estimate from execution_log windows if DB available and sufficient sample size
    try:
        wo = asyncio.run(_db_exec_error_reduction())
    except Exception:
        wo = None
    if wo and wo.get("relative_reduction") is not None:
        rr = float(wo["relative_reduction"])
        c4 = CriteriaStatus("met" if rr >= 0.20 else "not_met", f"relative_error_reduction={rr:.2f} (n1={wo['n_first']}, n2={wo['n_second']})")
    else:
        c4 = CriteriaStatus("unknown", "Insufficient execution_log data to estimate before/after error rates")

    # 5) Drift detection identifies changes
    if adv.get("available"):
        drift = adv.get("drift") or {}
        diffs = drift.get("diffs") or {}
        if any(abs(float(v or 0.0)) >= 0.1 for v in diffs.values()):
            c5 = CriteriaStatus("met", f"Detected drift signals: {diffs}")
        else:
            c5 = CriteriaStatus("unknown", "No significant drift signals detected (or insufficient data)")
    else:
        c5 = CriteriaStatus("unknown", "Advanced metrics not available")

    return {
        "criteria": {
            "patterns_50_plus": c1.__dict__,
            "rag_accuracy_gt_70": c2.__dict__,
            "p_value_lt_0_05": c3.__dict__,
            "weight_opt_minus_20pct_errors": c4.__dict__,
            "drift_detection_signals": c5.__dict__,
        },
        "sources": {
            "ab_eval_json": ab.get("path"),
            "advanced_metrics_json": adv.get("path"),
        },
    }


def write_outputs(report: Dict[str, Any]) -> str:
    os.makedirs("logs", exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    md = f"logs/success_criteria_{ts}.md"
    js = f"logs/success_criteria_{ts}.json"

    crit = report.get("criteria", {})
    lines = [
        "# Success Criteria Validation",
        "",
        "| Criterion | Status | Details |",
        "| --- | --- | --- |",
    ]
    for key, st in crit.items():
        lines.append(f"| {key} | {st.get('status','-')} | {st.get('details','')} |")

    with open(md, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(js, "w") as f:
        json.dump(report, f, indent=2)
    return md


def main() -> int:
    rep = criteria_report()
    out = write_outputs(rep)
    print(f"Wrote success criteria report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

