#!/usr/bin/env python3
"""
Generate Missing Templates (DRAFTs)
- Scan tasks/ for per-domain template counts
- For domains with <5 templates, generate stub YAMLs under tasks/_generated/
- Mark as DRAFT, for human review before use

Usage:
  python scripts/generate_missing_templates.py --min 5 --dry-run
  python scripts/generate_missing_templates.py --min 5 --domains backend,qa
"""
from __future__ import annotations

import argparse, os, json
from pathlib import Path
from typing import Dict, List
from datetime import datetime

TEMPLATE_SKELETON = """# DRAFT: Auto-generated template for human review
# status: DRAFT (do not commit to production without review)
# generated: {ts}
# domain: {domain}
# rationale: This draft was generated to increase coverage in an under-represented domain.
# guideline: Ensure specificity, include file:line references when applicable, add acceptance criteria.
---
name: "{domain} draft task {idx}"
domain: "{domain}"
description: |
  Write a clear, testable task in the {domain} domain.
  Include:
  - Specific files or components to touch
  - Expected outputs and acceptance criteria
  - Edge cases
  - Constraints and performance considerations
inputs:
  context: "Provide any context needed for the task"
acceptance_criteria:
  - "Tests pass (add or update tests as needed)"
  - "Clear, minimal diff with reasoning"
  - "No regressions in related modules"
notes:
  - "Replace this draft with a concrete, domain-specific task"
"""


def count_templates(tasks_dir: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for p in tasks_dir.rglob('*.yaml'):
        try:
            # domain inferred from yaml content or directory name; here infer from parent
            d = p.parent.name
            counts[d] = counts.get(d, 0) + 1
        except Exception:
            pass
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--tasks-dir', default=str(Path(__file__).parent.parent / 'tasks'))
    ap.add_argument('--min', type=int, default=5, dest='min_count')
    ap.add_argument('--domains', help='Comma-separated domains to restrict')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    tasks_dir = Path(args.tasks_dir)
    out_dir = tasks_dir / '_generated'
    out_dir.mkdir(parents=True, exist_ok=True)

    restrict = set([s.strip() for s in args.domains.split(',')]) if args.domains else None

    counts = count_templates(tasks_dir)
    ts = datetime.utcnow().isoformat() + 'Z'

    targets: List[str] = []
    for domain, c in sorted(counts.items()):
        if restrict and domain not in restrict:
            continue
        if c < args.min_count:
            targets.append(domain)

    if not targets:
        print('No domains below threshold; nothing to generate.')
        return 0

    for domain in targets:
        # create up to (min_count - current) drafts capped at 5
        needed = min(args.min_count - counts.get(domain, 0), 5)
        for i in range(needed):
            idx = counts.get(domain, 0) + i + 1
            name = f"{domain}-draft-{idx:02d}.yaml"
            path = out_dir / name
            content = TEMPLATE_SKELETON.format(ts=ts, domain=domain, idx=idx)
            print(('DRY RUN - would write: ' if args.dry_run else 'Writing: ') + str(path))
            if not args.dry_run:
                path.write_text(content, encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

