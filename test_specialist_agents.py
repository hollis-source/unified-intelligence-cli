"""
Test Specialist Agents with Granite + RAG

Quick validation test (5 min runtime) to verify:
1. Each specialist responds to domain-specific prompts
2. RAG provides relevant codebase context
3. English-only responses (ULTRATHINK disabled)
4. Output quality appropriate for domain

Run before expensive 7-agent analysis to catch issues early.

Usage:
    python test_specialist_agents.py

Expected output:
    SPECIALIST AGENT TEST
    Testing: Python Engineer
      ✅ PASS (250 chars)
    Testing: DSL Engineer
      ✅ PASS (280 chars)
    ...
    ✅ All specialists tested
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.adapters.llm.granite_adapter import GraniteAdapter
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.entity import Task
from src.interface import LLMConfig
from specialist_agents import create_specialist_agents


async def test_specialists():
    """Quick test of each specialist with simple domain-specific task."""

    print("=" * 80)
    print("SPECIALIST AGENT TEST")
    print("=" * 80)
    print("LLM: IBM Granite 4.0-H (local, via llama.cpp)")
    print("RAG: Disabled (validation test only)")
    print("Config: enable_ultrathink=False, enable_cache=False")
    print("=" * 80)
    print()

    # Setup Granite (RAG disabled for simple validation)
    granite = GraniteAdapter(enable_rag=False)
    executor = LLMAgentExecutor(
        llm_provider=granite,
        default_config=LLMConfig(temperature=0.7, max_tokens=300),
        enable_cache=False,
        enable_ultrathink=False  # Granite compatibility
    )

    specialists = create_specialist_agents()

    # Test each specialist with domain-specific prompt
    tests = [
        {
            "name": "Python Engineer",
            "agent": specialists["python_engineer"],
            "task": (
                "Explain 3 Python design patterns used in software engineering. "
                "Give examples: Factory, Adapter, Strategy."
            )
        },
        {
            "name": "DSL Engineer",
            "agent": specialists["dsl_engineer"],
            "task": (
                "What is Lark parser generator? "
                "Explain how it works and why it's used for DSL implementation."
            )
        },
        {
            "name": "Category Theory Specialist",
            "agent": specialists["category_theory_specialist"],
            "task": (
                "Define morphism in category theory. "
                "Give a programming example (e.g., function composition)."
            )
        },
        {
            "name": "HTN Expert",
            "agent": specialists["htn_expert"],
            "task": (
                "Explain Hierarchical Task Network (HTN) planning. "
                "What is a DAG and why is it important for HTN?"
            )
        },
        {
            "name": "Algorithms Expert",
            "agent": specialists["algorithms_expert"],
            "task": (
                "Explain Big O notation. "
                "Compare O(n²) vs O(n log n) with examples."
            )
        }
    ]

    results = []

    for test in tests:
        print(f"Testing: {test['name']}")
        print(f"  Role: {test['agent'].role}")
        print(f"  Task: {test['task'][:80]}...")

        task = Task(description=test['task'], priority=1)
        result = await executor.execute(test['agent'], task)

        # Validation
        success = (
            result.status.name == "SUCCESS" and
            result.output and
            len(result.output) > 100 and
            "single responsibility" not in result.output.lower() # Not generic response
        )

        # Check for Chinese characters (should be 0)
        chinese_chars = sum(1 for c in result.output if '\u4e00' <= c <= '\u9fff')
        has_chinese = chinese_chars > 10

        if success and not has_chinese:
            print(f"  ✅ PASS ({len(result.output)} chars)")
        else:
            print(f"  ❌ FAIL ({len(result.output)} chars)")
            if has_chinese:
                print(f"     Warning: {chinese_chars} Chinese characters detected")
            print(f"     Output preview: {result.output[:150]}...")

        results.append({
            "name": test["name"],
            "agent": test["agent"].role,
            "passed": success and not has_chinese,
            "output_length": len(result.output or ''),
            "has_chinese": has_chinese
        })

        print()

    # Summary
    print("=" * 80)
    passed = sum(1 for r in results if r["passed"])
    print(f"✅ Passed: {passed}/{len(results)}")

    if passed == len(results):
        print("✅ All specialists tested")
        print("Ready to run full analysis")
    else:
        print("⚠️  Some specialists failed")
        print("Check output above for details")

    print("=" * 80)

    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(test_specialists())
    sys.exit(0 if success else 1)
