#!/usr/bin/env python3
"""Test the Grok chat with tools functionality."""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI
import requests

# Load environment
load_dotenv()

api_key = os.getenv("XAI_API_KEY")
if not api_key:
    raise ValueError("XAI_API_KEY environment variable not set")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.x.ai/v1"
)

# Tool definitions
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate_math",
            "description": "Evaluate a mathematical expression safely.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "The math expression to evaluate, e.g., '2 + 2 * 3'"}
                },
                "required": ["expression"]
            }
        }
    }
]

def calculate_math(expression):
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {str(e)}"

tool_functions = {"calculate_math": calculate_math}

# Test conversation
messages = [
    {"role": "system", "content": "You are a helpful AI assistant. Use tools when needed."},
    {"role": "user", "content": "What is 15 * 23 + 7?"}
]

print("Testing Grok chat with tools...")
print(f"User: {messages[-1]['content']}")

# Call API
response = client.chat.completions.create(
    model="grok-code-fast-1",
    messages=messages,
    tools=tools,
    tool_choice="auto",
    temperature=0.7,
    max_tokens=256
)

# Process response
assistant_msg = response.choices[0].message
print(f"Assistant: {assistant_msg.content if assistant_msg.content else '(using tool...)'}")

# Handle tool calls
if assistant_msg.tool_calls:
    for tool_call in assistant_msg.tool_calls:
        func_name = tool_call.function.name
        func_args = json.loads(tool_call.function.arguments)
        print(f"  → Calling {func_name}({func_args})")

        if func_name in tool_functions:
            result = tool_functions[func_name](**func_args)
            print(f"  ← Result: {result}")

            # Add tool result to messages
            messages.append({
                "role": "assistant",
                "content": assistant_msg.content,
                "tool_calls": [tool_call.model_dump()]
            })
            messages.append({
                "role": "tool",
                "content": result,
                "tool_call_id": tool_call.id
            })

            # Get final response
            final_response = client.chat.completions.create(
                model="grok-code-fast-1",
                messages=messages,
                temperature=0.7,
                max_tokens=256
            )

            print(f"Assistant (final): {final_response.choices[0].message.content}")

print("\n✓ Grok chat with tools test complete!")