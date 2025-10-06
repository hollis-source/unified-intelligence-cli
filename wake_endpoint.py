"""
Wake up the endpoint with a simple request.
Scale-to-zero endpoints automatically resume when receiving a request.
"""

import os
import requests
import time

HF_TOKEN = os.getenv("HF_TOKEN", "hf_YOUR_TOKEN_HERE")
ENDPOINT_URL = "https://crlqq5n5zwaz4rnh.us-east-2.aws.endpoints.huggingface.cloud"

print("="*80)
print("WAKING UP INFERENCE ENDPOINT")
print("="*80)
print()
print(f"Endpoint: {ENDPOINT_URL}")
print("Strategy: Send simple request to trigger auto-scale-up")
print()

headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# Simple test message to wake up the endpoint
test_payload = {
    "messages": [{"role": "user", "content": "Hi"}],
    "max_tokens": 10,
    "temperature": 0.6
}

api_url = f"{ENDPOINT_URL}/v1/chat/completions"

print("Sending wake-up request...")
print("(First request may take 2-5 minutes if endpoint is scaled to zero)")
print()

for attempt in range(1, 6):
    print(f"Attempt {attempt}/5...")

    try:
        # Set a longer timeout for the first request (endpoint might be warming up)
        timeout = 300 if attempt == 1 else 60

        response = requests.post(
            api_url,
            headers=headers,
            json=test_payload,
            timeout=timeout
        )

        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            print("\n✓ SUCCESS! Endpoint is now responding!")
            print()
            result = response.json()
            print(f"  Response: {result.get('choices', [{}])[0].get('message', {}).get('content', 'N/A')}")
            print()
            print("="*80)
            print("ENDPOINT IS READY")
            print("="*80)
            print()
            print("You can now run: python3 execute_blueprint_query.py")
            break

        elif response.status_code == 503:
            print(f"  503 Service Unavailable - Endpoint is warming up...")
            if attempt < 5:
                wait_time = 30
                print(f"  Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print()
                print("✗ Endpoint still not responding after 5 attempts")
                print()
                print("This endpoint may need manual intervention:")
                print("1. Visit: https://ui.endpoints.huggingface.co/")
                print("2. Log in with your HuggingFace account")
                print("3. Find endpoint with ID containing: crlqq5n5zwaz4rnh")
                print("4. Check status and click 'Resume' if paused")
                print("5. Wait 2-5 minutes for warm-up")
                print("6. Retry this script")

        elif response.status_code == 401:
            print(f"  ✗ Authentication failed")
            print(f"  Check that HF_TOKEN is valid: {HF_TOKEN[:10]}...")
            break

        elif response.status_code == 404:
            print(f"  ✗ Endpoint not found")
            print(f"  The endpoint URL might be incorrect or deleted")
            print(f"  Check: https://ui.endpoints.huggingface.co/")
            break

        else:
            print(f"  Unexpected status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            if attempt < 5:
                print(f"  Retrying in 30 seconds...")
                time.sleep(30)

    except requests.exceptions.Timeout:
        print(f"  ⏱️  Request timed out (endpoint might still be warming up)")
        if attempt < 5:
            print(f"  Retrying in 30 seconds...")
            time.sleep(30)
        else:
            print()
            print("✗ Endpoint is taking too long to respond")
            print("  It may need manual restart via HuggingFace UI")

    except Exception as e:
        print(f"  ✗ Error: {e}")
        if attempt < 5:
            print(f"  Retrying in 30 seconds...")
            time.sleep(30)

print()
print("="*80)
