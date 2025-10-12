"""
Check and resume HuggingFace Inference Endpoint.
"""

import os
import requests
import time

HF_TOKEN = os.getenv("HF_TOKEN", "hf_YOUR_TOKEN_HERE")
ENDPOINT_URL = "https://crlqq5n5zwaz4rnh.us-east-2.aws.endpoints.huggingface.cloud"

# Extract namespace and endpoint name from URL
# Format: https://{endpoint_name}.{region}.aws.endpoints.huggingface.cloud
endpoint_name = "crlqq5n5zwaz4rnh"

# HuggingFace API base
API_BASE = "https://api.endpoints.huggingface.cloud/v2/endpoint"

print("Checking endpoint status...")
print(f"Endpoint: {endpoint_name}")
print()

# First, try to get endpoint info
headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# Try to get the endpoint namespace (username)
# We need to list all endpoints first
list_url = f"{API_BASE}"
print(f"Fetching endpoint list from: {list_url}")

try:
    response = requests.get(list_url, headers=headers)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        endpoints = response.json()
        print(f"Found {len(endpoints.get('items', []))} endpoints")

        # Find our endpoint
        target_endpoint = None
        for ep in endpoints.get('items', []):
            if endpoint_name in ep.get('name', ''):
                target_endpoint = ep
                break

        if target_endpoint:
            print("\n✓ Endpoint found!")
            print(f"  Name: {target_endpoint.get('name')}")
            print(f"  Status: {target_endpoint.get('status', {}).get('state')}")
            print(f"  URL: {target_endpoint.get('status', {}).get('url')}")

            state = target_endpoint.get('status', {}).get('state')
            namespace = target_endpoint.get('namespace')
            name = target_endpoint.get('name')

            if state in ['scaled_to_zero', 'paused']:
                print(f"\n⚠️  Endpoint is {state}, attempting to resume...")

                # Resume endpoint
                resume_url = f"{API_BASE}/{namespace}/{name}/resume"
                print(f"Resume URL: {resume_url}")

                resume_response = requests.post(resume_url, headers=headers)
                print(f"Resume status: {resume_response.status_code}")

                if resume_response.status_code in [200, 202]:
                    print("✓ Resume request successful!")
                    print("\nWaiting for endpoint to warm up (this can take 2-5 minutes)...")

                    # Wait and check status
                    for i in range(30):  # Check for up to 5 minutes
                        time.sleep(10)
                        check_response = requests.get(f"{API_BASE}/{namespace}/{name}", headers=headers)
                        if check_response.status_code == 200:
                            current_state = check_response.json().get('status', {}).get('state')
                            print(f"  [{i*10}s] Current state: {current_state}")

                            if current_state == 'running':
                                print("\n✓ Endpoint is now running!")
                                print(f"  Ready to accept requests at: {ENDPOINT_URL}")
                                break
                        else:
                            print(f"  [{i*10}s] Checking status...")

                else:
                    print(f"✗ Resume failed: {resume_response.text}")
                    print("\nPlease resume manually at: https://huggingface.co/endpoints")

            elif state == 'running':
                print("\n✓ Endpoint is already running!")
                print("  It should be accepting requests.")
                print("\n  If you're still getting 503 errors, the endpoint might be:")
                print("  - Still warming up (wait 1-2 minutes)")
                print("  - Overloaded (wait and retry)")
                print("  - Having service issues (check HuggingFace status)")

            else:
                print(f"\n⚠️  Endpoint state: {state}")
                print("  This is an unexpected state. Please check the HuggingFace dashboard.")

        else:
            print("\n✗ Endpoint not found in your account")
            print(f"  Searched for: {endpoint_name}")
            print("\n  Available endpoints:")
            for ep in endpoints.get('items', []):
                print(f"    - {ep.get('name')}: {ep.get('status', {}).get('state')}")

    else:
        print(f"✗ Failed to list endpoints: {response.status_code}")
        print(f"  Response: {response.text}")
        print("\n  Please check:")
        print("  1. HF_TOKEN is valid and has access to endpoints")
        print("  2. You have permission to manage this endpoint")
        print("  3. Try manually at: https://huggingface.co/endpoints")

except Exception as e:
    print(f"\n✗ Error: {e}")
    print("\nPlease resume the endpoint manually:")
    print("1. Go to: https://huggingface.co/endpoints")
    print(f"2. Find endpoint: {endpoint_name}")
    print("3. Click 'Resume'")
    print("4. Wait 2-5 minutes for warm-up")
    print("5. Retry the blueprint generation script")
