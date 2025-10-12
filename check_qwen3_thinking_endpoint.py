#!/usr/bin/env python3
"""
Check Qwen3-Next-80B-Thinking endpoint status and test with simple query.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

from huggingface_hub import HfApi

def check_endpoint_status():
    """Check if endpoint is ready."""

    token = os.getenv("HF_TOKEN")
    api = HfApi(token=token)

    endpoint_url = "https://crlqq5n5zwaz4rnh.us-east-2.aws.endpoints.huggingface.cloud"

    print("Checking Qwen3-Next-80B-Thinking Endpoint Status")
    print("="*70)
    print(f"URL: {endpoint_url}")

    try:
        # List endpoints to find ours
        endpoints = api.list_inference_endpoints(namespace="hollis-source")

        for ep in endpoints:
            if "qwen3-next" in ep.name.lower() or "thinking" in ep.name.lower():
                print(f"\n✅ Found endpoint: {ep.name}")
                print(f"   Status: {ep.status}")
                print(f"   URL: {ep.url}")
                print(f"   Namespace: {ep.namespace}")
                print(f"   Repository: {ep.repository}")

                if ep.status == "running":
                    print("\n✅ Endpoint is READY for inference!")
                    return True
                elif ep.status == "initializing":
                    print("\n⏳ Endpoint is still INITIALIZING...")
                    print("   This usually takes 3-5 minutes.")
                    print("   Wait a bit longer, then try again.")
                    return False
                elif ep.status == "scaled_to_zero":
                    print("\n✅ Endpoint is SCALED TO ZERO (ready but idle)")
                    print("   First request will take 2-3 minutes to wake up.")
                    return True
                else:
                    print(f"\n⚠️ Status: {ep.status}")
                    return False

        print("\n❌ Endpoint not found in list")
        print("   It may still be initializing. Check Web UI:")
        print("   https://ui.endpoints.huggingface.co/hollis-source/endpoints")

    except Exception as e:
        print(f"\n❌ Error checking endpoint: {e}")

    return False

if __name__ == "__main__":
    check_endpoint_status()
