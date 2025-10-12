#!/usr/bin/env python3
"""Test health endpoint with existing services."""
import os
import sys
import time

# Set env vars for health checks
os.environ['SURREALDB_URL'] = 'http://127.0.0.1:8001'
os.environ['REDIS_URL'] = 'redis://127.0.0.1:6379/0'
os.environ['PB_SSH_KEY_PATH'] = f'/home/{os.getenv("USER")}/.ssh/id_ed25519'

from src.observability.health_server import HealthServer

print("Starting health server on port 8000...")
server = HealthServer(host='0.0.0.0', port=8000)
server.start()

# Mark as ready
server.set_ready(True)

print("\nHealth server started!")
print("Testing endpoints...\n")

import urllib.request
import json

time.sleep(1)  # Let server start

# Test health endpoint
try:
    with urllib.request.urlopen('http://localhost:8000/health', timeout=5) as response:
        health_data = json.loads(response.read().decode())
        print(f"✓ /health endpoint: {json.dumps(health_data, indent=2)}")
except Exception as e:
    print(f"✗ /health failed: {e}")

# Test ready endpoint
try:
    with urllib.request.urlopen('http://localhost:8000/ready', timeout=5) as response:
        ready_data = json.loads(response.read().decode())
        print(f"\n✓ /ready endpoint: {json.dumps(ready_data, indent=2)}")
except Exception as e:
    print(f"✗ /ready failed: {e}")

# Test metrics endpoint
try:
    with urllib.request.urlopen('http://localhost:8000/metrics', timeout=5) as response:
        metrics_data = response.read().decode()
        print(f"\n✓ /metrics endpoint (first 500 chars):\n{metrics_data[:500]}")
except Exception as e:
    print(f"✗ /metrics failed: {e}")

print("\n\nHealth server running on http://localhost:8000")
print("Press Ctrl+C to stop...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\nStopping health server...")
    server.stop()
    print("Server stopped")
