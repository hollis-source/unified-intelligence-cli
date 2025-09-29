#!/usr/bin/env python3
"""Consult Grok about optimizing the script."""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("XAI_API_KEY")
client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

# The question with context
messages = [
    {
        "role": "system",
        "content": "You are Grok. Analyze code and provide optimization suggestions for structured outputs and programmatic use."
    },
    {
        "role": "user",
        "content": """I have a Python script that interfaces with you (Grok) via API. I need to optimize it for:
1. Structured outputs (JSON, dictionaries) instead of just strings
2. Programmatic use (can be called from other scripts easily)
3. Iterative use (maintain conversation state across multiple calls)

Current approach uses OpenAI SDK with your API. Key requirements:
- Need to capture both text responses AND tool call results separately
- Want to preserve message history for context
- Should return structured data (not just print to console)
- Must handle streaming responses properly

What's the best architecture for this? Should I:
A) Return a dict with {'response': str, 'tool_calls': list, 'messages': list}?
B) Create a GrokSession class that maintains state?
C) Use async/await for better concurrency?

Please provide a concrete code structure optimized for these needs."""
    }
]

response = client.chat.completions.create(
    model="grok-code-fast-1",
    messages=messages,
    temperature=0.7
)

print("=== Grok's Optimization Recommendations ===\n")
print(response.choices[0].message.content)