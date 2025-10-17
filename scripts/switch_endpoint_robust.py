#!/usr/bin/env python3
"""
Robust endpoint switcher: Thinking → Instruct.

Tries multiple strategies:
1. Direct update (no pause/resume)
2. Pause with extended timeout (10 min)
3. Force update if supported
"""

import os
import sys
import time
from huggingface_hub import HfApi

def try_direct_update(api, endpoint_name, namespace):
    """Try updating model without pausing (fastest)."""
    print("\n🔄 Strategy 1: Direct model update (no pause)")
    try:
        endpoint = api.get_inference_endpoint(name=endpoint_name, namespace=namespace)

        print(f"   Current: {endpoint.repository}")
        print(f"   Status: {endpoint.status}")

        if "Instruct" in endpoint.repository:
            print("   ✅ Already using Instruct model!")
            return endpoint, True

        print("   Updating model repository...")
        endpoint = endpoint.update(repository="Qwen/Qwen3-Next-80B-A3B-Instruct")

        print("   Waiting for update to complete (max 10 min)...")
        endpoint = endpoint.wait(timeout=600)

        print(f"   ✅ Updated! New model: {endpoint.repository}")
        return endpoint, True

    except Exception as e:
        print(f"   ⚠️  Direct update failed: {e}")
        return None, False


def try_pause_and_update(api, endpoint_name, namespace):
    """Try pausing, updating, then resuming (more reliable but slower)."""
    print("\n🔄 Strategy 2: Pause → Update → Resume")
    try:
        endpoint = api.get_inference_endpoint(name=endpoint_name, namespace=namespace)

        # Step 1: Pause
        print("   ⏸️  Pausing endpoint...")
        endpoint = endpoint.pause()
        print("   Waiting for pause (max 10 min)...")
        endpoint = endpoint.wait(timeout=600)  # Increased from 300s
        print(f"   Status: {endpoint.status}")

        # Step 2: Update
        print("   🔄 Updating model...")
        endpoint = endpoint.update(repository="Qwen/Qwen3-Next-80B-A3B-Instruct")
        print(f"   New model: {endpoint.repository}")

        # Step 3: Resume
        print("   ▶️  Resuming endpoint...")
        endpoint = endpoint.resume()
        print("   Waiting for ready state (max 10 min)...")
        endpoint = endpoint.wait(timeout=600)

        print(f"   ✅ Complete! Status: {endpoint.status}")
        return endpoint, True

    except Exception as e:
        print(f"   ❌ Pause/update/resume failed: {e}")
        return None, False


def try_polling_approach(api, endpoint_name, namespace):
    """Manual polling with status checks (most robust)."""
    print("\n🔄 Strategy 3: Manual polling approach")
    try:
        endpoint = api.get_inference_endpoint(name=endpoint_name, namespace=namespace)

        # Pause
        print("   ⏸️  Requesting pause...")
        endpoint = endpoint.pause()

        # Poll for paused state
        print("   Polling for paused state...")
        for i in range(60):  # 60 attempts = 10 minutes at 10s intervals
            time.sleep(10)
            endpoint = api.get_inference_endpoint(name=endpoint_name, namespace=namespace)
            print(f"   [{i+1}/60] Status: {endpoint.status}")

            if endpoint.status == "paused":
                print("   ✅ Paused successfully")
                break
            elif endpoint.status in ["failed", "error"]:
                raise Exception(f"Endpoint in error state: {endpoint.status}")
        else:
            raise Exception("Timeout waiting for pause")

        # Update
        print("   🔄 Updating model...")
        endpoint = endpoint.update(repository="Qwen/Qwen3-Next-80B-A3B-Instruct")
        print(f"   Updated to: {endpoint.repository}")

        # Resume
        print("   ▶️  Requesting resume...")
        endpoint = endpoint.resume()

        # Poll for running state
        print("   Polling for running state...")
        for i in range(60):
            time.sleep(10)
            endpoint = api.get_inference_endpoint(name=endpoint_name, namespace=namespace)
            print(f"   [{i+1}/60] Status: {endpoint.status}")

            if endpoint.status == "running":
                print("   ✅ Running successfully")
                break
            elif endpoint.status in ["failed", "error"]:
                raise Exception(f"Endpoint in error state: {endpoint.status}")
        else:
            raise Exception("Timeout waiting for running state")

        return endpoint, True

    except Exception as e:
        print(f"   ❌ Polling approach failed: {e}")
        return None, False


def test_endpoint(endpoint, token):
    """Test the endpoint is working."""
    print("\n🧪 Testing endpoint...")
    try:
        from openai import OpenAI

        client = OpenAI(
            base_url=endpoint.url + "/v1",
            api_key=token
        )

        response = client.chat.completions.create(
            model="Qwen/Qwen3-Next-80B-A3B-Instruct",
            messages=[{"role": "user", "content": "Say: Instruct active!"}],
            max_tokens=20
        )

        result = response.choices[0].message.content
        print(f"   Response: {result}")

        if "Instruct" in result or "active" in result:
            print("   ✅ Endpoint working correctly!")
            return True
        else:
            print("   ⚠️  Unexpected response")
            return False

    except Exception as e:
        print(f"   ⚠️  Test failed: {e}")
        return False


def main():
    print("=" * 80)
    print("ROBUST Endpoint Switcher: Thinking → Instruct")
    print("=" * 80)

    token = os.getenv("HUGGINGFACE_TOKEN")
    if not token:
        print("❌ HUGGINGFACE_TOKEN not set")
        return 1

    api = HfApi(token=token)
    endpoint_name = "qwen3-next-80b-a3b-thinking-rvs"
    namespace = "hollis-source"

    # Try strategies in order
    strategies = [
        ("Direct Update", try_direct_update),
        ("Pause/Update/Resume", try_pause_and_update),
        ("Manual Polling", try_polling_approach)
    ]

    endpoint = None
    for strategy_name, strategy_func in strategies:
        print(f"\n{'='*80}")
        print(f"Attempting: {strategy_name}")
        print('='*80)

        endpoint, success = strategy_func(api, endpoint_name, namespace)

        if success:
            print(f"\n✅ {strategy_name} succeeded!")
            break
    else:
        print("\n❌ All strategies failed")
        print("\nManual intervention required:")
        print("1. Go to: https://ui.endpoints.huggingface.co/hollis-source/endpoints")
        print(f"2. Select: {endpoint_name}")
        print("3. Settings → Model Repository → Qwen/Qwen3-Next-80B-A3B-Instruct")
        print("4. Click 'Update Endpoint'")
        return 1

    # Test the endpoint
    if endpoint:
        test_endpoint(endpoint, token)

    print("\n" + "=" * 80)
    print("✅ SWITCH COMPLETE")
    print("=" * 80)
    print(f"\nEndpoint: {endpoint.url}/v1")
    print(f"Model: {endpoint.repository}")
    print(f"Status: {endpoint.status}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
