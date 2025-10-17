#!/bin/bash
# Stop all llama-server instances

set -e

echo "=== Stopping llama-server instances ==="

# Find and kill all llama-server processes
if pgrep -f "llama-server.*granite" > /dev/null; then
    echo "Stopping servers..."
    pkill -f "llama-server.*granite"
    sleep 2

    # Force kill if still running
    if pgrep -f "llama-server.*granite" > /dev/null; then
        echo "Force killing remaining processes..."
        pkill -9 -f "llama-server.*granite"
    fi

    echo "✓ All servers stopped"
else
    echo "No running llama-server instances found"
fi
