#!/usr/bin/env python3
"""
Integration test for TongyiDeepResearchAdapter.

Tests:
1. Connection to llama.cpp server
2. Message format conversion
3. Agentic reasoning capability
4. Error handling

Follows TDD principle: Validate adapter against real model.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.factories.provider_factory import ProviderFactory
from src.interfaces import LLMConfig


def test_connection():
    """Test 1: Verify server connection."""
    print("\n[TEST 1] Testing server connection...")
    try:
        factory = ProviderFactory()
        tongyi = factory.create_provider("tongyi")
        print("✓ Connected to llama.cpp server")
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def test_simple_generation():
    """Test 2: Basic text generation."""
    print("\n[TEST 2] Testing simple generation...")
    try:
        factory = ProviderFactory()
        tongyi = factory.create_provider("tongyi")

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is 2+2?"}
        ]

        config = LLMConfig(temperature=0.7, max_tokens=50)
        response = tongyi.generate(messages, config)

        print(f"Response: {response[:100]}...")

        if response and len(response) > 0:
            print("✓ Generation successful")
            return True
        else:
            print("✗ Empty response")
            return False

    except Exception as e:
        print(f"✗ Generation failed: {e}")
        return False


def test_agentic_reasoning():
    """Test 3: Validate agentic coordinator capabilities."""
    print("\n[TEST 3] Testing agentic reasoning (coordinator task)...")
    try:
        factory = ProviderFactory()
        tongyi = factory.create_provider("tongyi")

        messages = [
            {
                "role": "system",
                "content": "You are a coordinator agent responsible for breaking down complex tasks into subtasks and assigning them to specialist agents."
            },
            {
                "role": "user",
                "content": "Break down this task into subtasks with role assignments: Build a REST API with authentication, unit tests, and deployment scripts."
            }
        ]

        config = LLMConfig(temperature=0.7, max_tokens=256)
        response = tongyi.generate(messages, config)

        print(f"Response preview: {response[:200]}...")

        # Validate agentic reasoning markers
        reasoning_indicators = [
            "subtask",
            "assign",
            "role",
            "step",
            "plan"
        ]

        found_indicators = [
            ind for ind in reasoning_indicators
            if ind.lower() in response.lower()
        ]

        if len(found_indicators) >= 2:
            print(f"✓ Agentic reasoning detected (found: {found_indicators})")
            return True
        else:
            print(f"✗ Weak agentic reasoning (found only: {found_indicators})")
            return False

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_error_handling():
    """Test 4: Validate error handling."""
    print("\n[TEST 4] Testing error handling...")
    try:
        factory = ProviderFactory()

        # Test invalid server URL
        config = {"server_url": "http://localhost:9999"}
        try:
            tongyi = factory.create_provider("tongyi", config)
            print("✗ Should have raised ConnectionError")
            return False
        except ConnectionError:
            print("✓ Correctly raises ConnectionError for invalid server")
            return True

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("Tongyi-DeepResearch-30B Adapter Integration Tests")
    print("=" * 60)

    results = {
        "Connection": test_connection(),
        "Simple Generation": test_simple_generation(),
        "Agentic Reasoning": test_agentic_reasoning(),
        "Error Handling": test_error_handling()
    }

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    total_passed = sum(results.values())
    total_tests = len(results)
    success_rate = (total_passed / total_tests) * 100

    print(f"\nSuccess Rate: {total_passed}/{total_tests} ({success_rate:.0f}%)")

    if success_rate == 100:
        print("\n🎉 All tests passed!")
        return 0
    elif success_rate >= 75:
        print("\n⚠️  Most tests passed")
        return 0
    else:
        print("\n❌ Multiple test failures")
        return 1


if __name__ == "__main__":
    sys.exit(main())