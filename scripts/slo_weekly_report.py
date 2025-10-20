#!/usr/bin/env python3
"""
SLO Weekly Report Generator
- Generates weekly SLO compliance reports
- Tracks historical trends
- Identifies incident timeline

Usage:
  python scripts/slo_weekly_report.py --days 7 --output logs/slo_weekly.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.slo.slo_definitions import SLODefinitions


def generate_weekly_report(days: int, output_path: Path):
    """Generate weekly SLO compliance report."""
    
    # In production, this would query actual metrics from DB
    # For now, generate mock data
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Mock data: daily compliance rates
    daily_compliance = {}
    incidents = []
    
    import random
    random.seed(42)  # Reproducible
    
    for i in range(days):
        date = start_date + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        
        # Generate mock compliance (mostly good, occasional violations)
        compliance_rate = random.uniform(0.85, 1.0)
        daily_compliance[date_str] = compliance_rate
        
        # Generate mock incidents
        if compliance_rate < 0.95:
            incidents.append({
                "date": date_str,
                "slo": random.choice(["latency_p95", "accuracy", "availability"]),
                "duration_minutes": random.randint(5, 60),
                "severity": random.choice(["critical", "high", "medium"]),
            })
    
    # Calculate statistics
    avg_compliance = sum(daily_compliance.values()) / len(daily_compliance)
    min_compliance = min(daily_compliance.values())
    max_compliance = max(daily_compliance.values())
    
    # Build report
    lines = [
        "# SLO Weekly Compliance Report",
        f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Summary",
        f"- Average Compliance: {avg_compliance*100:.1f}%",
        f"- Min Compliance: {min_compliance*100:.1f}%",
        f"- Max Compliance: {max_compliance*100:.1f}%",
        f"- Total Incidents: {len(incidents)}",
        "",
    ]
    
    # Daily compliance
    lines.extend([
        "## Daily Compliance",
        "",
        "| Date | Compliance | Status |",
        "|------|------------|--------|",
    ])
    
    for date_str, compliance in sorted(daily_compliance.items()):
        if compliance >= 0.95:
            status = "🟢 Good"
        elif compliance >= 0.85:
            status = "🟡 Warning"
        else:
            status = "🔴 Poor"
        
        lines.append(f"| {date_str} | {compliance*100:.1f}% | {status} |")
    
    lines.append("")
    
    # SLO breakdown
    lines.extend([
        "## SLO Breakdown",
        "",
    ])
    
    for slo in SLODefinitions.get_all_slos():
        # Mock compliance for each SLO
        slo_compliance = random.uniform(0.85, 1.0)
        
        if slo_compliance >= 0.95:
            status = "🟢"
        elif slo_compliance >= 0.85:
            status = "🟡"
        else:
            status = "🔴"
        
        lines.append(f"- {status} **{slo.name}**: {slo_compliance*100:.1f}% compliant")
        lines.append(f"  - Target: {slo.description}")
    
    lines.append("")
    
    # Incident timeline
    if incidents:
        lines.extend([
            "## Incident Timeline",
            "",
        ])
        
        for incident in sorted(incidents, key=lambda x: x["date"]):
            severity_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
            }.get(incident["severity"], "⚪")
            
            lines.append(
                f"- {severity_icon} **{incident['date']}**: {incident['slo']} violated "
                f"for {incident['duration_minutes']} minutes ({incident['severity']})"
            )
        
        lines.append("")
    
    # Recommendations
    lines.extend([
        "## Recommendations",
        "",
    ])
    
    if avg_compliance < 0.95:
        lines.append("- ⚠️ Average compliance below 95% - investigate root causes")
    
    if len(incidents) > 5:
        lines.append(f"- ⚠️ {len(incidents)} incidents in {days} days - review SLO targets")
    
    # Group incidents by SLO
    incidents_by_slo = defaultdict(int)
    for incident in incidents:
        incidents_by_slo[incident["slo"]] += 1
    
    for slo, count in sorted(incidents_by_slo.items(), key=lambda x: x[1], reverse=True):
        if count >= 3:
            lines.append(f"- ⚠️ {slo} violated {count} times - prioritize optimization")
    
    if not lines[-1].startswith("-"):
        lines.append("- ✅ No major issues detected")
    
    lines.append("")
    
    # Next steps
    lines.extend([
        "## Next Steps",
        "",
        "1. Review incident timeline and identify patterns",
        "2. Investigate SLOs with multiple violations",
        "3. Update SLO targets if consistently violated",
        "4. Implement auto-remediation for common issues",
        "5. Schedule post-incident reviews for critical incidents",
    ])
    
    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    
    # Also write JSON
    json_path = output_path.with_suffix(".json")
    json_data = {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "summary": {
            "avg_compliance": avg_compliance,
            "min_compliance": min_compliance,
            "max_compliance": max_compliance,
            "total_incidents": len(incidents),
        },
        "daily_compliance": daily_compliance,
        "incidents": incidents,
    }
    json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
    
    print(f"Report written to: {output_path}")
    print(f"JSON written to: {json_path}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7, help="Number of days to analyze")
    ap.add_argument("--output", default="logs/slo_weekly.md", help="Output report path")
    
    args = ap.parse_args(argv)
    
    generate_weekly_report(args.days, Path(args.output))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

