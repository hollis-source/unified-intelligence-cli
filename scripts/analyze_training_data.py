#!/usr/bin/env python3
"""
Analyze collected training data quality.

Week 9 Phase 1: Data quality analysis for fine-tuning preparation.
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime


def analyze_training_data(jsonl_file: str):
    """
    Analyze collected training data from JSONL file.

    Args:
        jsonl_file: Path to JSONL file containing interactions
    """
    interactions = []

    # Load all interactions
    with open(jsonl_file, 'r') as f:
        for line in f:
            interactions.append(json.loads(line))

    # Basic statistics
    total_interactions = len(interactions)

    # Agent distribution
    agent_counts = Counter(i['agent']['role'] for i in interactions)

    # Provider distribution
    provider_counts = Counter(i['llm']['provider'] for i in interactions)

    # Status distribution
    status_counts = Counter(i['execution']['status'] for i in interactions)

    # Execution times
    durations = [i['execution']['duration_ms'] for i in interactions]
    avg_duration = sum(durations) / len(durations) if durations else 0
    min_duration = min(durations) if durations else 0
    max_duration = max(durations) if durations else 0

    # Token counts (estimate from output length)
    output_lengths = []
    for i in interactions:
        if i['execution']['output']:
            output_lengths.append(len(i['execution']['output']))
    avg_output_len = sum(output_lengths) / len(output_lengths) if output_lengths else 0

    # Input message analysis
    total_messages = sum(len(i['execution']['input_messages']) for i in interactions)
    avg_messages = total_messages / total_interactions

    # Time range
    timestamps = [datetime.fromisoformat(i['timestamp'].replace('Z', '+00:00')) for i in interactions]
    earliest = min(timestamps)
    latest = max(timestamps)
    duration_hours = (latest - earliest).total_seconds() / 3600

    # Print report
    print("=" * 80)
    print("TRAINING DATA COLLECTION REPORT")
    print("=" * 80)
    print(f"\nFile: {jsonl_file}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n📊 OVERVIEW")
    print(f"  Total Interactions: {total_interactions}")
    print(f"  Collection Period: {earliest.strftime('%Y-%m-%d %H:%M')} to {latest.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Duration: {duration_hours:.2f} hours")

    print(f"\n🤖 AGENT DISTRIBUTION")
    for agent, count in agent_counts.most_common():
        percentage = (count / total_interactions) * 100
        print(f"  {agent:12s}: {count:3d} ({percentage:5.1f}%)")

    print(f"\n🔌 PROVIDER DISTRIBUTION")
    for provider, count in provider_counts.most_common():
        percentage = (count / total_interactions) * 100
        print(f"  {provider:12s}: {count:3d} ({percentage:5.1f}%)")

    print(f"\n✅ STATUS DISTRIBUTION")
    for status, count in status_counts.most_common():
        percentage = (count / total_interactions) * 100
        print(f"  {status:12s}: {count:3d} ({percentage:5.1f}%)")

    print(f"\n⏱️  EXECUTION PERFORMANCE")
    print(f"  Average Duration: {avg_duration:,.0f} ms ({avg_duration/1000:.2f}s)")
    print(f"  Min Duration:     {min_duration:,.0f} ms")
    print(f"  Max Duration:     {max_duration:,.0f} ms")

    print(f"\n📝 DATA CHARACTERISTICS")
    print(f"  Avg Messages per Interaction: {avg_messages:.1f}")
    print(f"  Avg Output Length: {avg_output_len:,.0f} chars")
    print(f"  Est. Avg Tokens: {avg_output_len/4:,.0f} (rough estimate)")

    # Quality metrics
    print(f"\n🎯 QUALITY METRICS")
    success_rate = (status_counts['success'] / total_interactions) * 100
    print(f"  Success Rate: {success_rate:.1f}%")

    # Diversity
    unique_task_descriptions = len(set(i['task']['description'] for i in interactions))
    print(f"  Unique Tasks: {unique_task_descriptions} ({unique_task_descriptions/total_interactions*100:.1f}% unique)")

    # Sample tasks
    print(f"\n📋 SAMPLE TASKS")
    for i, interaction in enumerate(interactions[:3], 1):
        task_desc = interaction['task']['description']
        if len(task_desc) > 70:
            task_desc = task_desc[:70] + "..."
        print(f"  {i}. [{interaction['agent']['role']:8s}] {task_desc}")

    print(f"\n💡 RECOMMENDATIONS")
    print(f"  - Target: 300-1,500 interactions for initial fine-tuning")
    print(f"  - Current: {total_interactions} interactions collected")
    print(f"  - Progress: {(total_interactions/300)*100:.1f}% to minimum target")
    if total_interactions < 300:
        print(f"  - ⚠️  Continue data collection ({300-total_interactions} more needed for minimum)")
    else:
        print(f"  - ✅ Minimum threshold reached! Can proceed to Phase 2 (Evaluation)")

    print("\n" + "=" * 80)

    return {
        "total_interactions": total_interactions,
        "success_rate": success_rate,
        "avg_duration_ms": avg_duration,
        "agent_distribution": dict(agent_counts),
        "provider_distribution": dict(provider_counts)
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_training_data.py <jsonl_file>")
        sys.exit(1)

    jsonl_file = sys.argv[1]
    if not Path(jsonl_file).exists():
        print(f"Error: File not found: {jsonl_file}")
        sys.exit(1)

    analyze_training_data(jsonl_file)
