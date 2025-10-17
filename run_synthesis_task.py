#!/usr/bin/env python3
"""Synthesize All Research Into Deployment Plan

Meta-synthesis task that:
1. Reads all 6 research outputs
2. Identifies key decisions from each
3. Resolves conflicts
4. Creates unified deployment plan
5. Identifies gaps requiring additional research (Batch 3?)

Execution: Single auggie task (15-20 min estimated)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.entity.htn.htn_node import HTNNode
from src.adapters.llm.hybrid_executor import HybridTaskExecutor


def build_synthesis_prompt() -> str:
    """Build comprehensive synthesis prompt with all research inputs"""

    # Read all 6 research outputs
    cpu1 = Path("/tmp/cpu1_output.txt").read_text()
    cpu2 = Path("/tmp/cpu2_hybrid_output.txt").read_text()
    rag1 = Path("/tmp/rag1_output.txt").read_text() if Path("/tmp/rag1_output.txt").exists() else "[RAG-1 not yet available]"
    ram1 = Path("/tmp/ram1_output.txt").read_text()
    quant1 = Path("/tmp/quant1_output.txt").read_text()
    surrealdb1 = Path("/tmp/surrealdb1_output.txt").read_text()

    prompt = f"""COMPREHENSIVE SYNTHESIS TASK: IBM Granite 4.0-H Small (32B-A9B) + RAG Deployment Plan

## Mission
Synthesize 6 completed research outputs into unified, actionable deployment plan for:
- Model: IBM Granite 4.0-H Small (32B-A9B) in GGUF format
- Hardware: 1TB+ RAM server, CPU inference
- Goal: Production llama.cpp deployment + SurrealDB RAG integration

## Research Inputs

### INPUT 1: CPU-1 (Hardware Detection Strategy)
```
{cpu1[:2000]}...
[TRUNCATED - Full research available, contains: hardware detection commands, NUMA decision tree, JSON schema]
```

### INPUT 2: CPU-2 (Thread Allocation Model)
```
{cpu2[:2000]}...
[TRUNCATED - Full research available, contains: bandwidth-based formula, physical vs HT decision matrix]
```

### INPUT 3: RAG-1 (RAG Architecture Pattern)
```
{rag1[:2000] if rag1 != "[RAG-1 not yet available]" else rag1}...
[TRUNCATED if available - Full research available, contains: embedding granularity, retrieval strategies, context injection]
```

### INPUT 4: RAM-1 (RAM Utilization Strategy - 1TB+)
```
{ram1[:2000]}...
[TRUNCATED - Full research available, contains: 5 strategies, multiple models recommendation, capacity calculations]
```

### INPUT 5: QUANT-1 (Quantization Selection)
```
{quant1[:2000]}...
[TRUNCATED - Full research available, contains: Q5_K_M recommendation, MoE-specific analysis, quality vs speed]
```

### INPUT 6: SURREALDB-1 (SurrealDB Vector Integration)
```
{surrealdb1[:2000]}...
[TRUNCATED - Full research available, contains: <100ms latency architecture, hybrid search, caching strategy]
```

## Synthesis Requirements

### 1. Executive Summary (1 page)
Create high-level overview of final deployment strategy addressing:
- What we're deploying (model, quantization, instances)
- How we're leveraging 1TB RAM (multiple models? massive context?)
- RAG integration approach (SurrealDB, embedding, retrieval)
- Expected performance (throughput, latency, capacity)

### 2. Key Decisions Matrix
For each decision, show:
- Options considered (from research)
- Choice made
- Rationale (data-driven)
- Trade-offs accepted

Decisions to cover:
a) **Quantization**: F16/Q8/Q5_K_M/Q4_K_M/Q4_0
b) **RAM Strategy**: Multiple models / Massive context / Aggressive cache / Speculative / Ensemble
c) **Instance Count**: How many model instances in 1TB RAM?
d) **Thread Allocation**: Formula-based thread count
e) **NUMA Configuration**: Single/interleave/pinned
f) **RAG Architecture**: Semantic/hybrid/graph-based retrieval
g) **Embedding Model**: nomic-embed-text vs alternatives
h) **Chunking Strategy**: File/function/class level

### 3. Unified Deployment Plan
Create phased implementation plan:

**Phase 1: Infrastructure Setup**
- Hardware detection and configuration
- NUMA setup
- Resource allocation

**Phase 2: Model Deployment**
- Download/convert Granite GGUF
- Deploy N instances with calculated threads
- Validate performance

**Phase 3: RAG Integration**
- SurrealDB vector store setup
- Codebase embedding pipeline
- Integration with llama.cpp

**Phase 4: Testing & Optimization**
- Performance benchmarks
- Quality validation
- Tuning and optimization

For each phase:
- Specific tasks
- Dependencies
- Success criteria
- Estimated timeline

### 4. Conflict Resolution
Identify any conflicting recommendations across research:
- Example: RAM-1 says "multiple models" but QUANT-1 might suggest "fewer higher-quality instances"
- Resolve with data and clear reasoning
- Document trade-offs

### 5. Gap Analysis & Batch 3 Assessment
Critically evaluate what's MISSING from our research:
- Are there unresolved questions?
- Do we need more research on:
  - Batch processing optimization? (BATCH-1 from original plan)
  - System integration details? (INTEGRATION-1 from original plan)
  - Something else not yet identified?
- Can we proceed to implementation with current research, or do we need Batch 3?

**Decision criteria**:
- ✓ Proceed if: All critical decisions have data-driven answers
- ✗ Batch 3 needed if: Key uncertainties remain that would block implementation

### 6. Implementation Priorities & Next Steps
Provide concrete next actions:
1. Immediate next step (what to do first)
2. Critical path (what blocks everything else)
3. Parallel workstreams (what can happen concurrently)
4. Success metrics (how to validate)

## Output Requirements

**Format**: Markdown document with:
- Clear section headers
- Decision tables (markdown tables)
- Bullet points for action items
- Code snippets for commands (if applicable)

**Length**: Comprehensive but concise (aim for 3-5 pages of dense content)

**Tone**: Technical, data-driven, actionable

**Critical**: Be specific with numbers from research:
- "Deploy 10 instances of Q5_K_M (30GB each)" not "deploy several instances"
- "Use 32 threads based on 307 GB/s bandwidth" not "use appropriate thread count"
- "Expect 14-22 tok/s per instance" not "good performance"

## Success Criteria

Your synthesis succeeds if:
1. ✓ All 6 research outputs are integrated (no orphaned findings)
2. ✓ Every decision has clear rationale with data
3. ✓ Conflicts are identified and resolved
4. ✓ Gap analysis is honest and critical
5. ✓ Next steps are immediately actionable
6. ✓ Someone could implement this plan without further research (if gaps filled)

Begin synthesis now. Think step by step, cross-reference findings, and create the definitive deployment plan.
"""

    return prompt


def main():
    print("="*80)
    print("SYNTHESIS TASK: All Research → Deployment Plan")
    print("="*80)
    print()
    print("Input: 6 research outputs")
    print("  - CPU-1: Hardware Detection Strategy")
    print("  - CPU-2: Thread Allocation Model")
    print("  - RAG-1: RAG Architecture Pattern")
    print("  - RAM-1: RAM Utilization Strategy (1TB+)")
    print("  - QUANT-1: Quantization Selection")
    print("  - SURREALDB-1: SurrealDB Vector Integration")
    print()
    print("Output: Unified deployment plan + gap analysis")
    print("Estimated time: 15-20 minutes")
    print()
    print("="*80)

    # Build synthesis prompt
    prompt = build_synthesis_prompt()

    # Create HTN node
    node = HTNNode(
        task_id="synthesis_deployment_plan",
        description=prompt
    )

    # Execute synthesis
    print("\nExecuting meta-synthesis task...")
    print("(This will take 15-20 minutes - complex integration task)")
    print()

    executor = HybridTaskExecutor()
    result = executor.execute(node)

    # Report results
    print("\n" + "="*80)
    print("SYNTHESIS COMPLETE")
    print("="*80)

    if result.success:
        print(f"✓ SUCCESS in {result.duration_seconds:.1f}s")
        print(f"\nOutput length: {len(result.output)} chars")

        # Save output
        output_file = Path("/tmp/deployment_plan_synthesis.md")
        output_file.write_text(result.output)

        print(f"Saved to: {output_file}")
        print()
        print("Preview:")
        print("-" * 80)
        print(result.output[:1000])
        print("...")
        print("-" * 80)

        return 0
    else:
        print(f"✗ FAILED")
        print(f"Error: {result.error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
