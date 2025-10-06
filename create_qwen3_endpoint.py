#!/usr/bin/env python3
"""
Create Qwen3-8B Inference Endpoint using HuggingFace API.

This script creates a dedicated Inference Endpoint for Qwen3-8B with:
- Scale-to-zero (min_replica=0) to save costs
- L4 GPU instance (~$1/hour when active)
- Private endpoint (billed to Jake-DevOps-KTP organization)
"""

import os
from dotenv import load_dotenv
from pathlib import Path

env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

from huggingface_hub import HfApi, InferenceEndpoint

def create_endpoint():
    """Create Qwen3-8B Inference Endpoint."""

    token = os.getenv("HF_TOKEN")
    api = HfApi(token=token)

    print("Creating Qwen3-8B Inference Endpoint...")
    print("="*60)

    # Endpoint configuration
    config = {
        "name": "qwen3-8b-production",
        "namespace": "Jake-DevOps-KTP",  # Organization for billing
        "repository": "Qwen/Qwen3-8B",
        "framework": "pytorch",
        "task": "text-generation",
        "accelerator": "gpu",
        "instance_type": "nvidia-l4",  # L4 GPU (~$1/hour)
        "instance_size": "x1",
        "region": "us-east-1",
        "vendor": "aws",
        "min_replica": 0,  # Scale-to-zero (save costs)
        "max_replica": 1,
        "type": "private",  # Use org billing
        "revision": "main"
    }

    print(f"\nConfiguration:")
    for key, value in config.items():
        print(f"  {key}: {value}")

    try:
        print("\n" + "-"*60)
        print("Creating endpoint (this may take a few minutes)...")
        print("-"*60)

        endpoint = api.create_inference_endpoint(
            name=config["name"],
            namespace=config["namespace"],
            repository=config["repository"],
            framework=config["framework"],
            task=config["task"],
            accelerator=config["accelerator"],
            instance_type=config["instance_type"],
            instance_size=config["instance_size"],
            region=config["region"],
            vendor=config["vendor"],
            min_replica=config["min_replica"],
            max_replica=config["max_replica"],
            type=config["type"],
            revision=config["revision"]
        )

        print("\n✅ Endpoint created successfully!")
        print("="*60)
        print(f"Name: {endpoint.name}")
        print(f"Status: {endpoint.status}")
        print(f"URL: {endpoint.url}")
        print(f"Namespace: {endpoint.namespace}")
        print(f"Repository: {endpoint.repository}")
        print("="*60)

        print("\n📊 Cost Estimate:")
        print(f"  Idle (scale-to-zero): $0/hour")
        print(f"  Active (L4 GPU): ~$1/hour")
        print(f"  Budget: $100/month = 100 hours/month available")

        print("\n⏳ Deployment Status:")
        print("  The endpoint is now deploying. It will take 2-5 minutes.")
        print("  Check status: python3 check_endpoint_status.py")

        print("\n🔗 Integration:")
        print(f"  Endpoint URL: {endpoint.url}")
        print(f"  Use in code: InferenceClient(model='{endpoint.url}', token=HF_TOKEN)")

        return endpoint

    except Exception as e:
        print(f"\n❌ Error creating endpoint: {e}")
        print("\nTroubleshooting:")
        print("  1. Check payment method is added to Jake-DevOps-KTP")
        print("  2. Verify Teams subscription is active")
        print("  3. Try different instance type (nvidia-a10g, nvidia-t4)")
        print("  4. Check Web UI: https://ui.endpoints.huggingface.co/")
        raise

if __name__ == "__main__":
    create_endpoint()
