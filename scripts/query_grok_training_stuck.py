#!/usr/bin/env python3
"""
Consult Grok API: Is Qwen3-8B Training Stuck?

Emergency consultation about training progress concerns.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.query_grok_qwen3 import consult_grok


def main():
    query = """
I'm training Qwen3-8B (8.2B params) with LoRA on CPU (48 cores, 110GB RAM) and concerned training may be stuck.

**Symptoms:**
- Step 1/24 completed in 35:49 minutes (logged at 17:52:08)
- Now 28 minutes later (18:20:35) - NO log update for step 2
- CPU usage: Steady 2670% (27 cores)
- Memory behavior: Fluctuating (123GB → 124GB → 120GB over 4 seconds)
- I/O: ZERO (no reads, no writes between steps)
- Process state: R (running), wchan: - (not waiting)

**Configuration:**
- Model: Qwen3-8B (8.2B params)
- LoRA rank: 16, alpha: 32
- Target modules: q/k/v/o_proj + gate/up/down_proj (7 modules)
- Batch size: 2, gradient accumulation: 16 (effective: 32)
- Framework: Transformers Trainer on CPU

**Questions:**

1. **Is 28+ minutes between step logs normal?**
   - Step 1 took 35:49
   - Should step 2 take similar time or be faster (compilation done)?
   - At what point should I consider it stuck?

2. **What does memory fluctuation indicate?**
   - 123GB → 124GB → 120GB in 4 seconds
   - Is this active computation or just garbage collection?
   - Would a stuck process show static memory?

3. **Why zero I/O between steps?**
   - No read_bytes, no write_bytes changing
   - Is data loading done in-memory after first step?
   - Should I see I/O for checkpoints/logging?

4. **How to definitively diagnose stuck vs working?**
   - What signals prove training is progressing?
   - What tools can I use to verify computation happening?
   - At what point should I kill and restart?

5. **PyTorch Trainer logging behavior:**
   - Does Trainer buffer logs until step complete?
   - Could step 2 be in progress but not visible in logs?
   - How long can computation run between log outputs?

**Context:**
This is critical Week 9 Phase 4 deliverable. Already invested 1 hour training time. Need to know if I should:
- A) Wait longer (if this is normal)
- B) Investigate deeper (if suspicious)
- C) Kill and restart with better logging (if stuck)

Please provide specific, actionable guidance based on PyTorch/Transformers behavior with large models on CPU.
"""

    print("=" * 80)
    print("CONSULTING GROK API: TRAINING DIAGNOSTICS")
    print("=" * 80)
    print("\nQuery: Is Qwen3-8B training stuck or working?\n")

    response = consult_grok(query, verbose=True)

    print("\n" + "=" * 80)
    print("GROK RESPONSE")
    print("=" * 80)
    print(response)
    print("\n" + "=" * 80)

    # Save response
    output_file = Path("training/GROK_TRAINING_DIAGNOSTIC.md")
    with open(output_file, 'w') as f:
        f.write("# Grok API: Training Diagnostic Consultation\n\n")
        f.write("**Query Date**: 2025-10-01 18:20\n")
        f.write("**Issue**: Step 2 log not appearing 28+ minutes after step 1\n\n")
        f.write("---\n\n")
        f.write("## Question\n\n")
        f.write(query)
        f.write("\n\n---\n\n")
        f.write("## Grok Response\n\n")
        f.write(response)

    print(f"\n💾 Response saved to: {output_file}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
