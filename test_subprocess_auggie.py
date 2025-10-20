#!/usr/bin/env python3
"""Test subprocess launching of auggie to debug /root permission issue."""

import subprocess
import os
import sys
from pathlib import Path

print(f"Current user: {os.getenv('USER')}")
print(f"Current HOME: {os.getenv('HOME')}")
print(f"Working directory: {os.getcwd()}")

# Test 1: Basic auggie command
print("\n=== Test 1: Direct auggie call ===")
try:
    result = subprocess.run(
        ["auggie", "echo test", "--quiet"],
        capture_output=True,
        text=True,
        timeout=10
    )
    print(f"✓ Direct call succeeded: {result.stdout.strip()}")
except Exception as e:
    print(f"✗ Direct call failed: {e}")

# Test 2: Popen with start_new_session (mimics LocalWorkerPool)
print("\n=== Test 2: Popen with start_new_session ===")
try:
    env = os.environ.copy()
    env['HOME'] = os.path.expanduser('~')

    log_path = "/tmp/test_auggie.log"
    log_file = open(log_path, 'w')

    process = subprocess.Popen(
        ["auggie", "echo test", "--quiet"],
        cwd=os.getcwd(),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        env=env
    )

    process.wait(timeout=10)
    log_file.close()

    output = Path(log_path).read_text()
    print(f"✓ Popen with start_new_session succeeded")
    print(f"  Output: {output.strip()[:100]}")
    Path(log_path).unlink()
except Exception as e:
    print(f"✗ Popen failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== All tests complete ===")
