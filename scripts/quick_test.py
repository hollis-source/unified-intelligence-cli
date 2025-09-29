#!/usr/bin/env python3
"""Quick test of GrokSession functionality."""

from grok_session import GrokSession
import logging

# Reduce logging noise
logging.getLogger("httpx").setLevel(logging.WARNING)

print("=== Quick GrokSession Test ===\n")

# Create session
session = GrokSession(
    system_prompt="You are Grok. Be concise.",
    max_history=10,
    enable_logging=False  # Reduce noise
)

# Test 1: Simple message
print("1. Testing simple message...")
result = session.send_message("Say 'Hello World' and nothing else")
print(f"   Response: {result['response']}")
print(f"   Success: {result['success']}\n")

# Test 2: Math tool
print("2. Testing math tool...")
result = session.send_message("Calculate: 100 / 4")
if result['tool_results']:
    print(f"   Tool used: {result['tool_results'][0]['tool']}")
    print(f"   Result: {result['tool_results'][0]['result']}")
print(f"   Response: {result['response']}\n")

# Test 3: Persistence
print("3. Testing save/load...")
session.save_history("/tmp/quick_test.json")
print("   Saved history")

new_session = GrokSession(enable_logging=False)
new_session.load_history("/tmp/quick_test.json")
stats = new_session.get_stats()
print(f"   Loaded {stats['total_messages']} messages")
print(f"   User messages: {stats['user_messages']}")
print(f"   Assistant messages: {stats['assistant_messages']}\n")

print("✅ Quick test completed successfully!")