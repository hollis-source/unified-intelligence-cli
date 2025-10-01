#!/usr/bin/env python3
"""
Analyze collected training data to extract baseline metrics.

Week 9 Phase 2: Use existing 302 interactions as baseline evaluation.
"""

import json
import statistics
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter


def load_interactions(jsonl_file: Path) -> List[Dict]:
    """Load interaction data from JSONL."""
    interactions = []
    with open(jsonl_file, 'r') as f:
        for line in f:
            interactions.append(json.loads(line))
    return interactions


def analyze_baseline(interactions: List[Dict]) -> Dict[str, Any]:
    """
    Calculate baseline metrics from collected interactions.

    Metrics:
    - Success rate (% of successful executions)
    - Avg duration (ms)
    - Agent distribution
    - Provider distribution
    - Task complexity metrics
    """
    # Filter successful interactions (status="success")
    successful = [i for i in interactions if i["execution"]["status"] == "success"]
    failed = [i for i in interactions if i["execution"]["status"] != "success"]

    # Success rate
    success_rate = len(successful) / len(interactions) if interactions else 0.0

    # Duration statistics (successful only)
    durations = [i["execution"]["duration_ms"] for i in successful]
    avg_duration = statistics.mean(durations) if durations else 0.0
    median_duration = statistics.median(durations) if durations else 0.0
    min_duration = min(durations) if durations else 0.0
    max_duration = max(durations) if durations else 0.0

    # Agent distribution
    agent_dist = Counter(i["agent"]["role"] for i in interactions)

    # Provider distribution
    provider_dist = Counter(i["llm"]["provider"] for i in interactions)

    # Model distribution
    model_dist = Counter(i["llm"]["model"] for i in interactions)

    # Task analysis
    task_lengths = [len(i["task"]["description"]) for i in interactions]
    avg_task_length = statistics.mean(task_lengths) if task_lengths else 0.0

    # Output analysis (successful only)
    output_lengths = [len(i["execution"]["output"]) for i in successful if i["execution"]["output"]]
    avg_output_length = statistics.mean(output_lengths) if output_lengths else 0.0

    return {
        "total_interactions": len(interactions),
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": success_rate,
        "duration_stats": {
            "avg_ms": avg_duration,
            "median_ms": median_duration,
            "min_ms": min_duration,
            "max_ms": max_duration,
            "avg_s": avg_duration / 1000,
            "median_s": median_duration / 1000
        },
        "agent_distribution": dict(agent_dist),
        "provider_distribution": dict(provider_dist),
        "model_distribution": dict(model_dist),
        "task_metrics": {
            "avg_task_length_chars": avg_task_length,
            "avg_output_length_chars": avg_output_length
        }
    }


def print_baseline_report(metrics: Dict[str, Any]):
    """Print comprehensive baseline report."""
    print("=" * 80)
    print("BASELINE METRICS - Week 9 Phase 2")
    print("=" * 80)
    print(f"\n📊 Dataset Overview:")
    print(f"  Total interactions:  {metrics['total_interactions']}")
    print(f"  ✓ Successful:        {metrics['successful']} ({metrics['success_rate']:.1%})")
    print(f"  ✗ Failed:            {metrics['failed']}")

    print(f"\n⚡ Performance (successful tasks only):")
    print(f"  Avg duration:        {metrics['duration_stats']['avg_s']:.1f}s")
    print(f"  Median duration:     {metrics['duration_stats']['median_s']:.1f}s")
    print(f"  Min/Max duration:    {metrics['duration_stats']['min_ms']/1000:.1f}s / {metrics['duration_stats']['max_ms']/1000:.1f}s")

    print(f"\n🤖 Agent Distribution:")
    for agent, count in sorted(metrics['agent_distribution'].items(), key=lambda x: x[1], reverse=True):
        pct = count / metrics['total_interactions'] * 100
        print(f"  {agent:15s}: {count:3d} ({pct:5.1f}%)")

    print(f"\n🔌 Provider Distribution:")
    for provider, count in metrics['provider_distribution'].items():
        pct = count / metrics['total_interactions'] * 100
        print(f"  {provider:15s}: {count:3d} ({pct:5.1f}%)")

    print(f"\n📝 Model Distribution:")
    for model, count in metrics['model_distribution'].items():
        model_name = model if model else "unknown"
        pct = count / metrics['total_interactions'] * 100
        print(f"  {model_name:40s}: {count:3d} ({pct:5.1f}%)")

    print(f"\n📏 Task Complexity:")
    print(f"  Avg task length:     {metrics['task_metrics']['avg_task_length_chars']:.0f} chars")
    print(f"  Avg output length:   {metrics['task_metrics']['avg_output_length_chars']:.0f} chars")

    print("\n" + "=" * 80)
    print("BASELINE ESTABLISHED ✅")
    print("=" * 80)
    print("\n📌 Key Findings:")
    print(f"  • Success rate: {metrics['success_rate']:.1%} (target for improvement: >95%)")
    print(f"  • Avg latency: {metrics['duration_stats']['avg_s']:.1f}s (target: <10s with fine-tuned 7B)")
    print(f"  • Primary model: {list(metrics['model_distribution'].keys())[0]}")
    print("\n🎯 Phase 3 Goals:")
    print("  • Fine-tune Qwen2.5-7B with LoRA on 302 interactions")
    print("  • Target: +5-10% success rate improvement")
    print("  • Target: 2x faster inference (smaller model)")
    print()


def main():
    # Load collected training data
    data_file = Path(__file__).parent.parent / "data" / "training" / "interactions_20251001.jsonl"

    if not data_file.exists():
        print(f"Error: Data file not found: {data_file}")
        return 1

    print(f"📂 Loading data from: {data_file}")
    interactions = load_interactions(data_file)
    print(f"✓ Loaded {len(interactions)} interactions\n")

    # Analyze
    metrics = analyze_baseline(interactions)

    # Print report
    print_baseline_report(metrics)

    # Save metrics
    output_file = Path(__file__).parent.parent / "results" / "baseline_metrics.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"💾 Baseline metrics saved to: {output_file}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
