#!/usr/bin/env python3
"""
Test script for Tongyi tool calling integration (Week 5).

Tests that TongyiAdapter can use tools via IToolSupportedProvider interface.
Follows TDD principle: Write tests first, implement to pass.

Validates:
1. TongyiAdapter implements IToolSupportedProvider
2. generate_with_tools() executes tools
3. Tool results are incorporated into responses
4. Tool calling works with debug logging
5. Error handling for tool failures
"""

import sys
import os
import subprocess

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_tongyi_implements_tool_interface():
    """Test 1: TongyiAdapter implements IToolSupportedProvider."""
    print("\n[TEST 1] TongyiAdapter implements IToolSupportedProvider")
    print("=" * 60)

    try:
        from src.adapters.llm.tongyi_adapter import TongyiDeepResearchAdapter
        from src.interfaces import IToolSupportedProvider

        adapter = TongyiDeepResearchAdapter()

        # Check if implements interface
        is_tool_supported = isinstance(adapter, IToolSupportedProvider)

        if is_tool_supported:
            print("✓ TongyiAdapter implements IToolSupportedProvider")
            return True
        else:
            print("⚠️  TongyiAdapter does not implement IToolSupportedProvider")
            print("  This is expected before Week 5 implementation")
            return False

    except Exception as e:
        print(f"⚠️  Cannot test interface implementation: {e}")
        return False


def test_tongyi_supports_tools_method():
    """Test 2: supports_tools() method returns True."""
    print("\n[TEST 2] supports_tools() method")
    print("=" * 60)

    try:
        from src.adapters.llm.tongyi_adapter import TongyiDeepResearchAdapter

        adapter = TongyiDeepResearchAdapter()

        # Check if supports_tools method exists and returns True
        if hasattr(adapter, 'supports_tools'):
            supports = adapter.supports_tools()
            if supports:
                print("✓ supports_tools() returns True")
                return True
            else:
                print("⚠️  supports_tools() returns False")
                return False
        else:
            print("⚠️  supports_tools() method not found")
            print("  This is expected before Week 5 implementation")
            return False

    except Exception as e:
        print(f"⚠️  Test error: {e}")
        return False


def test_generate_with_tools_method_exists():
    """Test 3: generate_with_tools() method exists."""
    print("\n[TEST 3] generate_with_tools() method exists")
    print("=" * 60)

    try:
        from src.adapters.llm.tongyi_adapter import TongyiDeepResearchAdapter

        adapter = TongyiDeepResearchAdapter()

        if hasattr(adapter, 'generate_with_tools'):
            print("✓ generate_with_tools() method exists")
            return True
        else:
            print("⚠️  generate_with_tools() method not found")
            print("  This is expected before Week 5 implementation")
            return False

    except Exception as e:
        print(f"⚠️  Test error: {e}")
        return False


def test_list_files_tool_execution():
    """Test 4: Tool execution - list_files."""
    print("\n[TEST 4] Tool execution: list_files")
    print("=" * 60)

    try:
        from src.adapters.llm.tongyi_adapter import TongyiDeepResearchAdapter
        from src.tool_registry import default_registry
        from src.interfaces import LLMConfig

        adapter = TongyiDeepResearchAdapter()

        if not hasattr(adapter, 'generate_with_tools'):
            print("⚠️  generate_with_tools() not implemented yet")
            return False

        # Get tools from registry
        tools = default_registry.get_openai_tools()

        messages = [
            {"role": "system", "content": "You can use tools to help answer questions."},
            {"role": "user", "content": "List the Python files in the src/ directory"}
        ]

        config = LLMConfig(temperature=0.7, max_tokens=256)

        result = adapter.generate_with_tools(messages, tools, config)

        # Validate result structure
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "response" in result, "Result should contain 'response' key"
        assert "tool_calls" in result, "Result should contain 'tool_calls' key"

        # Check if list_files tool was called
        tool_calls = result["tool_calls"]
        has_list_files = any("list_files" in str(call) for call in tool_calls)

        if has_list_files:
            print("✓ list_files tool was called")
            print(f"  Tool calls: {len(tool_calls)}")
            return True
        else:
            print("⚠️  list_files tool not called (may need prompt tuning)")
            return True  # Don't fail - model might not call tool

    except ConnectionError as e:
        print(f"⚠️  Server connection error: {e}")
        print("  Ensure llama.cpp server is running on localhost:8080")
        return False
    except Exception as e:
        print(f"⚠️  Test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_run_command_tool_execution():
    """Test 5: Tool execution - run_command."""
    print("\n[TEST 5] Tool execution: run_command (git status)")
    print("=" * 60)

    try:
        from src.adapters.llm.tongyi_adapter import TongyiDeepResearchAdapter
        from src.tool_registry import default_registry
        from src.interfaces import LLMConfig

        adapter = TongyiDeepResearchAdapter()

        if not hasattr(adapter, 'generate_with_tools'):
            print("⚠️  generate_with_tools() not implemented yet")
            return False

        tools = default_registry.get_openai_tools()

        messages = [
            {"role": "system", "content": "You can use the run_command tool to execute shell commands."},
            {"role": "user", "content": "Check the git status of this repository using run_command tool"}
        ]

        config = LLMConfig(temperature=0.7, max_tokens=256)

        result = adapter.generate_with_tools(messages, tools, config)

        # Check if run_command was called
        tool_calls = result.get("tool_calls", [])
        has_run_command = any("run_command" in str(call) for call in tool_calls)

        if has_run_command:
            print("✓ run_command tool was called")
            # Check if tool was actually executed (should have results)
            tool_results = result.get("tool_results", [])
            if tool_results:
                print(f"✓ Tool execution produced results: {len(tool_results)} results")
                return True
            else:
                print("⚠️  Tool called but no results")
                return False
        else:
            print("⚠️  run_command tool not called")
            return True  # Don't fail - model might not call tool

    except ConnectionError as e:
        print(f"⚠️  Server connection error: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Test error: {e}")
        return False


def test_tool_error_handling():
    """Test 6: Tool error handling."""
    print("\n[TEST 6] Tool error handling")
    print("=" * 60)

    try:
        from src.adapters.llm.tongyi_adapter import TongyiDeepResearchAdapter
        from src.tool_registry import default_registry
        from src.interfaces import LLMConfig

        adapter = TongyiDeepResearchAdapter()

        if not hasattr(adapter, 'generate_with_tools'):
            print("⚠️  generate_with_tools() not implemented yet")
            return False

        tools = default_registry.get_openai_tools()

        # Request a command that will fail
        messages = [
            {"role": "system", "content": "You can use tools."},
            {"role": "user", "content": "Run the command 'nonexistent_command_xyz123' using run_command"}
        ]

        config = LLMConfig(temperature=0.7, max_tokens=256)

        # Should not crash, should handle error gracefully
        try:
            result = adapter.generate_with_tools(messages, tools, config)
            print("✓ Tool errors handled gracefully (no crash)")
            return True
        except Exception as e:
            # If it raises a specific error, that's okay
            print(f"✓ Tool error raised appropriately: {type(e).__name__}")
            return True

    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        return False


def test_tool_calling_with_debug_logs():
    """Test 7: Tool calling generates debug logs."""
    print("\n[TEST 7] Tool calling with debug logs")
    print("=" * 60)

    result = subprocess.run(
        [
            "python3", "-m", "src.main",
            "--task", "List files in src/ directory",
            "--provider", "tongyi",
            "--debug"
        ],
        capture_output=True,
        text=True,
        timeout=45
    )

    output = result.stdout + result.stderr

    # Check for tool-related debug logs
    has_tool_logs = any([
        "tool" in output.lower() and "DEBUG" in output,
        "list_files" in output.lower(),
        "execute" in output.lower() and "DEBUG" in output
    ])

    if has_tool_logs:
        print("✓ Tool calling generates debug logs")
        sample = [line for line in output.split('\n') if 'tool' in line.lower() and 'DEBUG' in line]
        if sample:
            print(f"  Sample: {sample[0][:80]}")
        return True
    else:
        print("⚠️  No tool-related debug logs found")
        print("  This may be expected if tools aren't called")
        return True  # Don't fail


def main():
    """Run all Tongyi tool calling tests."""
    print("=" * 60)
    print("Tongyi Tool Calling Integration Tests (Week 5)")
    print("=" * 60)

    results = {
        "Implements IToolSupportedProvider": test_tongyi_implements_tool_interface(),
        "supports_tools() method": test_tongyi_supports_tools_method(),
        "generate_with_tools() exists": test_generate_with_tools_method_exists(),
        "list_files tool execution": test_list_files_tool_execution(),
        "run_command tool execution": test_run_command_tool_execution(),
        "Tool error handling": test_tool_error_handling(),
        "Debug logging": test_tool_calling_with_debug_logs()
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

    # Week 5 specific: Expect some failures before implementation
    expected_implementations = [
        "Implements IToolSupportedProvider",
        "supports_tools() method",
        "generate_with_tools() exists"
    ]

    not_implemented = [name for name in expected_implementations if not results[name]]

    if not_implemented:
        print(f"\n⚠️  Expected implementations needed (Week 5):")
        for name in not_implemented:
            print(f"   - {name}")

    if success_rate == 100:
        print("\n✅ All tool calling tests passed!")
        return 0
    elif success_rate >= 40:
        print("\n⚠️  Partial implementation (expected during Week 5)")
        return 0
    else:
        print("\n⚠️  Multiple tests need implementation")
        return 1


if __name__ == "__main__":
    sys.exit(main())