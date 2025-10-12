#!/usr/bin/env python3
"""Quick test of ParamikoSSHAdapter"""

import asyncio
import logging
from src.adapters.mcp.paramiko_ssh_adapter import create_paramiko_ssh_adapter

logging.basicConfig(level=logging.INFO)

async def test_adapter():
    print("=" * 60)
    print("Testing ParamikoSSHAdapter")
    print("=" * 60)

    # Create adapter
    adapter = create_paramiko_ssh_adapter(
        default_host="root@syd2.jacobhollis.com"
    )

    try:
        # Connect
        print("\n[1/3] Connecting to syd2...")
        await adapter.connect()
        print("✓ Connected")

        # Read file
        print("\n[2/3] Reading remote file...")
        content = await adapter.read_file(
            None,  # Use default host
            "/opt/grokmonster/cna-dad-release-v1.0/src/services/db_status.py"
        )
        print(f"✓ Read {len(content)} bytes")
        print(f"\nFirst 200 chars:\n{content[:200]}...")

        # Check file exists
        print("\n[3/3] Checking file exists...")
        info = await adapter.file_exists(
            None,
            "/opt/grokmonster/cna-dad-release-v1.0/src/services/db_status.py"
        )
        print(f"✓ File exists: {info.exists}, type: {info.file_type}")

        # Metrics
        print("\nMetrics:")
        metrics = adapter.get_metrics()
        print(f"  Operations: {metrics['metrics']['operations']}")
        print(f"  Successes: {metrics['metrics']['successes']}")
        print(f"  Failures: {metrics['metrics']['failures']}")
        print(f"  Connections: {metrics['metrics']['connections']}")

    finally:
        # Disconnect
        print("\nDisconnecting...")
        await adapter.disconnect()
        print("✓ Disconnected")

    print("\n" + "=" * 60)
    print("Test PASSED ✓")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_adapter())
