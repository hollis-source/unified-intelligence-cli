#!/usr/bin/env python3
"""
Metrics Viewer - Display routing and model selection metrics.

Week 13: Priority 3 - Monitoring & Metrics.

Usage:
    python3 scripts/view_metrics.py [session_file]
    python3 scripts/view_metrics.py --latest
"""

import json
import sys
from pathlib import Path
from typing import Optional


def find_latest_session(metrics_dir: Path) -> Optional[Path]:
    """Find the most recent metrics session file."""
    session_files = sorted(metrics_dir.glob("session_*.json"), reverse=True)
    return session_files[0] if session_files else None


def format_percentage(value: float) -> str:
    """Format percentage with color coding."""
    if value >= 90:
        return f"\033[92m{value}%\033[0m"  # Green
    elif value >= 70:
        return f"\033[93m{value}%\033[0m"  # Yellow
    else:
        return f"\033[91m{value}%\033[0m"  # Red


def display_metrics(metrics_file: Path) -> None:
    """Display metrics from a session file."""
    with open(metrics_file) as f:
        data = json.load(f)

    summary = data.get("summary", {})
    routing_metrics = data.get("routing_metrics", [])
    model_metrics = data.get("model_metrics", [])

    print("\n" + "="*70)
    print(f"  Metrics Session: {data.get('session_id', 'unknown')}")
    print(f"  Timestamp: {data.get('timestamp', 'unknown')}")
    print("="*70)

    # Summary
    print("\n📊 SUMMARY")
    print("-" * 70)
    routing_accuracy = summary.get("routing_accuracy", 0)
    print(f"Routing Accuracy:       {format_percentage(routing_accuracy)}")
    print(f"Routing Decisions:      {summary.get('total_routing_decisions', 0)}")
    print(f"Correct Routings:       {summary.get('correct_routing_decisions', 0)}")
    print(f"Model Selections:       {summary.get('total_model_selections', 0)}")

    fallback_rate = summary.get("fallback_usage_rate", 0)
    print(f"Fallback Usage:         {format_percentage(fallback_rate)}")

    # Model breakdown
    print("\n🤖 MODEL SELECTION BREAKDOWN")
    print("-" * 70)
    for model, count in summary.get("model_selection_breakdown", {}).items():
        print(f"{model:20s}: {count:3d} uses")

    # Team utilization
    print("\n👥 TEAM UTILIZATION")
    print("-" * 70)
    team_util = summary.get("team_utilization", {})
    if team_util:
        for team, count in sorted(team_util.items(), key=lambda x: x[1], reverse=True):
            print(f"{team:20s}: {count:3d} tasks")
    else:
        print("No team utilization data")

    # Recent routing decisions
    if routing_metrics:
        print("\n🔀 RECENT ROUTING DECISIONS")
        print("-" * 70)
        for metric in routing_metrics[-5:]:  # Last 5
            task = metric["task_description"]
            domain = metric["classified_domain"]
            score = metric["domain_score"]
            team = metric["target_team"]
            agent = metric["target_agent"]
            is_correct = metric.get("is_correct")

            status = ""
            if is_correct is True:
                status = "\033[92m✓\033[0m"
            elif is_correct is False:
                status = "\033[91m✗\033[0m"

            print(f"{status} [{domain:15s}] score:{score:5.1f} → {team} → {agent}")
            print(f"   Task: {task[:60]}...")

    # Recent model selections
    if model_metrics:
        print("\n⚡ RECENT MODEL SELECTIONS")
        print("-" * 70)
        for metric in model_metrics[-5:]:  # Last 5
            task = metric["task_description"]
            model = metric["selected_model"]
            criteria = metric["criteria"]
            latency = metric["latency_seconds"]
            success = metric["success"]
            fallback = metric["fallback_used"]

            status = "\033[92m✓\033[0m" if success else "\033[91m✗\033[0m"
            fallback_indicator = " (FALLBACK)" if fallback else ""

            print(f"{status} {model:15s} [{criteria:8s}] {latency:5.1f}s{fallback_indicator}")
            print(f"   Task: {task[:60]}...")

    print("\n" + "="*70 + "\n")


def main():
    """Main entry point."""
    metrics_dir = Path("data/metrics")

    if not metrics_dir.exists():
        print(f"Error: Metrics directory not found: {metrics_dir}")
        print("Run tasks with metrics collection enabled first.")
        sys.exit(1)

    # Parse arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--latest":
            metrics_file = find_latest_session(metrics_dir)
            if not metrics_file:
                print("Error: No metrics sessions found")
                sys.exit(1)
        else:
            metrics_file = Path(sys.argv[1])
            if not metrics_file.exists():
                print(f"Error: Metrics file not found: {metrics_file}")
                sys.exit(1)
    else:
        # Default: latest session
        metrics_file = find_latest_session(metrics_dir)
        if not metrics_file:
            print("Error: No metrics sessions found")
            sys.exit(1)

    print(f"\nLoading metrics from: {metrics_file.name}")
    display_metrics(metrics_file)


if __name__ == "__main__":
    main()
