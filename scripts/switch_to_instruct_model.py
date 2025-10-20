#!/usr/bin/env python3
"""
Switch HF Inference Endpoint from Thinking to Instruct model.

This script:
1. Pauses the existing endpoint
2. Updates the model repository to Instruct variant
3. Resumes the endpoint with new model
4. Waits for it to be ready
"""

import os
import sys
from huggingface_hub import HfApi

def main():
    print("=" * 80)
    print("Switching Qwen3 Endpoint: Thinking → Instruct")
    print("=" * 80)

    token = os.getenv("HUGGINGFACE_TOKEN")
    if not token:
        print("❌ Error: HUGGINGFACE_TOKEN not set")
        return 1

    api = HfApi(token=token)

    # Get existing endpoint
    print("\n📍 Step 1: Getting existing endpoint...")
    try:
        endpoint = api.get_inference_endpoint(
            name="qwen3-next-80b-a3b-thinking-rvs",
            namespace="hollis-source"
        )
        print(f"   Current model: {endpoint.repository}")
        print(f"   Status: {endpoint.status}")
        print(f"   URL: {endpoint.url}")
    except Exception as e:
        print(f"   ❌ Failed to get endpoint: {e}")
        return 1

    # Check if already Instruct
    if "Instruct" in endpoint.repository:
        print("\n✅ Endpoint already serving Instruct model!")
        return 0

    # Pause endpoint
    print("\n⏸️  Step 2: Pausing endpoint...")
    try:
        endpoint = endpoint.pause()
        endpoint = endpoint.wait(timeout=300)
        print(f"   Status: {endpoint.status}")
    except Exception as e:
        print(f"   ❌ Failed to pause: {e}")
        return 1

    # Update model repository
    print("\n🔄 Step 3: Updating model to Instruct...")
    try:
        endpoint = endpoint.update(
            repository="Qwen/Qwen3-Next-80B-A3B-Instruct"
        )
        print(f"   New model: {endpoint.repository}")
    except Exception as e:
        print(f"   ❌ Failed to update model: {e}")
        return 1

    # Resume endpoint
    print("\n▶️  Step 4: Resuming endpoint...")
    try:
        endpoint = endpoint.resume()
        print(f"   Waiting for endpoint to be ready (may take 2-5 minutes)...")
        endpoint = endpoint.wait(timeout=600)  # 10 minutes max
        print(f"   Status: {endpoint.status}")
        print(f"   ✅ Endpoint ready!")
    except Exception as e:
        print(f"   ❌ Failed to resume: {e}")
        return 1

    # Test the endpoint
    print("\n🧪 Step 5: Testing endpoint...")
    try:
        from openai import OpenAI

        client = OpenAI(
            base_url=endpoint.url + "/v1",
            api_key=token
        )

        response = client.chat.completions.create(
            model="Qwen/Qwen3-Next-80B-A3B-Instruct",
            messages=[
                {"role": "user", "content": "Say 'Instruct model active!' if you can read this."}
            ],
            max_tokens=50
        )

        print(f"   Response: {response.choices[0].message.content}")
        print("   ✅ Endpoint working!")
    except Exception as e:
        print(f"   ⚠️  Test failed: {e}")
        print("   (Endpoint may still be initializing)")

    print("\n" + "=" * 80)
    print("✅ Switch Complete!")
    print("=" * 80)
    print(f"\nEndpoint URL: {endpoint.url}/v1")
    print(f"Model: {endpoint.repository}")
    print("\nNext: Update scripts to remove thinking_mode=True overrides")

    return 0


if __name__ == "__main__":
    sys.exit(main())
