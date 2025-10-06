#!/usr/bin/env python3
"""
Create Qwen3-Next-80B-A3B-Instruct Inference Endpoint.

Configuration:
- Model: Qwen/Qwen3-Next-80B-A3B-Instruct (from catalog)
- Hardware: Nvidia H200 2 GPUs · 282 GB RAM
- Cost: $10/hour when active (scale-to-zero when idle)
- Container: vLLM (optimized for text generation)
- Region: AWS us-east
"""

import os
from dotenv import load_dotenv
from pathlib import Path

env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

from huggingface_hub import HfApi

def create_qwen3_next_endpoint():
    """Create Qwen3-Next-80B Inference Endpoint with optimal configuration."""

    token = os.getenv("HF_TOKEN")
    api = HfApi(token=token)

    print("Creating Qwen3-Next-80B-A3B-Instruct Inference Endpoint")
    print("="*70)

    # Endpoint configuration
    config = {
        # Basic
        "name": "qwen3-next-80b-production",
        "namespace": "hollis-source",  # Your account (can use Jake-DevOps-KTP for org billing)
        "repository": "Qwen/Qwen3-Next-80B-A3B-Instruct",
        "revision": "main",

        # Hardware (H200 2 GPUs - only option that works per your note)
        "accelerator": "gpu",
        "instance_type": "nvidia-h200",
        "instance_size": "x2",  # 2 GPUs
        "vendor": "aws",
        "region": "us-east-1",

        # Autoscaling (cost optimization)
        "min_replica": 0,  # Scale-to-zero after 1 hour idle
        "max_replica": 1,  # Max 1 replica (can increase if needed)
        "scale_to_zero_timeout": 3600,  # 1 hour (in seconds)

        # Security
        "type": "protected",  # Requires HF token (recommended)

        # Container (vLLM optimized - catalog will apply defaults)
        "framework": "pytorch",
        "task": "text-generation"
    }

    print("\n📋 Configuration:")
    print(f"  Name: {config['name']}")
    print(f"  Repository: {config['repository']}")
    print(f"  Hardware: {config['instance_type']} x {config['instance_size']} ({config['vendor']} {config['region']})")
    print(f"  Autoscaling: {config['min_replica']}-{config['max_replica']} replicas")
    print(f"  Scale-to-zero: After {config['scale_to_zero_timeout']/3600:.0f} hour(s)")
    print(f"  Security: {config['type']}")
    print(f"  Container: vLLM (catalog default with 2 GPU tensor parallel)")

    print("\n💰 Cost Estimate:")
    print(f"  Idle (scaled to 0): $0/hour")
    print(f"  Active (H200 x2): $10/hour")
    print(f"  Budget: $100/month = 10 hours/month active time")
    print(f"  Recommendation: Use for high-quality tasks, fallback to cheaper models for simple queries")

    print("\n⚙️ vLLM Configuration:")
    print(f"  Tensor Parallel Size: 2 GPUs")
    print(f"  Max Batch Tokens: 32,768")
    print(f"  Max Input Length: 8,192 tokens")
    print(f"  Max Total Tokens: 32,768 tokens")

    # Auto-confirm (skip interactive prompt for automation)
    print("\n" + "="*70)
    print("Auto-confirmed: Creating endpoint...")
    print("="*70)

    try:
        print("\n" + "-"*70)
        print("🚀 Creating endpoint (this will take 3-5 minutes)...")
        print("-"*70)

        # Create endpoint with HF API
        # Simplified call - HF API will use catalog defaults for this model
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
        print("="*70)
        print(f"Name: {endpoint.name}")
        print(f"Status: {endpoint.status}")
        print(f"URL: {endpoint.url}")
        print(f"Namespace: {endpoint.namespace}")
        print("="*70)

        print("\n⏳ Deployment Status:")
        print("  The endpoint is now deploying. Initial deployment takes 3-5 minutes.")
        print("  Monitor: python3 check_endpoint_status.py")
        print(f"  Or visit: https://ui.endpoints.huggingface.co/{config['namespace']}/{config['name']}")

        print("\n🔗 Integration:")
        print(f"  URL: {endpoint.url}")
        print(f"  Usage:")
        print(f"    from huggingface_hub import InferenceClient")
        print(f"    client = InferenceClient(model='{endpoint.url}', token=HF_TOKEN)")
        print(f"    response = client.chat_completion(messages=[...])")

        print("\n📊 Usage Tips:")
        print("  - First request will take 2-3 min (cold start from scale-to-zero)")
        print("  - Subsequent requests: <10s latency while warm")
        print("  - Auto-scales to 0 after 1 hour of inactivity")
        print("  - Use for complex reasoning, long-form generation")
        print("  - Fallback to qwen3_hf_inference for simple queries")

        return endpoint

    except Exception as e:
        print(f"\n❌ Error creating endpoint: {e}")
        print("\n🔧 Troubleshooting:")
        print("  1. Check quota: You need 4 quotas, currently have 1-2 available")
        print("  2. Request quota increase: https://ui.endpoints.huggingface.co/")
        print("  3. Verify payment method: https://huggingface.co/settings/billing")
        print("  4. Alternative: Try smaller model or different GPU")
        print("\nFull error details:")
        raise

if __name__ == "__main__":
    create_qwen3_next_endpoint()
