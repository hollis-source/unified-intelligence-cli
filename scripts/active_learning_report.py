#!/usr/bin/env python3
"""
Active Learning Report
- Identifies weak domains (low accuracy or few patterns)
- Generates prioritized collection recommendations
- Optionally auto-triggers collection jobs

Usage:
  python scripts/active_learning_report.py --output logs/active_learning.md
  python scripts/active_learning_report.py --auto-trigger --max-domains 3
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, UTC
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="logs/active_learning.md", help="Output report path")
    ap.add_argument("--min-accuracy", type=float, default=0.70, help="Minimum acceptable accuracy")
    ap.add_argument("--min-patterns", type=int, default=20, help="Minimum acceptable pattern count")
    ap.add_argument("--max-domains", type=int, default=5, help="Max domains to prioritize")
    ap.add_argument("--auto-trigger", action="store_true", help="Auto-trigger collection jobs")
    ap.add_argument("--balance", action="store_true", help="Balance pattern distribution")
    
    args = ap.parse_args(argv)
    
    try:
        from src.claude_orchestrator.use_cases.active_learning import ActiveLearning
        
        # Initialize active learning
        active_learning = ActiveLearning(db_store=None)  # TODO: wire DB store
        
        # Identify weak domains
        logger.info("Identifying weak domains...")
        weak_domains = active_learning.identify_weak_domains(
            min_accuracy=args.min_accuracy,
            min_patterns=args.min_patterns,
        )
        
        logger.info(f"Found {len(weak_domains)} weak domains")
        
        # Prioritize collection
        priorities = active_learning.prioritize_collection(
            weak_domains,
            max_domains=args.max_domains,
        )
        
        # Balance distribution if requested
        balance_targets = {}
        if args.balance:
            logger.info("Balancing pattern distribution...")
            balance_targets = active_learning.balance_pattern_distribution()
        
        # Auto-trigger if requested
        triggered = []
        if args.auto_trigger:
            logger.info("Auto-triggering collection jobs...")
            triggered = active_learning.auto_trigger_collection(
                weak_domains,
                max_domains=args.max_domains,
            )
        
        # Generate report
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        _write_report(
            output_path,
            weak_domains,
            priorities,
            balance_targets,
            triggered,
        )
        
        logger.info(f"Report written to: {output_path}")
        
        # Also write JSON
        json_path = output_path.with_suffix(".json")
        _write_json_report(
            json_path,
            weak_domains,
            priorities,
            balance_targets,
            triggered,
        )
        
        logger.info(f"JSON report written to: {json_path}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Active learning report failed: {e}", exc_info=True)
        return 1


def _write_report(
    output_path: Path,
    weak_domains: list,
    priorities: list,
    balance_targets: dict,
    triggered: list,
):
    """Write Markdown report."""
    lines = [
        "# Active Learning Report",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "",
        "## Summary",
        f"- Weak domains identified: {len(weak_domains)}",
        f"- Prioritized for collection: {len(priorities)}",
        f"- Balance targets: {len(balance_targets)}",
        f"- Auto-triggered: {len(triggered)}",
        "",
    ]
    
    if weak_domains:
        lines.extend([
            "## Weak Domains",
            "",
            "| Domain | Accuracy | Patterns | Weakness Score | Priority | Recommendation |",
            "|--------|----------|----------|----------------|----------|----------------|",
        ])
        
        for domain in weak_domains:
            lines.append(
                f"| {domain.domain} | {domain.accuracy:.1%} | {domain.pattern_count} | "
                f"{domain.weakness_score:.3f} | P{domain.priority} | {domain.recommendation} |"
            )
        
        lines.append("")
    
    if priorities:
        lines.extend([
            "## Collection Priorities",
            "",
        ])
        
        for i, (domain, target_count) in enumerate(priorities, 1):
            lines.append(f"{i}. **{domain}**: Collect to {target_count} patterns")
        
        lines.append("")
    
    if balance_targets:
        lines.extend([
            "## Balance Targets",
            "",
        ])
        
        for domain, target in balance_targets.items():
            lines.append(f"- **{domain}**: Target {target} patterns")
        
        lines.append("")
    
    if triggered:
        lines.extend([
            "## Auto-Triggered Jobs",
            "",
        ])
        
        for domain in triggered:
            lines.append(f"- {domain}")
        
        lines.append("")
    
    lines.extend([
        "## Next Steps",
        "",
        "1. Review weak domains and recommendations",
        "2. Run pattern collection for prioritized domains:",
        "   ```bash",
        "   python scripts/build_rag_patterns.py --balance-source",
        "   ```",
        "3. Monitor accuracy improvements after collection",
        "4. Re-run this report weekly to track progress",
    ])
    
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _write_json_report(
    output_path: Path,
    weak_domains: list,
    priorities: list,
    balance_targets: dict,
    triggered: list,
):
    """Write JSON report."""
    data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "weak_domains": [
            {
                "domain": d.domain,
                "accuracy": d.accuracy,
                "pattern_count": d.pattern_count,
                "weakness_score": d.weakness_score,
                "priority": d.priority,
                "recommendation": d.recommendation,
            }
            for d in weak_domains
        ],
        "priorities": [
            {"domain": domain, "target_count": count}
            for domain, count in priorities
        ],
        "balance_targets": balance_targets,
        "triggered": triggered,
    }
    
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

