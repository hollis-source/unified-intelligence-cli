#!/usr/bin/env python3
"""Test script to verify dashboard POST integration."""

import json
import requests
from pathlib import Path

# Dashboard API configuration
DASHBOARD_API_URL = "http://syd2.jacobhollis.com:8080/api/metrics/iteration"
DASHBOARD_API_KEY = "auggie-secret-key"

# Load existing metrics
metrics_file = Path.home() / ".ui-cli" / "autonomous_metrics.json"
if not metrics_file.exists():
    print(f"ERROR: Metrics file not found: {metrics_file}")
    exit(1)

data = json.loads(metrics_file.read_text())
iterations = data.get("iterations", [])

if not iterations:
    print("ERROR: No iterations found in metrics file")
    exit(1)

# Test POST with the first iteration
test_metric = iterations[0]
print(f"Testing POST to: {DASHBOARD_API_URL}")
print(f"Test metric (iteration {test_metric.get('iteration_number')}):")
print(json.dumps(test_metric, indent=2))
print()

# Map our modes/priorities to dashboard's expected values
mode_mapping = {
    "fast": "autonomous",
    "thorough": "execution",
    "full": "validation",
}
priority_mapping = {
    "P1": "critical",
    "P2": "high",
    "P3": "medium",
    "P4": "low",
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
}

test_metric_mapped = test_metric.copy()
test_metric_mapped["mode"] = mode_mapping.get(test_metric["mode"], "autonomous")

# Map priority if present
if "task_priority" in test_metric_mapped and test_metric_mapped["task_priority"]:
    test_metric_mapped["task_priority"] = priority_mapping.get(
        test_metric_mapped["task_priority"], "medium"
    )

try:
    response = requests.post(
        DASHBOARD_API_URL,
        json=test_metric_mapped,
        headers={"X-API-Key": DASHBOARD_API_KEY},
        timeout=10,
    )
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    print(f"Response body: {response.text}")

    response.raise_for_status()
    print("\n✅ POST successful!")

except requests.exceptions.RequestException as e:
    print(f"\n❌ POST failed: {e}")
    exit(1)

# Verify by GET
print("\nVerifying with GET request...")
try:
    get_url = "http://syd2.jacobhollis.com:8080/api/metrics/iterations"
    response = requests.get(get_url, timeout=10)
    response.raise_for_status()

    iterations_list = response.json()
    print(f"Total iterations in dashboard: {len(iterations_list)}")

    if iterations_list:
        latest = iterations_list[-1]
        print(f"Latest iteration:")
        print(f"  - Timestamp: {latest.get('timestamp')}")
        print(f"  - Mode: {latest.get('mode')}")
        print(f"  - Success: {latest.get('success')}")
        print(f"  - Duration: {latest.get('duration_total'):.1f}s")

    print("\n✅ Integration test PASSED!")

except requests.exceptions.RequestException as e:
    print(f"\n❌ GET verification failed: {e}")
    exit(1)
