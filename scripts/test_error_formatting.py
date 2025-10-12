#!/usr/bin/env python3
"""
Test script for Rich error formatting (Week 2).

Tests the enhanced ResultFormatter with error_details display.
Follows TDD principle: Validate formatter with real error structures.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.entities import ExecutionResult, ExecutionStatus
from src.adapters.cli import ResultFormatter


def test_validation_error():
    """Test 1: Display validation error with suggestion."""
    print("\n[TEST 1] Validation Error with Suggestion")
    print("=" * 60)

    result = ExecutionResult(
        status=ExecutionStatus.FAILURE,
        output=None,
        errors=["Task description cannot be empty"],
        error_details={
            "error_type": "ValidationError",
            "component": "TaskValidator",
            "input": {"description": "", "priority": 1},
            "root_cause": "Field 'description' failed validation",
            "user_message": "Task description cannot be empty",
            "suggestion": "Provide a clear task description (e.g., 'Write a Python function to sort a list')",
            "context": {"field": "description"}
        }
    )

    formatter = ResultFormatter(verbose=False)
    formatter.format_results([result])
    print("\n✓ Validation error displayed\n")


def test_tool_error():
    """Test 2: Display tool timeout error."""
    print("\n[TEST 2] Tool Execution Timeout Error")
    print("=" * 60)

    result = ExecutionResult(
        status=ExecutionStatus.FAILURE,
        output=None,
        errors=["Command timed out"],
        error_details={
            "error_type": "ToolError",
            "component": "run_command",
            "input": {"command": "sleep 1000", "timeout": 60},
            "root_cause": "Command execution exceeded 60s timeout",
            "user_message": "Command timed out after 60 seconds",
            "suggestion": "Try breaking it into smaller steps or increase timeout",
            "context": {
                "command": "sleep 1000",
                "timeout_seconds": 60,
                "tool": "run_command"
            }
        }
    )

    formatter = ResultFormatter(verbose=False)
    formatter.format_results([result])
    print("\n✓ Tool error displayed\n")


def test_verbose_mode():
    """Test 3: Display error with verbose details."""
    print("\n[TEST 3] Verbose Mode (shows root cause + context)")
    print("=" * 60)

    result = ExecutionResult(
        status=ExecutionStatus.FAILURE,
        output=None,
        errors=["Provider error"],
        error_details={
            "error_type": "ProviderError",
            "component": "TongyiAdapter",
            "input": {"prompt": "Test prompt", "max_tokens": 100},
            "root_cause": "HTTP request failed: Connection refused",
            "user_message": "Cannot connect to llama.cpp server at http://localhost:8080",
            "suggestion": "Ensure llama.cpp server is running (docker ps)",
            "context": {
                "server_url": "http://localhost:8080",
                "error_code": "ConnectionRefusedError",
                "retry_count": 0
            }
        }
    )

    formatter = ResultFormatter(verbose=True)  # Enable verbose
    formatter.format_results([result])
    print("\n✓ Verbose error displayed with root cause\n")


def test_simple_error_fallback():
    """Test 4: Fallback to simple error display."""
    print("\n[TEST 4] Simple Error (no error_details)")
    print("=" * 60)

    result = ExecutionResult(
        status=ExecutionStatus.FAILURE,
        output=None,
        errors=["Unknown error occurred"],
        error_details=None  # No structured error
    )

    formatter = ResultFormatter(verbose=False)
    formatter.format_results([result])
    print("\n✓ Simple error displayed\n")


def test_success_case():
    """Test 5: Success case (no errors)."""
    print("\n[TEST 5] Success Case (No Errors)")
    print("=" * 60)

    result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        output="Task completed successfully",
        errors=[],
        error_details=None
    )

    formatter = ResultFormatter(verbose=False)
    formatter.format_results([result])
    print("\n✓ Success case displayed\n")


def main():
    """Run all formatting tests."""
    print("=" * 60)
    print("Rich Error Formatting Tests (Week 2)")
    print("=" * 60)

    try:
        test_validation_error()
        test_tool_error()
        test_verbose_mode()
        test_simple_error_fallback()
        test_success_case()

        print("=" * 60)
        print("✅ All formatting tests completed successfully!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())