#!/usr/bin/env python3
"""
Weights CLI: list audit entries, show/apply proposals, rollback by audit id.

Examples:
  python scripts/weights_cli.py list-audit --limit 10
  python scripts/weights_cli.py show-proposal --latest
  python scripts/weights_cli.py apply-proposal --latest
  python scripts/weights_cli.py rollback --from-audit <audit-id>

Notes:
- Applies domain multipliers to routing_weight entries per domain
- Records audit entries for apply/rollback; falls back to logs/audit_log.jsonl
"""
from __future__ import annotations

import argparse, os, json, glob, sys
from datetime import datetime, UTC
from typing import Any, Dict


async def _connect_store():
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
    return store


def _write_audit_file(payload: Dict[str, Any]) -> None:
    os.makedirs("logs", exist_ok=True)
    rec = dict(payload)
    rec["ts"] = datetime.now(UTC).isoformat().replace('+00:00', 'Z')
    with open("logs/audit_log.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")


async def list_audit(limit: int, action: str | None) -> int:
    try:
        store = await _connect_store()
        # fetch last N
        where = " WHERE action = $action" if action else ""
        params = {"action": action} if action else {}
        rows = await store.query(f"SELECT * FROM audit_log ORDER BY ts DESC LIMIT {int(limit)}{where}", params)
        print(json.dumps(rows, indent=2))
        return 0
    except Exception:
        # fallback to file
        try:
            entries = []
            with open("logs/audit_log.jsonl") as f:
                for line in f:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
            if action:
                entries = [e for e in entries if e.get("action") == action]
            for e in entries[-limit:][::-1]:
                print(json.dumps(e, indent=2))
            return 0
        except Exception as e:
            print("Error reading audit log:", e, file=sys.stderr)
            return 1


def _latest_proposal_json() -> str | None:
    paths = sorted(glob.glob("logs/promotion_proposal_*.json"))
    return paths[-1] if paths else None


async def show_proposal(latest: bool, path: str | None) -> int:
    js = path or (_latest_proposal_json() if latest else None)
    if not js or not os.path.exists(js):
        print("No proposal found", file=sys.stderr)
        return 2
    print(open(js).read())
    return 0


async def apply_proposal(latest: bool, path: str | None, dry_run: bool) -> int:
    js = path or (_latest_proposal_json() if latest else None)
    if not js or not os.path.exists(js):
        print("No proposal found", file=sys.stderr)
        return 2
    data = json.load(open(js))
    weights = data.get("suggested_weights") or {}
    actor = os.getenv("GITHUB_ACTOR") or os.getenv("CI_ACTOR") or "cli"
    reason = f"apply_proposal {os.path.basename(js)}"

    # Try DB apply; if unavailable, print SQL and file-log
    try:
        store = await _connect_store()
        before_rows = await store.fetch_weights_for_domains(list(weights.keys()))
        if not dry_run:
            await store.apply_domain_multipliers(weights)
        await store.store_audit_log(
            action="weights_applied" + ("_dry_run" if dry_run else ""),
            actor=actor,
            reason=reason,
            before={"rows": before_rows},
            after={"domain_multipliers": weights},
            metadata={"proposal": os.path.basename(js)},
        )
        print(("Dry-run: " if dry_run else "") + "Applied proposal to routing_weight")
        return 0
    except Exception as e:
        # Fallback: file log + emit SQL to stdout
        print("DB unavailable; printing SQL you can run manually:\n", file=sys.stderr)
        for dom, mult in weights.items():
            print(
                "UPDATE routing_weight SET weight = math::max(0.1, math::min(2.0, weight * %.3f)), update_count = update_count + 1, last_updated = time::now() WHERE domain = '%s';"
                % (float(mult), dom)
            )
        _write_audit_file({
            "action": "weights_applied" + ("_dry_run" if dry_run else ""),
            "actor": actor,
            "reason": reason,
            "before": None,
            "after": {"domain_multipliers": weights},
            "metadata": {"proposal": os.path.basename(js)},
        })
        return 0


async def rollback(from_audit: str, dry_run: bool) -> int:
    # Lookup audit entry for 'weights_applied' and use its 'before' snapshot
    try:
        store = await _connect_store()
        rows = await store.query("SELECT * FROM audit_log WHERE id = $id", {"id": from_audit})
        entry = rows[0] if rows else None
        if not entry:
            print("Audit entry not found", file=sys.stderr)
            return 2
        before_rows = (entry.get("before") or {}).get("rows") or []
        # reconstruct set statements per row
        if not before_rows:
            print("No 'before' snapshot in audit entry; cannot rollback", file=sys.stderr)
            return 3
        # Group by domain: set absolute weights per (domain, agent)
        if dry_run:
            print("-- Dry-run rollback statements")
        for r in before_rows:
            dom = r.get("domain"); agent = r.get("agent"); w = float(r.get("weight", 1.0))
            sql = "UPDATE routing_weight SET weight = %.6f, last_updated = time::now() WHERE domain = '%s' AND agent = '%s';" % (w, dom, agent)
            if dry_run:
                print(sql)
            else:
                await store.query("UPDATE routing_weight SET weight = $w, last_updated = time::now() WHERE domain = $d AND agent = $a", {"w": w, "d": dom, "a": agent})
        await store.store_audit_log(
            action="weights_rollback" + ("_dry_run" if dry_run else ""),
            actor=os.getenv("GITHUB_ACTOR") or os.getenv("CI_ACTOR") or "cli",
            reason=f"rollback from audit {from_audit}",
            before=None,
            after={"restored_from": from_audit},
            metadata=None,
        )
        print(("Dry-run: " if dry_run else "") + "Rollback complete")
        return 0
    except Exception as e:
        print("DB unavailable or error:", e, file=sys.stderr)
        return 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("list-audit")
    sp.add_argument("--limit", type=int, default=10)
    sp.add_argument("--action")

    sp = sub.add_parser("show-proposal")
    sp.add_argument("--latest", action="store_true")
    sp.add_argument("--path")

    sp = sub.add_parser("apply-proposal")
    sp.add_argument("--latest", action="store_true")
    sp.add_argument("--path")
    sp.add_argument("--dry-run", action="store_true")

    sp = sub.add_parser("rollback")
    sp.add_argument("--from-audit", required=True)
    sp.add_argument("--dry-run", action="store_true")

    args = ap.parse_args(argv)

    import asyncio
    if args.cmd == "list-audit":
        return asyncio.run(list_audit(args.limit, args.action))
    if args.cmd == "show-proposal":
        return asyncio.run(show_proposal(args.latest, args.path))
    if args.cmd == "apply-proposal":
        return asyncio.run(apply_proposal(args.latest, args.path, args.dry_run))
    if args.cmd == "rollback":
        return asyncio.run(rollback(args.from_audit, args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

