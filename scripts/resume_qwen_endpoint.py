#!/usr/bin/env python3
"""
Resume HuggingFace Inference Endpoint for Qwen3-Next-80B-A3B-Instruct.

This script resumes the paused endpoint and validates it's ready for inference.
"""

import os
import sys
import time
from huggingface_hub import HfApi, InferenceEndpoint, list_inference_endpoints
from huggingface_hub.utils import RepositoryNotFoundError

def main():
    """Resume and validate Qwen endpoint."""

    # Check for HF token
    token = os.getenv("HF_TOKEN")
    if not token:
        print("❌ Error: HF_TOKEN environment variable not set")
        sys.exit(1)

    # Initialize API
    api = HfApi(token=token)

    # Find the Qwen endpoint
    print("🔍 Searching for Qwen endpoint...")
    endpoints = list(list_inference_endpoints(token=token))

    qwen_endpoint = None
    for ep in endpoints:
        if "qwen3-next-80b" in ep.name.lower():
            qwen_endpoint = ep
            break

    if not qwen_endpoint:
        print("❌ Error: No Qwen3-Next endpoint found")
        sys.exit(1)

    print(f"✅ Found endpoint: {qwen_endpoint.name}")
    print(f"   Model: {qwen_endpoint.repository}")
    print(f"   Status: {qwen_endpoint.status}")
    print(f"   URL: {qwen_endpoint.url}")

    # Check if already running
    if qwen_endpoint.status in ["running", "initializing"]:
        print(f"✅ Endpoint already {qwen_endpoint.status}")
        return qwen_endpoint.url

    # Resume endpoint
    print("\n🚀 Resuming endpoint...")
    try:
        # Get endpoint object for operations
        endpoint = api.get_inference_endpoint(name=qwen_endpoint.name, token=token)
        endpoint.resume()
        print("✅ Resume request sent")

        # Wait for endpoint to be ready (max 5 minutes)
        print("\n⏳ Waiting for endpoint to initialize...")
        print("   (This typically takes 2-3 minutes for cold start)")

        # Use built-in wait method (timeout in seconds)
        endpoint = endpoint.wait(timeout=300)  # 5 minutes

        if endpoint.status == "running":
            print(f"\n✅ Endpoint is RUNNING!")
            print(f"   URL: {endpoint.url}")
            return endpoint.url
        else:
            print(f"\n❌ Endpoint status: {endpoint.status}")
            sys.exit(1)

    except TimeoutError:
        print(f"\n⚠️  Timeout: Endpoint not ready after 5 minutes")
        print("   You can check status manually on HuggingFace")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error resuming endpoint: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    endpoint_url = main()
    print(f"\n{'='*60}")
    print("DEPLOYMENT COMPLETE")
    print(f"{'='*60}")
    print(f"Endpoint URL: {endpoint_url}")
    print(f"\nNext steps:")
    print(f"1. Update QwenAgentAdapter to use this endpoint")
    print(f"2. Run integration tests")
    print(f"3. Monitor performance and costs")
