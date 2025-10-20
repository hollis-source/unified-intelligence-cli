"""Benchmark IBM Granite 4.0-H agentic capabilities."""

import requests
import json
import time

GRANITE_INSTANCE = "http://localhost:8080"

def query_granite(prompt, max_tokens=500, temperature=0.7):
    response = requests.post(
        f"{GRANITE_INSTANCE}/completion",
        json={"prompt": prompt, "n_predict": max_tokens, "temperature": temperature},
        timeout=60
    )
    return response.json()

def test_tool_calling():
    print("\n" + "="*80)
    print("TEST 1: TOOL CALLING")
    print("="*80)
    
    prompt = """Task: Check Python version. Use bash_execute tool.

Generate a tool call:
<tool_call>
  <name>bash_execute</name>
  <parameters>
    <command>python3 --version</command>
  </parameters>
</tool_call>

Your response:"""
    
    result = query_granite(prompt, max_tokens=150, temperature=0.3)
    response = result.get('content', '')
    print(f"Response: {response[:400]}")
    
    has_tool_call = "<tool_call>" in response
    has_bash = "bash" in response.lower() or "python" in response.lower()
    passed = has_tool_call or has_bash
    
    print(f"{'✅' if passed else '❌'} Tool calling capability")
    return {"test": "tool_calling", "passed": passed}

def test_task_decomposition():
    print("\n" + "="*80)
    print("TEST 2: TASK DECOMPOSITION")
    print("="*80)
    
    prompt = """Task: Implement user authentication for a web app.

Break into 5 subtasks (numbered list):"""
    
    result = query_granite(prompt, max_tokens=300, temperature=0.5)
    response = result.get('content', '')
    print(f"Response: {response[:500]}")
    
    has_list = any(f"{i}." in response for i in range(1, 4))
    has_auth = "password" in response.lower() or "database" in response.lower()
    passed = has_list and has_auth
    
    print(f"{'✅' if passed else '❌'} Task decomposition capability")
    return {"test": "task_decomposition", "passed": passed}

def test_error_recovery():
    print("\n" + "="*80)
    print("TEST 3: ERROR RECOVERY")
    print("="*80)
    
    prompt = """Code:
def avg(nums):
    return sum(nums) / len(nums)

avg([])  # ZeroDivisionError

Fix this error:"""
    
    result = query_granite(prompt, max_tokens=200, temperature=0.3)
    response = result.get('content', '')
    print(f"Response: {response[:400]}")
    
    has_fix = "if" in response.lower() or "len(nums) > 0" in response
    identifies_issue = "empty" in response.lower() or "zero" in response.lower()
    passed = has_fix or identifies_issue
    
    print(f"{'✅' if passed else '❌'} Error recovery capability")
    return {"test": "error_recovery", "passed": passed}

def main():
    print("="*80)
    print("GRANITE 4.0-H AGENTIC BENCHMARK")
    print("="*80)
    
    results = []
    start = time.time()
    
    results.append(test_tool_calling())
    results.append(test_task_decomposition())
    results.append(test_error_recovery())
    
    elapsed = time.time() - start
    passed = sum(1 for r in results if r["passed"])
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Passed: {passed}/3 ({passed/3*100:.0f}%)")
    print(f"Time: {elapsed:.1f}s")
    
    if passed >= 2:
        print("\n✅ PROCEED with ATADO integration")
    else:
        print("\n⚠️  Consider API models for complex agentic tasks")
    
    with open("granite_benchmark.json", "w") as f:
        json.dump({"results": results, "passed": passed, "total": 3}, f, indent=2)

if __name__ == "__main__":
    main()
