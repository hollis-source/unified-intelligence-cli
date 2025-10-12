#!/usr/bin/env python3
"""Test script to verify Grok API connection."""

import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

api_key = os.getenv("XAI_API_KEY")
if not api_key:
    raise ValueError("XAI_API_KEY environment variable not set")

print(f"✓ API key loaded (length: {len(api_key)})")

# Initialize client
client = OpenAI(
    api_key=api_key,
    base_url="https://api.x.ai/v1"
)

print("✓ Client initialized with xAI base URL")

# Test with a simple request
try:
    response = client.chat.completions.create(
        model="grok-code-fast-1",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Connection successful!' if you receive this."}
        ],
        max_tokens=50,
        temperature=0.7
    )

    print("✓ API call successful")
    print(f"Response: {response.choices[0].message.content}")

except Exception as e:
    print(f"✗ API call failed: {e}")
    import traceback
    traceback.print_exc()