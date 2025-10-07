#!/bin/sh
# wait-for.sh - Wait for service to be ready before starting application
# Usage: ./wait-for.sh <url> [timeout_seconds]
#
# Exit codes:
#   0 - Service is ready
#   1 - Service failed to become ready within timeout
#
# Production deployment helper for Project Builder
# Ensures SurrealDB is responsive before application starts

set -e

url="${1:-http://surrealdb:8001/health}"
timeout="${2:-60}"
counter=0

echo "[wait-for] Waiting for service at $url (timeout: ${timeout}s)"

while [ $counter -lt "$timeout" ]; do
    if wget -q -O /dev/null --timeout=2 "$url" 2>/dev/null || curl -sf --max-time 2 "$url" >/dev/null 2>&1; then
        echo "[wait-for] ✓ Service is ready at $url"
        exit 0
    fi

    counter=$((counter + 1))
    echo "[wait-for] Waiting... ($counter/${timeout})"
    sleep 1
done

echo "[wait-for] ✗ Service not ready after ${timeout}s - giving up"
exit 1
