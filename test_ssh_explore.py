#!/usr/bin/env python3
"""Explore dad's codebase via SSH to find files for testing."""

import asyncio
from src.adapters.mcp.paramiko_ssh_adapter import create_paramiko_ssh_adapter


async def main():
    print("Connecting to syd2...")
    adapter = create_paramiko_ssh_adapter(default_host="syd2.jacobhollis.com")
    await adapter.connect()
    print("✓ Connected\n")

    # List src directory
    print("Listing /opt/grokmonster/cna-dad-release-v1.0/src...")
    src_listing = await adapter.list_directory(
        "syd2.jacobhollis.com",
        "/opt/grokmonster/cna-dad-release-v1.0/src"
    )
    print(src_listing)
    print()

    # List services directory
    print("Listing /opt/grokmonster/cna-dad-release-v1.0/src/services...")
    services_listing = await adapter.list_directory(
        "syd2.jacobhollis.com",
        "/opt/grokmonster/cna-dad-release-v1.0/src/services"
    )
    print(services_listing)
    print()

    # Try to read db_status.py
    print("Reading db_status.py...")
    try:
        content = await adapter.read_file(
            "syd2.jacobhollis.com",
            "/opt/grokmonster/cna-dad-release-v1.0/src/services/db_status.py"
        )
        print(f"✓ Read {len(content)} bytes")
        print(f"First 500 chars:\n{content[:500]}")
    except Exception as e:
        print(f"✗ Error: {e}")

    await adapter.disconnect()
    print("\n✓ Disconnected")


if __name__ == "__main__":
    asyncio.run(main())
