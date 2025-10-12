#!/usr/bin/env python3
"""
End-to-End Dev Workflow Demo - Complete Pipeline

Demonstrates:
1. Multi-task CLI input
2. Intelligent agent selection
3. Tool-assisted execution with live Grok
4. Real dev workflow: Implement FizzBuzz with tests

This is the culmination of all implemented features.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.entities import Task
from src.composition import compose_dependencies
from src.factories import AgentFactory, ProviderFactory
from src.adapters.cli import ResultFormatter
from src.tools import DEV_TOOLS, TOOL_FUNCTIONS


async def run_workflow():
    """Run complete dev workflow with live Grok."""

    print("=" * 80)
    print("UNIFIED INTELLIGENCE CLI - END-TO-END DEMO")
    print("=" * 80)
    print()
    print("Workflow: Implement FizzBuzz with Tests")
    print("Provider: Live Grok API with tool support")
    print()

    # Check API key
    if not os.getenv("XAI_API_KEY"):
        print("❌ Error: XAI_API_KEY not set")
        print("Please set your XAI API key in .env file")
        return

    # Define dev workflow tasks
    tasks = [
        Task(
            description="Write a Python function that implements FizzBuzz. The function should take a number and return 'Fizz' for multiples of 3, 'Buzz' for multiples of 5, 'FizzBuzz' for multiples of both, and the number as string otherwise. Save it to demo_fizzbuzz.py",
            task_id="task_1_implement",
            priority=1
        ),
        Task(
            description="Write comprehensive pytest tests for the FizzBuzz function covering all cases: multiples of 3, 5, both, and regular numbers. Save tests to demo_fizzbuzz_test.py",
            task_id="task_2_test",
            priority=2
        ),
        Task(
            description="Run the tests using pytest on demo_fizzbuzz_test.py and report the results",
            task_id="task_3_verify",
            priority=3
        )
    ]

    print("Tasks defined:")
    for i, task in enumerate(tasks, 1):
        print(f"  {i}. [{task.task_id}] {task.description[:80]}...")
    print()

    # Create factories (DIP)
    agent_factory = AgentFactory()
    provider_factory = ProviderFactory()

    # Create agents
    agents = agent_factory.create_default_agents()
    print(f"Agents available: {', '.join(a.role for a in agents)}")
    print()

    # Create Grok provider with tool support
    print("Creating Grok provider with dev tools...")
    grok_provider = provider_factory.create_provider("grok")

    # Inject tools if provider supports them
    if hasattr(grok_provider, 'supports_tools') and grok_provider.supports_tools():
        print(f"✓ Tool support enabled ({len(DEV_TOOLS)} tools available)")
        # Register tools with the Grok session
        if hasattr(grok_provider, 'session'):
            for tool in DEV_TOOLS:
                tool_name = tool["function"]["name"]
                if tool not in grok_provider.session.tools:
                    grok_provider.session.tools.append(tool)
                if tool_name in TOOL_FUNCTIONS:
                    grok_provider.session.tool_functions[tool_name] = TOOL_FUNCTIONS[tool_name]
            print(f"✓ Tools registered: {', '.join(t['function']['name'] for t in DEV_TOOLS)}")
    print()

    # Compose dependencies (Clean Architecture)
    coordinator = compose_dependencies(
        llm_provider=grok_provider,
        agents=agents,
        logger=None
    )

    print("Starting task coordination...")
    print("=" * 80)
    print()

    # Execute with timeout
    try:
        results = await asyncio.wait_for(
            coordinator.coordinate(
                tasks=tasks,
                agents=agents
            ),
            timeout=120  # 2 minutes for dev work
        )
    except asyncio.TimeoutError:
        print("❌ Error: Operation timed out after 2 minutes")
        return

    # Display results
    print()
    print("=" * 80)
    print("EXECUTION RESULTS")
    print("=" * 80)
    print()

    formatter = ResultFormatter(verbose=True)
    formatter.format_results(results)

    # Summary
    print()
    print("=" * 80)
    print("WORKFLOW SUMMARY")
    print("=" * 80)
    print()

    success_count = sum(1 for r in results if r.status.value == "success")
    print(f"Tasks completed: {success_count}/{len(tasks)}")
    print()

    # Check if files were created
    fizzbuzz_file = Path("demo_fizzbuzz.py")
    test_file = Path("demo_fizzbuzz_test.py")

    if fizzbuzz_file.exists():
        print(f"✓ Implementation created: {fizzbuzz_file}")
        print(f"  Size: {fizzbuzz_file.stat().st_size} bytes")

    if test_file.exists():
        print(f"✓ Tests created: {test_file}")
        print(f"  Size: {test_file.stat().st_size} bytes")

    print()
    print("=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print()
    print("Key achievements demonstrated:")
    print("  ✓ Multi-task CLI input (3 sequential tasks)")
    print("  ✓ Intelligent agent selection (coder, tester agents)")
    print("  ✓ Tool-assisted execution (file writes, pytest)")
    print("  ✓ End-to-end dev workflow (implement → test → verify)")
    print()


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("Error: Python 3.8+ required")
        sys.exit(1)

    # Run async workflow
    asyncio.run(run_workflow())