#!/usr/bin/env python3
"""
Weekly RAG Report
- Summarize audit log entries (apply/rollback/proposals/previews)
- List latest promotion proposal
- Emit Markdown to logs/weekly_rag_report_<ts>.md
"""
from __future__ import annotations

import json, os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List


def load_audit_entries() -> List[Dict[str, Any]]:
    # Prefer DB in the future; for now, read file if present
    p = Path("logs/audit_log.jsonl")
    out: List[Dict[str, Any]] = []
    if p.exists():
        for line in p.read_text().splitlines():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def latest_proposal() -> Dict[str, Any] | None:
    paths = sorted(Path("logs").glob("promotion_proposal_*.json"))
    if not paths:
        return None
    try:
        return json.loads(paths[-1].read_text())
    except Exception:
        return None


def main() -> int:
    ts = datetime.now(timezone.utc)
    week_ago = ts - timedelta(days=7)

    entries = load_audit_entries()
    recent = []
    for e in entries:
        try:
            t = datetime.fromisoformat(e.get("ts","0").replace("Z","+00:00"))
        except Exception:
            t = None
        if t and t >= week_ago:
            recent.append(e)

    by_action = Counter(e.get("action") for e in recent)
    last_apply = next((e for e in reversed(recent) if str(e.get("action",""))
                       .startswith("weights_applied")), None)
    last_rollback = next((e for e in reversed(recent) if str(e.get("action",""))
                          .startswith("weights_rollback")), None)

    prop = latest_proposal()

    lines = [
        "# Weekly RAG Report",
        f"Generated: {ts.strftime('%Y-%m-%dT%H-%M-%SZ')}",
        "",
        "## Summary (last 7 days)",
        "- Audit entries: %d" % len(recent),
        "- By action:",
    ]
    for k,v in by_action.most_common():
        lines.append(f"  - {k}: {v}")

    lines += ["", "## Latest promotion proposal"]
    if prop:
        lines += [
            "- eligible: %s" % prop.get("eligible"),
            "- reason: %s" % prop.get("reason"),
            "- suggested_weights: %s" % (prop.get("suggested_weights") or {}),
        ]
    else:
        lines.append("- No proposal found")

    lines += ["", "## Recent actions"]
    if last_apply:
        lines.append("- Last apply: %s" % json.dumps(last_apply, indent=2))
    if last_rollback:
        lines.append("- Last rollback: %s" % json.dumps(last_rollback, indent=2))

    outdir = Path("logs"); outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / ("weekly_rag_report_" + ts.strftime('%Y-%m-%dT%H-%M-%SZ') + ".md")
    outpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote weekly report:", outpath)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

