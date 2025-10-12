#!/usr/bin/env python3
"""
Test script for MetricsAnalyzer
Generates sample metrics and validates all detection algorithms
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from syd2_agent import Metric, MetricsAnalyzer
from datetime import datetime
import random


async def test_metrics_analyzer():
    """Test all analyzer functions with sample data"""

    config = {
        "analysis": {
            "thresholds": {
                "failure_rate": 0.05,  # 5%
                "latency_p95_factor": 1.5,
                "routing_accuracy": 0.90,  # 90%
                "anomaly_z_score": 3.0,
            },
            "trend_window": 10,
            "min_samples": 20,
        },
        "logging": {"level": "INFO"},
    }

    analyzer = MetricsAnalyzer(config)
    await analyzer.initialize()

    print("=" * 60)
    print("MetricsAnalyzer Test Suite")
    print("=" * 60)
    print()

    # Test 1: High failure rate
    print("Test 1: High Failure Rate Detection")
    print("-" * 60)
    metrics_failures = []
    for i in range(50):
        metrics_failures.append(
            Metric(
                task_id=f"task_{i:03d}",
                category="testing",
                success=random.random() > 0.15,  # 15% failure rate
                latency=random.uniform(5, 15),
                timestamp=datetime.now().isoformat(),
                error_type="SSHTimeout" if random.random() < 0.5 else "TaskGenerationError",
            )
        )

    patterns = await analyzer.analyze(metrics_failures)
    if patterns:
        for p in patterns:
            print(f"✓ Detected: {p.type}")
            print(f"  Severity: {p.severity}")
            print(f"  Data: {p.data}")
            print(f"  Recommendation: {p.recommendation[:100]}...")
            print()
    else:
        print("✗ No patterns detected (expected high_failure_rate)")
    print()

    # Test 2: High latency
    print("Test 2: High Latency Detection")
    print("-" * 60)
    metrics_latency = []
    for i in range(50):
        # Most tasks fast, but 20% very slow
        if random.random() < 0.20:
            latency = random.uniform(50, 100)  # Slow
        else:
            latency = random.uniform(5, 15)  # Normal

        metrics_latency.append(
            Metric(
                task_id=f"task_{i:03d}",
                category=random.choice(["testing", "research", "code_review"]),
                success=True,
                latency=latency,
                timestamp=datetime.now().isoformat(),
            )
        )

    patterns = await analyzer.analyze(metrics_latency)
    if patterns:
        for p in patterns:
            print(f"✓ Detected: {p.type}")
            print(f"  Severity: {p.severity}")
            print(f"  Data: {p.data}")
            print(f"  Recommendation: {p.recommendation[:100]}...")
            print()
    else:
        print("✗ No patterns detected (expected high_latency)")
    print()

    # Test 3: Routing errors
    print("Test 3: Routing Errors Detection")
    print("-" * 60)
    metrics_routing = []
    for i in range(50):
        is_correct = random.random() > 0.20  # 20% misrouted
        metrics_routing.append(
            Metric(
                task_id=f"task_{i:03d}",
                category="testing",
                success=True,
                latency=random.uniform(5, 15),
                timestamp=datetime.now().isoformat(),
                routing_info={
                    "is_correct": is_correct,
                    "expected_team": "Testing Team",
                    "actual_team": "Testing Team" if is_correct else random.choice(["Frontend Team", "Backend Team"]),
                },
            )
        )

    patterns = await analyzer.analyze(metrics_routing)
    if patterns:
        for p in patterns:
            print(f"✓ Detected: {p.type}")
            print(f"  Severity: {p.severity}")
            print(f"  Data: {p.data}")
            print(f"  Recommendation: {p.recommendation[:100]}...")
            print()
    else:
        print("✗ No patterns detected (expected routing_errors)")
    print()

    # Test 4: Anomalies
    print("Test 4: Anomaly Detection")
    print("-" * 60)
    metrics_anomalies = []
    for i in range(50):
        # Most normal, a few extreme outliers
        if i % 20 == 0:
            latency = random.uniform(200, 300)  # Extreme outlier
        else:
            latency = random.uniform(10, 12)  # Normal, tight distribution

        metrics_anomalies.append(
            Metric(
                task_id=f"task_{i:03d}",
                category="testing",
                success=True,
                latency=latency,
                timestamp=datetime.now().isoformat(),
            )
        )

    patterns = await analyzer.analyze(metrics_anomalies)
    if patterns:
        for p in patterns:
            print(f"✓ Detected: {p.type}")
            print(f"  Severity: {p.severity}")
            print(f"  Data: {p.data}")
            print(f"  Recommendation: {p.recommendation[:100]}...")
            print()
    else:
        print("✗ No patterns detected (expected anomalies)")
    print()

    # Test 5: Trend detection (increasing)
    print("Test 5: Trend Detection (Increasing)")
    print("-" * 60)
    metrics_trend = []
    for i in range(50):
        # Gradual increase in latency
        base_latency = 10 + (i * 0.5)  # Increases over time
        latency = base_latency + random.uniform(-2, 2)

        metrics_trend.append(
            Metric(
                task_id=f"task_{i:03d}",
                category="testing",
                success=True,
                latency=latency,
                timestamp=datetime.now().isoformat(),
            )
        )

    patterns = await analyzer.analyze(metrics_trend)
    if patterns:
        for p in patterns:
            print(f"✓ Detected: {p.type}")
            print(f"  Severity: {p.severity}")
            print(f"  Data: {p.data}")
            print(f"  Recommendation: {p.recommendation[:100]}...")
            print()
    else:
        print("✗ No patterns detected (expected increasing_latency_trend)")
    print()

    # Test 6: Trend detection (decreasing - positive)
    print("Test 6: Trend Detection (Decreasing)")
    print("-" * 60)
    metrics_trend_down = []
    for i in range(50):
        # Gradual decrease in latency
        base_latency = 30 - (i * 0.5)  # Decreases over time
        latency = max(5, base_latency + random.uniform(-2, 2))  # Floor at 5

        metrics_trend_down.append(
            Metric(
                task_id=f"task_{i:03d}",
                category="testing",
                success=True,
                latency=latency,
                timestamp=datetime.now().isoformat(),
            )
        )

    patterns = await analyzer.analyze(metrics_trend_down)
    if patterns:
        for p in patterns:
            print(f"✓ Detected: {p.type}")
            print(f"  Severity: {p.severity}")
            print(f"  Data: {p.data}")
            print(f"  Recommendation: {p.recommendation[:100]}...")
            print()
    else:
        print("✗ No patterns detected (expected decreasing_latency_trend)")
    print()

    print("=" * 60)
    print("Test Suite Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_metrics_analyzer())
