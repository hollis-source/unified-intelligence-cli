#!/usr/bin/env python3
"""Test HuggingFace Inference Endpoints API directly."""

import os
from dotenv import load_dotenv
from pathlib import Path

env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

from huggingface_hub import HfApi

def list_endpoints():
    """List inference endpoints using HF API."""

    token = os.getenv("HF_TOKEN")
    api = HfApi(token=token)

    print("Attempting to list Inference Endpoints...")
    print(f"Token: {token[:20]}...")

    try:
        # Try to list endpoints for personal account
        print("\n1. Listing personal endpoints:")
        endpoints = api.list_inference_endpoints(namespace="hollis-source")
        print(f"Found {len(endpoints)} endpoints")
        for ep in endpoints:
            print(f"  - {ep.name}: {ep.status}")
    except Exception as e:
        print(f"Error listing personal endpoints: {e}")

    try:
        # Try to list endpoints for organization
        print("\n2. Listing organization endpoints:")
        endpoints = api.list_inference_endpoints(namespace="Jake-DevOps-KTP")
        print(f"Found {len(endpoints)} endpoints")
        for ep in endpoints:
            print(f"  - {ep.name}: {ep.status}")
    except Exception as e:
        print(f"Error listing organization endpoints: {e}")

if __name__ == "__main__":
    list_endpoints()
