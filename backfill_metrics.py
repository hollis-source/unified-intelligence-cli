#!/usr/bin/env python3
"""Backfill existing metrics from local JSON to dashboard API."""

import json
import requests
from pathlib import Path

# Dashboard API configuration
DASHBOARD_API_URL = "http://syd2.jacobhollis.com:8080/api/metrics/iteration"
DASHBOARD_API_KEY = "auggie-secret-key"

# Mode/priority mappings
MODE_MAPPING = {
    "fast": "autonomous",
    "thorough": "execution",
    "full": "validation",
}

PRIORITY_MAPPING = {
    "P1": "critical",
    "P2": "high",
    "P3": "medium",
    "P4": "low",
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
}

def main():
    # Load existing metrics
    metrics_file = Path.home() / ".atado" / "autonomous_metrics.json"
    if not metrics_file.exists():
        print(f"ERROR: Metrics file not found: {metrics_file}")
        return 1

    data = json.loads(metrics_file.read_text())
    iterations = data.get("iterations", [])

    if not iterations:
        print("No iterations found in metrics file")
        return 0

    print(f"Found {len(iterations)} metrics to backfill")
    print()

    successful = 0
    failed = 0

    for i, metric in enumerate(iterations, 1):
        # Transform payload
        payload = metric.copy()
        payload["mode"] = MODE_MAPPING.get(payload.get("mode"), "autonomous")

        if "task_priority" in payload and payload["task_priority"]:
            payload["task_priority"] = PRIORITY_MAPPING.get(
                payload["task_priority"], "medium"
            )

        print(f"[{i}/{len(iterations)}] Posting iteration {metric.get('iteration_number')}...", end=" ")

        try:
            response = requests.post(
                DASHBOARD_API_URL,
                json=payload,
                headers={"X-API-Key": DASHBOARD_API_KEY},
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()
            print(f"✓ ID={result.get('id')} (duration={metric.get('duration_total', 0):.1f}s)")
            successful += 1
        except requests.exceptions.RequestException as e:
            print(f"✗ FAILED: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"BACKFILL COMPLETE")
    print(f"Successful: {successful}/{len(iterations)}")
    print(f"Failed: {failed}/{len(iterations)}")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
