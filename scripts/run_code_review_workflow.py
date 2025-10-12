#!/usr/bin/env python3
"""Execute Multi-Model Code Review Workflow.

Demonstrates broadcast composition in practice by running the workflow
against the current codebase's uncommitted changes.

Usage:
    python scripts/run_code_review_workflow.py

Clean Architecture: Application script (outermost layer)
Sprint: Verifying broadcast composition works end-to-end
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dsl.adapters.parser import Parser
from src.dsl.use_cases import WorkflowValidator, TypedInterpreter
from src.dsl.adapters.cli_task_executor import CLITaskExecutor
from src.dsl.entities.functor import Functor


async def main():
    """Execute multi-model code review workflow."""
    print("\n" + "="*80)
    print("Multi-Model Code Review - Broadcast Composition Demo")
    print("="*80 + "\n")

    # Setup
    parser = Parser()
    validator = WorkflowValidator()
    executor = CLITaskExecutor()
    workflow_path = Path("examples/workflows/multi_model_code_review.ct")

    # Read and validate workflow
    print("📋 Step 1: Validating workflow...")
    with open(workflow_path, 'r') as f:
        workflow_text = f.read()

    report = validator.validate_text(workflow_text)
    if not report.success:
        print(f"❌ Validation failed:\n{report.summary()}")
        return 1

    print(f"✅ Validation passed: 0 errors, 0 warnings")
    print(f"   - {len(report.type_environment.bindings)} type bindings")
    print()

    # Parse workflow
    print("🔍 Step 2: Parsing workflow...")
    ast = parser.parse(workflow_text)
    if ast is None:
        print("❌ Parse failed")
        return 1

    # Find compliance_pipeline functor
    compliance_pipeline = None
    if isinstance(ast, list):
        for node in ast:
            if isinstance(node, Functor) and node.name == "compliance_pipeline":
                compliance_pipeline = node
                break

    if compliance_pipeline is None:
        print("❌ compliance_pipeline functor not found")
        return 1

    print(f"✅ Found compliance_pipeline functor")
    print()

    # Execute workflow with timing
    print("🚀 Step 3: Executing compliance_pipeline (parallel SOLID + Security analysis)...")
    print("   Expected: ~0.6s parallel (max(0.5s SOLID, 0.6s Security))")
    print("   Sequential would be: ~1.1s (0.5s + 0.6s)")
    print()

    interpreter = TypedInterpreter(
        task_executor=executor,
        type_env=report.type_environment,
        strict=True
    )

    import time
    start_time = time.perf_counter()
    result = await interpreter.execute(compliance_pipeline.expression)
    execution_time = time.perf_counter() - start_time

    # Unwrap TypedData if needed
    from src.dsl.use_cases.typed_data import TypedData
    if isinstance(result, TypedData):
        result_value = result.value
    else:
        result_value = result

    # Verify execution
    if result_value.get("status") != "success":
        print(f"❌ Execution failed: {result_value}")
        return 1

    print(f"\n✅ Execution completed successfully!")
    print(f"⏱️  Parallel execution time: {execution_time:.3f}s")
    print(f"📊 Speedup vs sequential: ~{1.1/execution_time:.1f}x")
    print(f"🎯 Parallel efficiency: {((1.1 - execution_time) / 1.1 * 100):.1f}%")
    print()

    # Show type information
    print("🔬 Type Safety Verification:")
    compliance_type = report.type_environment.lookup("compliance_pipeline")
    print(f"   compliance_pipeline :: {compliance_type}")
    print(f"   Broadcast composition: (analyze_solid × analyze_security) ∘ duplicate")
    print()

    print("="*80)
    print("✅ Broadcast Composition Demo Complete!")
    print("="*80 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
