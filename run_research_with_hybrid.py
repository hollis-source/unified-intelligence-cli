#!/usr/bin/env python3
"""Re-run Failed Research Using Hybrid Orchestration

Dogfooding our new hybrid system for the original use case:
- CPU optimization for llama.cpp
- RAG implementation with SurrealDB
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.entity.htn.htn_node import HTNNode
from src.adapters.llm.hybrid_executor import HybridTaskExecutor
import time

def main():
    print("="*70)
    print("LLAMA.CPP + RAG RESEARCH (Using Hybrid Orchestration)")
    print("="*70)

    executor = HybridTaskExecutor()

    # Task 2: Thread Allocation (failed before)
    print("\n[1/2] CPU-2: Thread Allocation Model")
    print("-" * 70)

    cpu2 = HTNNode(
        task_id="cpu2_threads",
        description="""Design optimal thread allocation for llama.cpp inference with high RAM (1TB+).

Requirements:
1. Formula: Calculate optimal threads from memory bandwidth (GB/s), not just core count
2. Explain why memory bandwidth limits thread scaling
3. Decision matrix: Physical cores vs hyperthreads based on workload

Focus: Mathematical model and principles, NOT scripts.
Output: Thread count formula + allocation decision table."""
    )

    start = time.time()
    result_cpu2 = executor.execute(cpu2)
    duration_cpu2 = time.time() - start

    print(f"\n{'✓' if result_cpu2.success else '✗'} CPU-2: {duration_cpu2:.1f}s")
    if result_cpu2.success:
        print(f"Output preview:\n{result_cpu2.output[:300]}...")

        # Save output
        Path("/tmp/cpu2_hybrid_output.txt").write_text(result_cpu2.output)
        print(f"Saved to: /tmp/cpu2_hybrid_output.txt")
    else:
        print(f"Error: {result_cpu2.error}")

    # Task 3: RAG Architecture (failed before)
    print("\n[2/2] RAG-1: RAG Architecture Pattern")
    print("-" * 70)

    rag1 = HTNNode(
        task_id="rag1_architecture",
        description="""Design RAG pattern for adaptive agent learning using codebase embeddings.

Context: Python autonomous agent system (HTN planning, multi-agent teams)
Goal: Agents learn from execution patterns to self-optimize

Requirements:
1. How to embed: entities, use cases, adapters (what granularity?)
2. Retrieval strategy: Semantic vs hybrid vs graph-based (pros/cons)
3. Context injection: Where in agent pipeline (TaskPlanner? TeamRouter?)

Focus: Architecture patterns and data flow, NOT implementation.
Output: RAG pattern diagram + retrieval strategy comparison."""
    )

    start = time.time()
    result_rag1 = executor.execute(rag1)
    duration_rag1 = time.time() - start

    print(f"\n{'✓' if result_rag1.success else '✗'} RAG-1: {duration_rag1:.1f}s")
    if result_rag1.success:
        print(f"Output preview:\n{result_rag1.output[:300]}...")

        # Save output
        Path("/tmp/rag1_hybrid_output.txt").write_text(result_rag1.output)
        print(f"Saved to: /tmp/rag1_hybrid_output.txt")
    else:
        print(f"Error: {result_rag1.error}")

    # Summary
    print("\n" + "="*70)
    print("RESEARCH SUMMARY")
    print("="*70)

    total_time = duration_cpu2 + duration_rag1
    success_count = sum([result_cpu2.success, result_rag1.success])

    print(f"Tasks completed: {success_count}/2")
    print(f"Total time: {total_time:.1f}s")
    print(f"Average: {total_time/2:.1f}s per task")

    if success_count == 2:
        print("\n✓ ALL RESEARCH COMPLETE")
        print("\nNext step: Synthesize findings and create implementation plan")
        print("\nResearch outputs:")
        print("  - CPU-1: /tmp/cpu1_output.txt (hardware detection)")
        print("  - CPU-2: /tmp/cpu2_hybrid_output.txt (thread allocation)")
        print("  - RAG-1: /tmp/rag1_hybrid_output.txt (RAG architecture)")
        return 0
    else:
        print(f"\n✗ {2 - success_count} TASKS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
