#!/usr/bin/env python3
"""
Real DSL Interpreter Example - Full Integration with CLI.

Demonstrates complete pipeline:
1. Parse DSL text → AST
2. Execute AST via Interpreter
3. Interpreter uses CLITaskExecutor
4. Tasks executed via multi-agent system

Clean Code: Shows real-world DSL usage with actual agent mapping.
"""

import asyncio
from src.dsl.adapters.parser import Parser
from src.dsl.use_cases.interpreter import Interpreter
from src.dsl.adapters.cli_task_executor import CLITaskExecutor


async def demo_real_execution(dsl_program: str, description: str):
    """
    Parse and execute DSL with real CLI integration.

    Args:
        dsl_program: DSL source code
        description: Human-readable description
    """
    print(f"\n{'=' * 70}")
    print(f"Example: {description}")
    print(f"{'=' * 70}")
    print(f"DSL Program: {dsl_program}\n")

    # 1. Parse DSL → AST
    parser = Parser()
    ast = parser.parse(dsl_program)
    print(f"Parsed AST: {ast}\n")

    # 2. Create CLI task executor (connects to multi-agent system)
    executor = CLITaskExecutor()
    print(f"Task-to-Agent Mapping:")
    for task, agent in sorted(executor.get_task_mapping().items())[:10]:
        print(f"  {task:15} → {agent}")
    print(f"  ... ({len(executor.get_task_mapping())} total mappings)\n")

    # 3. Create interpreter with CLI executor
    interpreter = Interpreter(executor)

    # 4. Execute AST
    print("Executing DSL program...\n")
    result = await interpreter.execute(ast)

    # 5. Display results
    print(f"Execution Result:")
    print_result(result, indent=2)

    print()


def print_result(result, indent=0):
    """Pretty print execution result."""
    prefix = " " * indent
    if isinstance(result, tuple):
        print(f"{prefix}Parallel Results:")
        for i, r in enumerate(result):
            print(f"{prefix}  [{i}]:")
            print_result(r, indent + 4)
    elif isinstance(result, dict):
        for key, value in result.items():
            if isinstance(value, (dict, list, tuple)):
                print(f"{prefix}{key}:")
                print_result(value, indent + 2)
            else:
                print(f"{prefix}{key}: {value}")
    else:
        print(f"{prefix}{result}")


async def main():
    """Run real interpreter examples."""
    print("=" * 70)
    print("Category Theory DSL - Real Interpreter with CLI Integration")
    print("=" * 70)

    # Example 1: Simple Sequential Task
    await demo_real_execution(
        'test ∘ build',
        "Sequential Pipeline (build → test)"
    )

    # Example 2: Parallel Execution
    await demo_real_execution(
        'frontend × backend',
        "Parallel Development (frontend ∥ backend)"
    )

    # Example 3: Complex Pipeline
    await demo_real_execution(
        '(test_ui × test_api) ∘ (build_ui × build_api) ∘ plan',
        "Full Stack Pipeline (plan → build both → test both)"
    )

    # Example 4: Functor Definition
    await demo_real_execution(
        'functor ci_pipeline = deploy ∘ test ∘ build',
        "CI/CD Functor (reusable workflow)"
    )

    # Example 5: Integration Pipeline
    await demo_real_execution(
        'deploy ∘ integrate ∘ (frontend × backend) ∘ design',
        "End-to-End Development (design → build → integrate → deploy)"
    )

    print(f"\n{'=' * 70}")
    print("Summary")
    print("=" * 70)
    print("\n✅ DSL Programs Successfully Executed\n")
    print("Pipeline:")
    print("  1. DSL Text (∘, ×, functors)")
    print("  2. Lark Parser → AST (immutable entities)")
    print("  3. Interpreter (visitor pattern)")
    print("  4. CLITaskExecutor (task → agent mapping)")
    print("  5. Multi-Agent Execution (coordinated)")
    print("\nCategory Theory Semantics:")
    print("  • Composition (∘): Sequential, right-to-left execution")
    print("  • Product (×): Parallel, concurrent with asyncio")
    print("  • Functors: Reusable workflow mappings")
    print("\nAgent Mapping:")
    print("  • Intelligent task-to-agent assignment")
    print("  • Extensible via custom mappings")
    print("  • Fallback to generic agents")
    print("\nNext Steps:")
    print("  • Connect to real TaskCoordinator for actual execution")
    print("  • Add result propagation through compositions")
    print("  • Implement caching and optimization (fusion)")
    print("  • Create CLI command: `ui-cli run program.ct`")


if __name__ == "__main__":
    asyncio.run(main())
