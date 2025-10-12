#!/usr/bin/env python3
"""
Python Integration Examples for Unified Intelligence CLI

Demonstrates how to integrate ui-cli into Python applications.
"""

import os
import json
import subprocess
import sys
from typing import List, Dict, Any
from pathlib import Path


class UICLIWrapper:
    """Wrapper class for UI-CLI integration."""
    
    def __init__(self, api_key: str = None):
        """Initialize with optional API key."""
        self.api_key = api_key or os.getenv('XAI_API_KEY')
        if not self.api_key:
            raise ValueError("XAI_API_KEY not set")
    
    def run_task(self, task: str, output_format: str = 'text') -> Dict[str, Any]:
        """
        Run a single task.
        
        Args:
            task: Task description
            output_format: 'text' or 'json'
        
        Returns:
            Task result as dict
        """
        env = os.environ.copy()
        env['XAI_API_KEY'] = self.api_key
        
        cmd = ['ui-cli']
        if output_format == 'json':
            cmd.extend(['--output', 'json'])
        cmd.append(task)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env
        )
        
        if result.returncode != 0:
            return {
                'success': False,
                'error': result.stderr,
                'output': None
            }
        
        if output_format == 'json':
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError:
                output = result.stdout
        else:
            output = result.stdout
        
        return {
            'success': True,
            'error': None,
            'output': output
        }
    
    def run_tasks(self, tasks: List[str], parallel: bool = False) -> List[Dict[str, Any]]:
        """
        Run multiple tasks.
        
        Args:
            tasks: List of task descriptions
            parallel: Execute in parallel
        
        Returns:
            List of task results
        """
        env = os.environ.copy()
        env['XAI_API_KEY'] = self.api_key
        
        cmd = ['ui-cli', '--output', 'json']
        if parallel:
            cmd.append('--parallel')
        cmd.extend(tasks)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env
        )
        
        if result.returncode != 0:
            return [{'success': False, 'error': result.stderr}]
        
        try:
            output = json.loads(result.stdout)
            return [{'success': True, 'output': output}]
        except json.JSONDecodeError:
            return [{'success': False, 'error': 'Invalid JSON response'}]


def example_1_simple_task():
    """Example 1: Simple single task."""
    print("=" * 70)
    print("Example 1: Simple Single Task")
    print("=" * 70)
    
    cli = UICLIWrapper()
    result = cli.run_task("Explain SOLID principles in 3 sentences")
    
    if result['success']:
        print(result['output'])
    else:
        print(f"Error: {result['error']}")
    print()


def example_2_multiple_tasks():
    """Example 2: Multiple sequential tasks."""
    print("=" * 70)
    print("Example 2: Multiple Sequential Tasks")
    print("=" * 70)
    
    cli = UICLIWrapper()
    tasks = [
        "Define: What is dependency injection?",
        "Benefits: List 3 key benefits",
        "Example: Provide Python code example"
    ]
    
    results = cli.run_tasks(tasks)
    for result in results:
        if result['success']:
            print(result['output'])
        else:
            print(f"Error: {result['error']}")
    print()


def example_3_parallel_tasks():
    """Example 3: Parallel task execution."""
    print("=" * 70)
    print("Example 3: Parallel Task Execution")
    print("=" * 70)
    
    cli = UICLIWrapper()
    tasks = [
        "Research: FastAPI framework",
        "Research: Flask framework",
        "Research: Django framework"
    ]
    
    results = cli.run_tasks(tasks, parallel=True)
    for result in results:
        if result['success']:
            print(result['output'])
        else:
            print(f"Error: {result['error']}")
    print()


def example_4_error_handling():
    """Example 4: Error handling."""
    print("=" * 70)
    print("Example 4: Error Handling")
    print("=" * 70)
    
    cli = UICLIWrapper()
    result = cli.run_task("Analyze non-existent technology")
    
    if not result['success']:
        print(f"Task failed: {result['error']}")
        print("Attempting recovery...")
        
        recovery_result = cli.run_task("Suggest alternatives to analyze instead")
        if recovery_result['success']:
            print(recovery_result['output'])
    print()


def example_5_code_review():
    """Example 5: Code review integration."""
    print("=" * 70)
    print("Example 5: Automated Code Review")
    print("=" * 70)
    
    code_to_review = """
def calculate_total(items):
    total = 0
    for i in range(len(items)):
        total = total + items[i]['price'] * items[i]['quantity']
    return total
"""
    
    cli = UICLIWrapper()
    result = cli.run_task(f"Review this code and suggest improvements:\n{code_to_review}")
    
    if result['success']:
        print(result['output'])
    print()


def example_6_batch_processing():
    """Example 6: Batch file processing."""
    print("=" * 70)
    print("Example 6: Batch File Processing")
    print("=" * 70)
    
    files = ["module1.py", "module2.py", "module3.py"]
    cli = UICLIWrapper()
    
    for file in files:
        print(f"\nAnalyzing {file}...")
        result = cli.run_task(f"Review: Analyze {file} for code quality (simulated)")
        
        if result['success']:
            print(result['output'][:200] + "...")  # Truncate for example
    print()


def example_7_conditional_logic():
    """Example 7: Conditional execution based on AI response."""
    print("=" * 70)
    print("Example 7: Conditional Logic")
    print("=" * 70)
    
    cli = UICLIWrapper()
    
    # Get security rating
    result = cli.run_task(
        "Rate the security of storing passwords in plain text (1-10). "
        "Respond with just the number."
    )
    
    if result['success']:
        try:
            score = int(result['output'].strip())
            print(f"Security score: {score}/10")
            
            if score < 5:
                print("\nLow security detected! Getting recommendations...")
                rec_result = cli.run_task("Recommend: Best practices for password storage")
                if rec_result['success']:
                    print(rec_result['output'])
        except ValueError:
            print("Could not parse security score")
    print()


def example_8_web_framework_integration():
    """Example 8: Integration with web frameworks (FastAPI example)."""
    print("=" * 70)
    print("Example 8: Web Framework Integration (Conceptual)")
    print("=" * 70)
    
    print("""
# FastAPI Integration Example:

from fastapi import FastAPI, BackgroundTasks
from integration_examples import UICLIWrapper

app = FastAPI()
cli = UICLIWrapper()

@app.post("/analyze")
async def analyze_code(code: str, background_tasks: BackgroundTasks):
    \"\"\"Endpoint to analyze code.\"\"\"
    background_tasks.add_task(perform_analysis, code)
    return {"status": "Analysis started"}

def perform_analysis(code: str):
    result = cli.run_task(f"Review this code: {code}")
    # Process result, store in database, etc.
    return result
""")
    print()


def example_9_testing_integration():
    """Example 9: Integration with testing frameworks."""
    print("=" * 70)
    print("Example 9: Testing Integration (Conceptual)")
    print("=" * 70)
    
    print("""
# pytest Integration Example:

import pytest
from integration_examples import UICLIWrapper

@pytest.fixture
def cli():
    return UICLIWrapper()

def test_code_quality(cli):
    \"\"\"Test that code meets quality standards.\"\"\"
    code = "def foo(): pass"
    result = cli.run_task(f"Rate this code quality (1-10): {code}")
    
    assert result['success']
    # Parse score and assert > threshold
    
def test_security_check(cli):
    \"\"\"Test security analysis.\"\"\"
    result = cli.run_task("Analyze security of this pattern: eval(user_input)")
    
    assert result['success']
    assert "dangerous" in result['output'].lower()
""")
    print()


def example_10_cli_wrapper_advanced():
    """Example 10: Advanced wrapper with caching."""
    print("=" * 70)
    print("Example 10: Advanced Wrapper with Caching")
    print("=" * 70)
    
    print("""
# Advanced wrapper with caching and retry logic:

import functools
import time
from typing import Optional

class AdvancedUICLIWrapper(UICLIWrapper):
    def __init__(self, api_key: str = None, cache_ttl: int = 300):
        super().__init__(api_key)
        self.cache = {}
        self.cache_ttl = cache_ttl
    
    @functools.lru_cache(maxsize=100)
    def run_task_cached(self, task: str) -> Dict[str, Any]:
        \"\"\"Run task with caching.\"\"\"
        cache_key = hash(task)
        
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_result
        
        result = self.run_task(task)
        self.cache[cache_key] = (result, time.time())
        return result
    
    def run_task_with_retry(self, task: str, max_retries: int = 3) -> Dict[str, Any]:
        \"\"\"Run task with retry logic.\"\"\"
        for attempt in range(max_retries):
            result = self.run_task(task)
            if result['success']:
                return result
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return result
""")
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print(" UI-CLI Python Integration Examples")
    print("=" * 70 + "\n")
    
    # Check API key
    if not os.getenv('XAI_API_KEY'):
        print("ERROR: XAI_API_KEY environment variable not set")
        print("Set it with: export XAI_API_KEY=your_key_here")
        sys.exit(1)
    
    # Run examples
    examples = [
        example_1_simple_task,
        example_2_multiple_tasks,
        example_3_parallel_tasks,
        example_4_error_handling,
        example_5_code_review,
        example_6_batch_processing,
        example_7_conditional_logic,
        example_8_web_framework_integration,
        example_9_testing_integration,
        example_10_cli_wrapper_advanced,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"Error running {example.__name__}: {e}")
            print()
    
    print("=" * 70)
    print(" All examples completed!")
    print("=" * 70)


if __name__ == '__main__':
    main()
