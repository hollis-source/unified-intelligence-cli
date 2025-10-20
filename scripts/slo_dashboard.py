#!/usr/bin/env python3
"""
SLO Dashboard CLI
- Real-time SLO compliance monitoring
- Generates compliance reports
- Displays red/yellow/green indicators

Usage:
  python scripts/slo_dashboard.py --watch
  python scripts/slo_dashboard.py --report --output logs/slo_report.md
"""
from __future__ import annotations

import argparse
import json
import time
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.slo.slo_monitor import SLOMonitor
from src.slo.slo_definitions import SLODefinitions, SLOStatus


def get_status_indicator(status: SLOStatus) -> str:
    """Get colored status indicator."""
    if status == SLOStatus.COMPLIANT:
        return "🟢 COMPLIANT"
    elif status == SLOStatus.WARNING:
        return "🟡 WARNING"
    else:
        return "🔴 VIOLATED"


def display_dashboard(monitor: SLOMonitor):
    """Display real-time SLO dashboard."""
    report = monitor.get_compliance_report()
    summary = report["compliance_summary"]
    
    # Clear screen (ANSI escape code)
    print("\033[2J\033[H")
    
    print("="*70)
    print("SLO COMPLIANCE DASHBOARD")
    print(f"Updated: {report['timestamp']}")
    print("="*70)
    print()
    
    # Overall compliance
    compliance_rate = summary["compliance_rate"] * 100
    if compliance_rate >= 100:
        status_icon = "🟢"
    elif compliance_rate >= 80:
        status_icon = "🟡"
    else:
        status_icon = "🔴"
    
    print(f"{status_icon} Overall Compliance: {compliance_rate:.1f}%")
    print(f"   Compliant: {summary['compliant']}/{summary['total_slos']}")
    print(f"   Warnings: {summary['warnings']}")
    print(f"   Violations: {summary['violations']}")
    print()
    
    # Individual SLOs
    print("SLO Status:")
    print("-" * 70)
    
    metrics = monitor.get_aggregated_metrics(window_minutes=5)
    
    for slo in SLODefinitions.get_all_slos():
        if slo.metric in metrics:
            actual = metrics[slo.metric]
            status = slo.check_compliance(actual)
            indicator = get_status_indicator(status)
            
            # Format values
            if slo.comparison == "lt":
                comparison_str = f"{actual:.2f} < {slo.target_value:.2f}"
            elif slo.comparison == "gt":
                comparison_str = f"{actual:.2f} > {slo.target_value:.2f}"
            else:
                comparison_str = f"{actual:.2f} ≈ {slo.target_value:.2f}"
            
            print(f"{indicator:20} {slo.name:20} {comparison_str}")
        else:
            print(f"⚪ NO DATA         {slo.name:20} (no metrics)")
    
    print()
    
    # Active violations
    if report["active_violations"]:
        print("Active Violations:")
        print("-" * 70)
        for v in report["active_violations"]:
            duration = v.get("duration_seconds", 0)
            print(f"🔴 {v['slo']:20} {v['severity']:10} Duration: {duration}s")
            print(f"   Target: {v['target']:.2f}, Actual: {v['actual']:.2f}")
        print()
    
    # Statistics
    stats = report["statistics"]
    print("Statistics:")
    print(f"  Total checks: {stats['total_checks']}")
    print(f"  Total violations: {stats['total_violations']}")
    print(f"  Total warnings: {stats['total_warnings']}")
    print(f"  Violation rate: {stats['violation_rate']*100:.2f}%")
    print()
    
    # Rollback recommendation
    if monitor.should_trigger_rollback():
        print("⚠️  RECOMMENDATION: TRIGGER ROLLBACK")
        print("   Critical SLO violations detected for >5 minutes")
        print()


def generate_report(monitor: SLOMonitor, output_path: Path):
    """Generate SLO compliance report."""
    report = monitor.get_compliance_report()
    summary = report["compliance_summary"]
    
    lines = [
        "# SLO Compliance Report",
        f"Generated: {report['timestamp']}",
        "",
        "## Summary",
        f"- Overall Compliance: {summary['compliance_rate']*100:.1f}%",
        f"- Compliant SLOs: {summary['compliant']}/{summary['total_slos']}",
        f"- Warnings: {summary['warnings']}",
        f"- Violations: {summary['violations']}",
        "",
    ]
    
    # SLO details
    lines.extend([
        "## SLO Status",
        "",
        "| SLO | Metric | Target | Actual | Status |",
        "|-----|--------|--------|--------|--------|",
    ])
    
    metrics = monitor.get_aggregated_metrics(window_minutes=5)
    
    for slo in SLODefinitions.get_all_slos():
        if slo.metric in metrics:
            actual = metrics[slo.metric]
            status = slo.check_compliance(actual)
            status_str = status.value.upper()
            
            lines.append(
                f"| {slo.name} | {slo.metric} | {slo.target_value:.2f} | "
                f"{actual:.2f} | {status_str} |"
            )
    
    lines.append("")
    
    # Active violations
    if report["active_violations"]:
        lines.extend([
            "## Active Violations",
            "",
        ])
        
        for v in report["active_violations"]:
            duration = v.get("duration_seconds", 0)
            lines.extend([
                f"### {v['slo']} ({v['severity']})",
                f"- Target: {v['target']:.2f}",
                f"- Actual: {v['actual']:.2f}",
                f"- Duration: {duration}s",
                "",
            ])
    
    # Statistics
    stats = report["statistics"]
    lines.extend([
        "## Statistics",
        f"- Total checks: {stats['total_checks']}",
        f"- Total violations: {stats['total_violations']}",
        f"- Total warnings: {stats['total_warnings']}",
        f"- Violation rate: {stats['violation_rate']*100:.2f}%",
        "",
    ])
    
    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    
    # Also write JSON
    json_path = output_path.with_suffix(".json")
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    
    print(f"Report written to: {output_path}")
    print(f"JSON written to: {json_path}")


def watch_mode(monitor: SLOMonitor, interval: int = 5):
    """Watch mode - continuously update dashboard."""
    print("Starting SLO dashboard in watch mode...")
    print(f"Refresh interval: {interval}s")
    print("Press Ctrl+C to exit")
    print()
    
    try:
        while True:
            # Simulate metric collection (in production, this would come from real metrics)
            # For demo, use mock data
            import random
            monitor.record_metric("p95_latency_ms", random.uniform(300, 600))
            monitor.record_metric("p99_latency_ms", random.uniform(500, 1200))
            monitor.record_metric("accuracy_pct", random.uniform(80, 95))
            monitor.record_metric("cost_usd", random.uniform(0.05, 0.15))
            monitor.record_metric("availability_pct", random.uniform(98, 100))
            monitor.record_metric("error_rate_pct", random.uniform(0, 8))
            
            # Check violations
            monitor.check_violations()
            
            # Display dashboard
            display_dashboard(monitor)
            
            # Wait
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\nExiting...")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true", help="Watch mode (continuous updates)")
    ap.add_argument("--report", action="store_true", help="Generate report")
    ap.add_argument("--output", default="logs/slo_report.md", help="Report output path")
    ap.add_argument("--interval", type=int, default=5, help="Watch mode refresh interval (seconds)")
    
    args = ap.parse_args(argv)
    
    # Initialize monitor
    monitor = SLOMonitor()
    
    if args.watch:
        watch_mode(monitor, interval=args.interval)
    
    elif args.report:
        # Collect some metrics first (in production, these would be real)
        import random
        for _ in range(10):
            monitor.record_metric("p95_latency_ms", random.uniform(300, 600))
            monitor.record_metric("p99_latency_ms", random.uniform(500, 1200))
            monitor.record_metric("accuracy_pct", random.uniform(80, 95))
            monitor.record_metric("cost_usd", random.uniform(0.05, 0.15))
            monitor.record_metric("availability_pct", random.uniform(98, 100))
            monitor.record_metric("error_rate_pct", random.uniform(0, 8))
        
        monitor.check_violations()
        generate_report(monitor, Path(args.output))
    
    else:
        # Single snapshot
        display_dashboard(monitor)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

