#!/usr/bin/env python3
"""
Auto Promotion Proposal (Guarded)

Reads latest A/B results and (optionally) DB-derived weights to generate a
promotion proposal artifact. Enforces guardrails:
- p_value < 0.05
- diff (rag - baseline) CI upper bound > 0
- per-domain weekly N >= 20 (if present in JSON fields)
- change cap: max +-10% per weight per rollout

Outputs:
- logs/promotion_proposal_<ts>.md
- logs/promotion_proposal_<ts>.json

NOTE: This script does not apply changes; it only proposes. Human/CI gate required.
"""
from __future__ import annotations

import asyncio
import glob
import json
import os
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, Dict, Optional



def _write_audit_log(payload: Dict[str, Any]) -> None:
    """Best-effort audit log: try SurrealDB; fallback to logs/audit_log.jsonl"""
    actor = os.getenv("GITHUB_ACTOR") or os.getenv("CI_ACTOR") or "ci"
    try:
        from src.adapters.llm.rag_config import RAGConfig  # type: ignore
        from src.adapters.rag.surrealdb_store import SurrealDBStore  # type: ignore
        cfg = RAGConfig()
        store = SurrealDBStore(
            url=os.getenv("SURREALDB_URL", cfg.db_url),
            namespace=cfg.db_namespace,
            database=cfg.db_database,
            user=cfg.db_user,
            password=cfg.db_password,
        )
        import asyncio
        async def _go():
            await store.store_audit_log(
                action=payload.get("action", "promotion_proposal"),
                actor=actor,
                reason=payload.get("reason"),
                before=payload.get("before"),
                after=payload.get("after"),
                metadata=payload.get("metadata"),
            )
        asyncio.run(_go())
        return
    except Exception:
        pass
    # Fallback file log
    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/audit_log.jsonl", "a") as f:
            rec = dict(payload)
            rec["ts"] = datetime.now(UTC).isoformat().replace('+00:00', 'Z')
            rec["actor"] = actor
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass


@dataclass
class Proposal:
    eligible: bool
    reason: str
    suggested_weights: Dict[str, float]


def _latest_ab_json() -> Optional[str]:
    paths = sorted(glob.glob("logs/ab_eval_*.json"))
    return paths[-1] if paths else None


def _load_candidate_weights() -> Dict[str, float]:
    """Try to compute or retrieve candidate weights via WeightOptimizer. Optional."""
    try:
        from src.adapters.llm.rag_config import RAGConfig  # type: ignore
        from src.adapters.rag.surrealdb_store import SurrealDBStore  # type: ignore
        from src.routing.weight_optimizer import WeightOptimizer  # type: ignore
        cfg = RAGConfig()
        store = SurrealDBStore(
            url=os.getenv("SURREALDB_URL", cfg.db_url),
            namespace=cfg.db_namespace,
            database=cfg.db_database,
            user=cfg.db_user,
            password=cfg.db_password,
        )
        weights = asyncio.run(WeightOptimizer(store, min_samples=10).optimize_domain_weights())
        return weights or {}
    except Exception:
        return {}


def _cap_changes(weights: Dict[str, float], cap: float = 0.10) -> Dict[str, float]:
    """Clamp multipliers within 1±cap."""
    out = {}
    for k, v in (weights or {}).items():
        out[k] = max(1 - cap, min(1 + cap, float(v)))
    return out


def build_proposal() -> Proposal:
    p = _latest_ab_json()
    if not p:
        return Proposal(False, "No A/B artifact found", {})
    data = json.load(open(p))
    pval = float(data.get("p_value", 1.0))
    ci = data.get("diff_ci95_wilson_newcombe") or data.get("diff_ci95") or [None, None]
    # Guardrails
    if pval >= 0.05:
        return Proposal(False, f"p_value not significant: {pval:.3f}", {})
    try:
        upper = float(ci[1]) if ci and ci[1] is not None else None
    except Exception:
        upper = None
    if upper is None or upper <= 0:
        return Proposal(False, f"Diff CI upper bound not > 0: {ci}", {})
    # Optional: per-domain N guard if present
    per_dom = int(data.get("per_domain", 0))
    if per_dom and per_dom < 20:
        return Proposal(False, f"per_domain too small: {per_dom} < 20", {})

    candidate = _load_candidate_weights()
    capped = _cap_changes(candidate, cap=0.10)
    return Proposal(True, "Eligible for promotion", capped)


def main() -> int:
    os.makedirs("logs", exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    md = f"logs/promotion_proposal_{ts}.md"
    js = f"logs/promotion_proposal_{ts}.json"
    prop = build_proposal()
    lines = [
        "# Promotion Proposal",
        f"eligible={prop.eligible}",
        f"reason={prop.reason}",
    ]
    if prop.suggested_weights:
        lines.append("\n## Suggested weights (capped ±10%)")
        for k, v in sorted(prop.suggested_weights.items()):
            lines.append(f"- {k}: {v:.3f}")
    open(md, "w").write("\n".join(lines) + "\n")
    payload = {
        "action": "promotion_proposal",
        "reason": prop.reason,
        "after": {"suggested_weights": prop.suggested_weights},
        "metadata": {"artifact_md": md, "artifact_json": js, "eligible": prop.eligible},
    }
    json.dump({
        "eligible": prop.eligible,
        "reason": prop.reason,
        "suggested_weights": prop.suggested_weights,
    }, open(js, "w"), indent=2)
    # Audit entry
    _write_audit_log(payload)
    print(f"Wrote promotion proposal: {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

