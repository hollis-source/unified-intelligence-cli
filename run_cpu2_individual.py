#!/usr/bin/env python3
"""Run CPU-2 Research Individually (Thread Allocation)"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.entity.htn.htn_node import HTNNode
from src.adapters.llm.hybrid_executor import HybridTaskExecutor
import time

def main():
    print("="*70)
    print("CPU-2: Thread Allocation Model (Hybrid Orchestration)")
    print("="*70)

    executor = HybridTaskExecutor()

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

    print("\nExecuting CPU-2 research...")
    start = time.time()
    result = executor.execute(cpu2)
    duration = time.time() - start

    print(f"\n{'✓' if result.success else '✗'} Completed in {duration:.1f}s")

    if result.success:
        output_file = Path("/tmp/cpu2_hybrid_output.txt")
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
