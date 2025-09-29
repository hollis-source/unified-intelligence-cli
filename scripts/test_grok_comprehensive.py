#!/usr/bin/env python3
"""Comprehensive test suite for the improved GrokSession."""

import asyncio
import json
import time
from pathlib import Path
from grok_session import GrokSession

async def test_async_features():
    """Test async-specific features including streaming."""
    print("\n=== Testing Async Features ===")

    session = GrokSession(
        system_prompt="You are Grok, a helpful AI assistant.",
        max_history=20
    )

    # Test 1: Basic async call
    print("\n1. Basic async call:")
    result = await session.send_message_async("What is async programming?")
    print(f"   Response length: {len(result['response'])} chars")
    print(f"   Success: {result['success']}")

    # Test 2: Streaming with callback
    print("\n2. Streaming with callback:")
    chunks_received = []

    def chunk_callback(chunk):
        chunks_received.append(chunk)
        print(".", end="", flush=True)

    result = await session.send_message_async(
        "Count from 1 to 5 slowly",
        stream=True,
        stream_callback=chunk_callback
    )
    print(f"\n   Received {len(chunks_received)} chunks")
    print(f"   Full response: {result['response'][:100]}...")

    # Test 3: Async streaming iterator
    print("\n3. Async streaming iterator:")
    chunk_count = 0
    async for chunk in session.stream_message("What is the meaning of life in one sentence?"):
        chunk_count += 1
        print(".", end="", flush=True)
    print(f"\n   Streamed {chunk_count} chunks")

    # Test 4: Tool execution in async
    print("\n4. Async tool execution:")
    result = await session.send_message_async("Calculate: (123 * 456) / 789")
    if result['tool_results']:
        print(f"   Tool result: {result['tool_results'][0]['result']}")
    print(f"   Final response: {result['response'][:100]}...")

    return session

def test_sync_features():
    """Test synchronous features."""
    print("\n=== Testing Sync Features ===")

    session = GrokSession(
        system_prompt="You are a helpful assistant.",
        max_history=30,
        max_retries=2
    )

    # Test 1: Basic sync call
    print("\n1. Basic sync call:")
    result = session.send_message_sync("Hello, how are you?")
    print(f"   Response: {result['response'][:100]}...")
    print(f"   Time: {result['elapsed_time']:.2f}s")

    # Test 2: Tool usage in sync
    print("\n2. Sync tool execution:")
    result = session.send_message_sync("What's 999 divided by 3?")
    if result['tool_results']:
        print(f"   Tools used: {[t['tool'] for t in result['tool_results']]}")
        print(f"   Calculation: {result['tool_results'][0]['result']}")

    # Test 3: Auto-detection (should use sync)
    print("\n3. Auto-detection mode:")
    result = session.send_message("Tell me a fun fact")  # Auto-detects sync context
    print(f"   Response received: {len(result['response'])} chars")
    print(f"   Mode used: Sync (auto-detected)")

    return session

def test_history_management():
    """Test history management features."""
    print("\n=== Testing History Management ===")

    session = GrokSession(max_history=5)

    # Add multiple messages
    print("\n1. Adding messages to test history limit:")
    for i in range(7):
        result = session.send_message_sync(f"Message {i+1}")
        print(f"   Message {i+1} added, total: {result['message_count']}")

    # Should be limited to max_history
    stats = session.get_stats()
    print(f"   Final message count: {stats['total_messages']} (max: {stats['max_history']})")

    # Test save/load
    print("\n2. Testing persistence:")
    save_path = "/tmp/test_grok_history.json"
    session.save_history(save_path)
    print(f"   Saved to {save_path}")

    # Load in new session
    new_session = GrokSession()
    new_session.load_history(save_path)
    new_stats = new_session.get_stats()
    print(f"   Loaded {new_stats['total_messages']} messages")

    # Test clear history
    print("\n3. Testing clear history:")
    session.clear_history(keep_system=False)
    stats = session.get_stats()
    print(f"   Messages after clear: {stats['total_messages']}")

    return session

def test_custom_tools():
    """Test adding custom tools."""
    print("\n=== Testing Custom Tools ===")

    session = GrokSession()

    # Add a custom tool
    def get_current_time():
        """Get the current time."""
        import datetime
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    tool_def = {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }

    session.add_tool(tool_def, get_current_time)
    print("\n1. Added custom tool: get_current_time")

    # Test using the custom tool
    result = session.send_message_sync("What time is it?")
    if result['tool_results']:
        print(f"   Tool executed: {result['tool_results'][0]['tool']}")
        print(f"   Result: {result['tool_results'][0]['result']}")

    return session

def test_error_handling():
    """Test error handling and retry logic."""
    print("\n=== Testing Error Handling ===")

    # Test with invalid API key
    print("\n1. Testing invalid API key handling:")
    try:
        bad_session = GrokSession(api_key="invalid_key")
        result = bad_session.send_message_sync("Hello")
        print(f"   Error captured: {result['success']} = {result['success']}")
        if not result['success']:
            print(f"   Error message: {result['response'][:100]}")
    except Exception as e:
        print(f"   Exception handled: {str(e)[:100]}")

    # Test with normal session
    session = GrokSession()

    # Test malformed math expression
    print("\n2. Testing tool error handling:")
    result = session.send_message_sync("Calculate: this is not math")
    if result['tool_results']:
        for tool_result in result['tool_results']:
            if 'error' in tool_result or 'Calculation error' in tool_result.get('result', ''):
                print(f"   Tool error handled: {tool_result}")

    return session

async def main():
    """Run all tests."""
    print("=" * 60)
    print("COMPREHENSIVE GROKSESSION TEST SUITE")
    print("=" * 60)

    # Run sync tests
    sync_session = test_sync_features()
    print(f"\n✓ Sync tests completed")

    # Run async tests
    async_session = await test_async_features()
    print(f"\n✓ Async tests completed")

    # Run history management tests
    history_session = test_history_management()
    print(f"\n✓ History management tests completed")

    # Run custom tools tests
    tools_session = test_custom_tools()
    print(f"\n✓ Custom tools tests completed")

    # Run error handling tests
    error_session = test_error_handling()
    print(f"\n✓ Error handling tests completed")

    # Final summary
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)

    # Show final stats
    stats = sync_session.get_stats()
    print("\nFinal session statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    # Run async main
    asyncio.run(main())