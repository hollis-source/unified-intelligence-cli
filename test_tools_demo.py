#!/usr/bin/env python3
"""
Demo: Dev tools with Grok - Real workflow test.

Tests tool-supported LLM provider with actual dev tools.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.adapters.llm.grok_adapter import GrokAdapter
from src.tools import DEV_TOOLS, TOOL_FUNCTIONS


def test_with_mock():
    """Test with mock provider (no API needed)."""
    from src.adapters.llm.mock_provider import MockToolProvider

    print("=" * 80)
    print("TESTING WITH MOCK PROVIDER")
    print("=" * 80)

    provider = MockToolProvider()

    messages = [
        {"role": "user", "content": "List the files in the current directory"}
    ]

    result = provider.generate_with_tools(
        messages=messages,
        tools=DEV_TOOLS
    )

    print(f"\nResponse: {result['response']}")
    print(f"Tool Calls: {result['tool_calls']}")
    print(f"Tool Results: {result['tool_results']}")
    print("\n✅ Mock provider test passed!")


def test_with_grok():
    """Test with real Grok provider (requires API key)."""
    if not os.getenv("XAI_API_KEY"):
        print("\n⚠️  Skipping Grok test: XAI_API_KEY not set")
        return

    print("\n" + "=" * 80)
    print("TESTING WITH REAL GROK PROVIDER")
    print("=" * 80)

    provider = GrokAdapter(model="grok-code-fast-1")

    messages = [
        {
            "role": "system",
            "content": "You are a helpful dev assistant. Use the provided tools to accomplish tasks, then provide a clear summary of your findings."
        },
        {
            "role": "user",
            "content": "List the Python files in the src/ directory and tell me what you find."
        }
    ]

    print("\nSending request to Grok with dev tools...")
    print("Available tools:")
    for tool in DEV_TOOLS:
        print(f"  - {tool['function']['name']}")

    result = provider.generate_with_tools(
        messages=messages,
        tools=DEV_TOOLS,
        tool_functions=TOOL_FUNCTIONS
    )

    print("\n" + "-" * 80)
    print("GROK RESPONSE:")
    print("-" * 80)
    print(result['response'])

    if result['tool_calls']:
        print("\n" + "-" * 80)
        print(f"TOOL CALLS MADE: {len(result['tool_calls'])}")
        print("-" * 80)
        for i, call in enumerate(result['tool_calls'], 1):
            print(f"{i}. {call}")

    if result['tool_results']:
        print("\n" + "-" * 80)
        print(f"TOOL RESULTS: {len(result['tool_results'])}")
        print("-" * 80)
        for i, res in enumerate(result['tool_results'], 1):
            print(f"{i}. {res}")

    print("\n✅ Grok test complete!")


if __name__ == "__main__":
    # Test mock first
    test_with_mock()

    # Test real Grok if API key available
    test_with_grok()

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)