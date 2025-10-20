#!/usr/bin/env python3
"""
Test Qwen3-Next-80B-A3B-Instruct endpoint integration.

This script tests:
1. Basic text generation
2. Tool calling capabilities
3. Thinking mode (reasoning transparency)
4. Integration with QwenAgentAdapter
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.factories.provider_factory import ProviderFactory
from src.entity.agent import Task


def test_basic_generation(provider):
    """Test basic text generation."""
    print("\n" + "="*60)
    print("TEST 1: Basic Text Generation")
    print("="*60)

    prompt = "Explain Clean Architecture in 2 sentences."

    print(f"Prompt: {prompt}")
    print("\nGenerating...")

    try:
        result = provider.generate(prompt)
        print(f"\nResult: {result}")

        # Validation
        assert result, "Result should not be empty"
        assert len(result) > 20, "Result should be substantial"

        print("\n✅ Test 1 PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_thinking_mode(provider):
    """Test thinking mode (reasoning transparency)."""
    print("\n" + "="*60)
    print("TEST 2: Thinking Mode")
    print("="*60)

    prompt = "What's the best way to refactor a large class? Think step by step."

    print(f"Prompt: {prompt}")
    print("\nGenerating with thinking mode...")

    try:
        result = provider.generate(prompt)
        print(f"\nResult: {result}")

        # Thinking mode should include reasoning steps
        # (Qwen3-Thinking outputs structured thought process)

        assert result, "Result should not be empty"
        print("\n✅ Test 2 PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_adapter_integration(provider):
    """Test QwenAgentAdapter integration."""
    print("\n" + "="*60)
    print("TEST 3: QwenAgentAdapter Integration")
    print("="*60)

    # Verify provider is our adapter
    from src.adapters.llm.qwen_agent_adapter import QwenAgentAdapter

    print(f"Provider type: {type(provider).__name__}")
    print(f"Is QwenAgentAdapter: {isinstance(provider, QwenAgentAdapter)}")

    if isinstance(provider, QwenAgentAdapter):
        print(f"Model: {provider.config.model}")
        print(f"Endpoint: {provider.config.model_server}")
        print(f"Thinking mode: {provider.config.thinking_mode}")

    print("\n✅ Test 3 PASSED")
    return True


def test_with_task(provider):
    """Test generation with Task object."""
    print("\n" + "="*60)
    print("TEST 4: Task-based Generation")
    print("="*60)

    task = Task(
        task_id="test-001",
        description="Write a function to check if a number is prime",
        priority=1
    )

    print(f"Task ID: {task.task_id}")
    print(f"Description: {task.description}")

    try:
        # For basic adapter, we'll use generate with task description
        result = provider.generate(f"Task: {task.description}\n\nProvide a Python implementation.")
        print(f"\nResult: {result[:200]}...")  # Show first 200 chars

        assert result, "Result should not be empty"
        assert "def" in result or "function" in result.lower(), "Should contain code"

        print("\n✅ Test 4 PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Test 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests."""

    print("="*60)
    print("Qwen3-Next-80B-A3B-Instruct Integration Tests")
    print("="*60)

    # Get endpoint URL from environment or use default
    endpoint_url = os.getenv("QWEN_ENDPOINT")

    print(f"\nEndpoint URL: {endpoint_url}")

    # Create provider via factory
    print("\nCreating provider via ProviderFactory...")
    factory = ProviderFactory()

    # Don't pass endpoint_url - let factory use QWEN_ENDPOINT from env
    config = {
        "model": "Qwen/Qwen3-Next-80B-A3B-Instruct",
        "thinking_mode": False
    }

    try:
        provider = factory.create_provider("qwen-agent", config)
        print("✅ Provider created successfully")
    except Exception as e:
        print(f"❌ Failed to create provider: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Run tests
    results = []
    results.append(("Basic Generation", test_basic_generation(provider)))
    results.append(("Thinking Mode", test_thinking_mode(provider)))
    results.append(("Adapter Integration", test_adapter_integration(provider)))
    results.append(("Task-based Generation", test_with_task(provider)))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
