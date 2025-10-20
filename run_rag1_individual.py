#!/usr/bin/env python3
"""Run RAG-1 Research Individually (RAG Architecture)"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.entity.htn.htn_node import HTNNode
from src.adapters.llm.hybrid_executor import HybridTaskExecutor
import time

def main():
    print("="*70)
    print("RAG-1: RAG Architecture Pattern (Hybrid Orchestration)")
    print("="*70)

    executor = HybridTaskExecutor()

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

    print("\nExecuting RAG-1 research...")
    start = time.time()
    result = executor.execute(rag1)
    duration = time.time() - start

    print(f"\n{'✓' if result.success else '✗'} Completed in {duration:.1f}s")

    if result.success:
        output_file = Path("/tmp/rag1_hybrid_output.txt")
        output_file.write_text(result.output)

        print(f"\nOutput length: {len(result.output)} chars")
        print(f"Saved to: {output_file}")
        print(f"\nPreview:\n{result.output[:500]}...")
        return 0
    else:
        print(f"Error: {result.error}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
