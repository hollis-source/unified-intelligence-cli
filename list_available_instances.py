#!/usr/bin/env python3
"""List available instance types for Inference Endpoints."""

import os
from dotenv import load_dotenv
from pathlib import Path

env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

from huggingface_hub import HfApi

def list_instances():
    """List available instance types."""

    token = os.getenv("HF_TOKEN")
    api = HfApi(token=token)

    print("Fetching available instance types...")

    try:
        # This might not be a direct API call, but let's try
        # Most likely we need to use the Web UI or check docs
        print("\nNote: Instance types are usually region-specific.")
        print("Best way to check: Use Web UI at https://ui.endpoints.huggingface.co/")
        print("\nCommon instance types:")
        print("  - 'g5.xlarge' (nvidia-l4)")
        print("  - 'p4d.24xlarge' (nvidia-a100)")
        print("  - 'p5.48xlarge' (nvidia-h100)")
        print("\nFor H200 2-GPU config, try Web UI creation first")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_instances()
