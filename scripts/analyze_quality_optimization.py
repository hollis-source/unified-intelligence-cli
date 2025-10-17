#!/usr/bin/env python3
"""
Quality & Optimization Analysis for Week 2 Baseline

Focus:
1. Identify optimization opportunities (latency, failures)
2. Establish quality improvement targets

NOT analyzing: Cost, token counts (user request)
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any
import statistics


def load_baseline(path: Path) -> List[Dict[str, Any]]:
    """Load JSONL baseline data."""
    records = []
    with open(path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def analyze_quality_distribution(records: List[Dict]) -> Dict[str, Any]:
    """Analyze quality score patterns."""
    by_agent = defaultdict(list)
    by_score_range = defaultdict(list)

    for r in records:
        agent = r.get('agent', 'unknown')
        quality = r.get('quality', 0)
        auto_score = r.get('auto_score', 0)

        by_agent[agent].append(quality)

        # Categorize by score
        if quality >= 5.0:
            by_score_range['high'].append(r)
        elif quality >= 3.0:
            by_score_range['medium'].append(r)
        else:
            by_score_range['low'].append(r)

    # Stats per agent
    agent_stats = {}
    for agent, scores in by_agent.items():
        agent_stats[agent] = {
            'mean': statistics.mean(scores),
            'median': statistics.median(scores),
            'stdev': statistics.stdev(scores) if len(scores) > 1 else 0,
            'min': min(scores),
            'max': max(scores),
            'count': len(scores)
        }

    return {
        'agent_stats': agent_stats,
        'score_ranges': {k: len(v) for k, v in by_score_range.items()},
        'high_quality_tasks': by_score_range['high'],
        'low_quality_tasks': by_score_range['low']
    }


def analyze_failures(records: List[Dict]) -> Dict[str, Any]:
    """Identify failure patterns."""
    failures = [r for r in records if not r.get('ok', False)]
    timeouts = [r for r in records if r.get('error') and str(r.get('error', '')).startswith('Timeout')]
    check_failures = [r for r in records if not r.get('checks_ok', True)]

    by_agent = defaultdict(int)
    for r in failures:
        by_agent[r.get('agent', 'unknown')] += 1

    return {
        'total_failures': len(failures),
        'timeout_count': len(timeouts),
        'check_failures': len(check_failures),
        'failures_by_agent': dict(by_agent),
        'timeout_tasks': [r.get('task_id') for r in timeouts]
    }


def analyze_latency(records: List[Dict]) -> Dict[str, Any]:
    """Identify latency bottlenecks."""
    by_agent = defaultdict(list)

    for r in records:
        if r.get('ok', False):
            agent = r.get('agent', 'unknown')
            latency = r.get('latency', 0)
            by_agent[agent].append({
                'task_id': r.get('task_id'),
                'latency': latency,
                'quality': r.get('quality', 0)
            })

    # Stats per agent
    agent_latency = {}
    for agent, data in by_agent.items():
        latencies = [d['latency'] for d in data]
        agent_latency[agent] = {
            'mean': statistics.mean(latencies),
            'p50': statistics.median(latencies),
            'p95': sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
            'max': max(latencies) if latencies else 0,
            'slowest_task': max(data, key=lambda x: x['latency']) if data else None
        }

    return agent_latency


def analyze_specificity(records: List[Dict]) -> Dict[str, Any]:
    """Analyze file:line reference patterns."""
    specific_count = sum(1 for r in records if r.get('specific', False))
    non_specific = sum(1 for r in records if not r.get('specific', False))

    # Quality correlation
    specific_tasks = [r for r in records if r.get('specific', False)]
    non_specific_tasks = [r for r in records if not r.get('specific', False)]

    specific_quality = statistics.mean([r.get('quality', 0) for r in specific_tasks]) if specific_tasks else 0
    non_specific_quality = statistics.mean([r.get('quality', 0) for r in non_specific_tasks]) if non_specific_tasks else 0

    return {
        'specific_count': specific_count,
        'non_specific_count': non_specific,
        'specific_pct': (specific_count / len(records) * 100) if records else 0,
        'specific_avg_quality': specific_quality,
        'non_specific_avg_quality': non_specific_quality,
        'quality_delta': specific_quality - non_specific_quality
    }


def extract_high_quality_patterns(high_quality_tasks: List[Dict]) -> Dict[str, Any]:
    """Analyze what makes high-quality responses."""
    patterns = {
        'count': len(high_quality_tasks),
        'avg_length': statistics.mean([r.get('output_length', 0) for r in high_quality_tasks]) if high_quality_tasks else 0,
        'specific_pct': sum(1 for r in high_quality_tasks if r.get('specific', False)) / len(high_quality_tasks) * 100 if high_quality_tasks else 0,
        'agents': defaultdict(int)
    }

    for task in high_quality_tasks:
        patterns['agents'][task.get('agent', 'unknown')] += 1

    patterns['agents'] = dict(patterns['agents'])
    return patterns


def identify_optimization_opportunities(
    quality_analysis: Dict,
    failure_analysis: Dict,
    latency_analysis: Dict,
    specificity_analysis: Dict
) -> List[str]:
    """Generate actionable optimization recommendations."""
    opportunities = []

    # 1. Quality improvements
    avg_quality = statistics.mean([
        stats['mean']
        for stats in quality_analysis['agent_stats'].values()
    ])

    opportunities.append(f"**Quality Baseline:** {avg_quality:.1f}/10")
    opportunities.append(f"**Target:** 4.5/10 (+{4.5 - avg_quality:.1f} points)")

    # 2. Specificity opportunity
    spec_delta = specificity_analysis['quality_delta']
    if spec_delta > 0:
        opportunities.append(
            f"**Specificity Gap:** Tasks with file:line refs score {spec_delta:.1f} points higher "
            f"({specificity_analysis['specific_pct']:.0f}% currently specific)"
        )
        opportunities.append(
            f"  → **Action:** Add file:line reference examples to prompts"
        )

    # 3. High-performing agents
    best_agent = max(
        quality_analysis['agent_stats'].items(),
        key=lambda x: x[1]['mean']
    )
    worst_agent = min(
        quality_analysis['agent_stats'].items(),
        key=lambda x: x[1]['mean']
    )

    delta = best_agent[1]['mean'] - worst_agent[1]['mean']
    if delta > 0.5:
        opportunities.append(
            f"**Agent Performance Gap:** {best_agent[0]} ({best_agent[1]['mean']:.1f}/10) "
            f"outperforms {worst_agent[0]} ({worst_agent[1]['mean']:.1f}/10) by {delta:.1f} points"
        )
        opportunities.append(
            f"  → **Action:** Analyze {best_agent[0]} prompts/capabilities for patterns"
        )

    # 4. Latency bottlenecks
    slowest = max(
        latency_analysis.items(),
        key=lambda x: x[1]['p95']
    )
    if slowest[1]['p95'] > 30:
        opportunities.append(
            f"**Latency Bottleneck:** {slowest[0]} P95 = {slowest[1]['p95']:.1f}s "
            f"(slowest task: {slowest[1]['slowest_task']['task_id']})"
        )
        opportunities.append(
            f"  → **Action:** Review task complexity, consider prompt simplification"
        )

    # 5. Failure patterns
    if failure_analysis['timeout_count'] > 0:
        opportunities.append(
            f"**Timeouts:** {failure_analysis['timeout_count']} tasks timed out "
            f"({', '.join(failure_analysis['timeout_tasks'][:3])})"
        )
        opportunities.append(
            f"  → **Action:** Increase timeout or split complex tasks"
        )

    # 6. Check failures
    if failure_analysis['check_failures'] > 0:
        opportunities.append(
            f"**Check Failures:** {failure_analysis['check_failures']} tasks failed validation"
        )
        opportunities.append(
            f"  → **Action:** Review AutoChecks weights, add examples"
        )

    return opportunities


def generate_quality_targets(quality_analysis: Dict) -> Dict[str, float]:
    """Set concrete quality improvement targets per agent."""
    targets = {}

    for agent, stats in quality_analysis['agent_stats'].items():
        current = stats['mean']
        # Target: 4.5/10 or +30% improvement, whichever is lower
        improvement_30pct = current * 1.3
        target = min(4.5, improvement_30pct)
        targets[agent] = {
            'current': current,
            'target': target,
            'delta': target - current,
            'improvement_pct': ((target - current) / current * 100) if current > 0 else 0
        }

    return targets


def main():
    baseline_path = Path("metrics/week2_baseline.jsonl")

    print("="*70)
    print("QUALITY & OPTIMIZATION ANALYSIS")
    print("Week 2 Baseline (100 tasks)")
    print("="*70)

    # Load data
    records = load_baseline(baseline_path)
    print(f"\nLoaded {len(records)} records")

    # Run analyses
    print("\n[1/5] Analyzing quality distribution...")
    quality_analysis = analyze_quality_distribution(records)

    print("[2/5] Analyzing failures...")
    failure_analysis = analyze_failures(records)

    print("[3/5] Analyzing latency...")
    latency_analysis = analyze_latency(records)

    print("[4/5] Analyzing specificity...")
    specificity_analysis = analyze_specificity(records)

    print("[5/5] Extracting high-quality patterns...")
    hq_patterns = extract_high_quality_patterns(
        quality_analysis['high_quality_tasks']
    )

    # Print results
    print("\n" + "="*70)
    print("QUALITY DISTRIBUTION")
    print("="*70)

    print(f"\nScore Ranges:")
    for range_name, count in quality_analysis['score_ranges'].items():
        pct = count / len(records) * 100
        print(f"  {range_name.upper():10s}: {count:3d} tasks ({pct:5.1f}%)")

    print(f"\nPer-Agent Quality:")
    for agent, stats in sorted(quality_analysis['agent_stats'].items()):
        print(f"  {agent:12s}: {stats['mean']:.1f}/10  "
              f"(median: {stats['median']:.1f}, "
              f"range: {stats['min']:.1f}-{stats['max']:.1f}, "
              f"σ: {stats['stdev']:.2f})")

    print("\n" + "="*70)
    print("PERFORMANCE ISSUES")
    print("="*70)

    print(f"\nFailures:")
    print(f"  Total: {failure_analysis['total_failures']}")
    print(f"  Timeouts: {failure_analysis['timeout_count']}")
    print(f"  Check failures: {failure_analysis['check_failures']}")

    if failure_analysis['timeout_tasks']:
        print(f"  Timeout tasks: {', '.join(failure_analysis['timeout_tasks'][:5])}")

    print(f"\nLatency (P95):")
    for agent, stats in sorted(latency_analysis.items(), key=lambda x: x[1]['p95'], reverse=True):
        print(f"  {agent:12s}: {stats['p95']:6.1f}s  "
              f"(mean: {stats['mean']:.1f}s, max: {stats['max']:.1f}s)")
        if stats['slowest_task']:
            print(f"    → Slowest: {stats['slowest_task']['task_id']} ({stats['slowest_task']['latency']:.1f}s)")

    print("\n" + "="*70)
    print("SPECIFICITY ANALYSIS")
    print("="*70)

    print(f"\nFile:line references:")
    print(f"  Specific: {specificity_analysis['specific_count']} ({specificity_analysis['specific_pct']:.1f}%)")
    print(f"  Non-specific: {specificity_analysis['non_specific_count']}")
    print(f"\nQuality correlation:")
    print(f"  With file:line refs:    {specificity_analysis['specific_avg_quality']:.1f}/10")
    print(f"  Without file:line refs: {specificity_analysis['non_specific_avg_quality']:.1f}/10")
    print(f"  Delta: {specificity_analysis['quality_delta']:+.1f} points")

    print("\n" + "="*70)
    print("HIGH-QUALITY PATTERNS (5+/10)")
    print("="*70)

    print(f"\nCount: {hq_patterns['count']} tasks")
    print(f"Avg output length: {hq_patterns['avg_length']:.0f} chars")
    print(f"Specificity rate: {hq_patterns['specific_pct']:.1f}%")
    print(f"By agent:")
    for agent, count in sorted(hq_patterns['agents'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {agent:12s}: {count} tasks")

    print("\n" + "="*70)
    print("OPTIMIZATION OPPORTUNITIES")
    print("="*70)

    opportunities = identify_optimization_opportunities(
        quality_analysis, failure_analysis, latency_analysis, specificity_analysis
    )

    for i, opp in enumerate(opportunities, 1):
        print(f"\n{i}. {opp}")

    print("\n" + "="*70)
    print("QUALITY IMPROVEMENT TARGETS")
    print("="*70)

    targets = generate_quality_targets(quality_analysis)

    print(f"\n{'Agent':<12s} {'Current':<10s} {'Target':<10s} {'Delta':<10s} {'Improve'}")
    print("-" * 70)
    for agent, data in sorted(targets.items(), key=lambda x: x[1]['delta'], reverse=True):
        print(f"{agent:<12s} {data['current']:>5.1f}/10   {data['target']:>5.1f}/10   "
              f"{data['delta']:>+4.1f}     {data['improvement_pct']:>5.1f}%")

    overall_current = statistics.mean([d['current'] for d in targets.values()])
    overall_target = statistics.mean([d['target'] for d in targets.values()])

    print("-" * 70)
    print(f"{'OVERALL':<12s} {overall_current:>5.1f}/10   {overall_target:>5.1f}/10   "
          f"{overall_target - overall_current:>+4.1f}     "
          f"{((overall_target - overall_current) / overall_current * 100):>5.1f}%")

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)

    # Save detailed report
    report_path = Path("docs/WEEK2_QUALITY_OPTIMIZATION_ANALYSIS.md")
    with open(report_path, 'w') as f:
        f.write("# Week 2 Quality & Optimization Analysis\n\n")
        f.write(f"**Date:** 2025-10-16\n")
        f.write(f"**Dataset:** {len(records)} tasks across 5 agents\n\n")

        f.write("## Quality Distribution\n\n")
        f.write(f"- **High (5+/10):** {quality_analysis['score_ranges'].get('high', 0)} tasks\n")
        f.write(f"- **Medium (3-5/10):** {quality_analysis['score_ranges'].get('medium', 0)} tasks\n")
        f.write(f"- **Low (<3/10):** {quality_analysis['score_ranges'].get('low', 0)} tasks\n\n")

        f.write("## Optimization Opportunities\n\n")
        for i, opp in enumerate(opportunities, 1):
            f.write(f"{i}. {opp}\n")

        f.write("\n## Quality Targets\n\n")
        f.write("| Agent | Current | Target | Delta | Improvement |\n")
        f.write("|-------|---------|--------|-------|-------------|\n")
        for agent, data in sorted(targets.items()):
            f.write(f"| {agent} | {data['current']:.1f}/10 | {data['target']:.1f}/10 | "
                   f"{data['delta']:+.1f} | {data['improvement_pct']:.1f}% |\n")

        f.write(f"\n**Overall:** {overall_current:.1f}/10 → {overall_target:.1f}/10 "
               f"({overall_target - overall_current:+.1f} points, "
               f"{((overall_target - overall_current) / overall_current * 100):.1f}% improvement)\n")

    print(f"\nDetailed report saved: {report_path}")


if __name__ == "__main__":
    main()
