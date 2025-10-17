#!/usr/bin/env python3
"""Complete Research Task Definitions for llama.cpp + RAG Deployment

Comprehensive research covering:
1. RAM utilization strategies (1TB+)
2. Quantization selection
3. SurrealDB vector integration
4. Batch processing optimization
5. Integration architecture

Designed for execution via HybridTaskExecutor (dogfooding our orchestration)
"""

from dataclasses import dataclass
from typing import List

@dataclass
class ResearchTask:
    """Research task definition"""
    task_id: str
    title: str
    description: str
    priority: int  # 1=highest
    batch: int  # Which batch to run in
    dependencies: List[str]  # Task IDs that must complete first


# ============================================================================
# BATCH 1: Foundation (Already Running)
# ============================================================================

BATCH_1 = [
    ResearchTask(
        task_id="cpu1",
        title="Hardware Detection Strategy",
        description="""Design a detection strategy for auto-configuring llama.cpp on unknown server hardware.

Requirements:
1. List Linux commands/tools to detect: CPU cores, NUMA nodes, memory channels, cache sizes
2. Create decision tree: When to enable/disable NUMA based on socket count
3. Output format: JSON schema for hardware specs

Focus: Strategy and tooling approach, NOT implementation code.
Output: Detection workflow (tool → data → decision) + NUMA decision matrix.""",
        priority=1,
        batch=1,
        dependencies=[]
    ),

    ResearchTask(
        task_id="cpu2",
        title="Thread Allocation Model",
        description="""Design optimal thread allocation for llama.cpp inference with high RAM (1TB+).

Requirements:
1. Formula: Calculate optimal threads from memory bandwidth (GB/s), not just core count
2. Explain why memory bandwidth limits thread scaling
3. Decision matrix: Physical cores vs hyperthreads based on workload

Focus: Mathematical model and principles, NOT scripts.
Output: Thread count formula + allocation decision table.""",
        priority=1,
        batch=1,
        dependencies=[]
    ),

    ResearchTask(
        task_id="rag1",
        title="RAG Architecture Pattern",
        description="""Design RAG pattern for adaptive agent learning using codebase embeddings.

Context: Python autonomous agent system (HTN planning, multi-agent teams)
Goal: Agents learn from execution patterns to self-optimize

Requirements:
1. How to embed: entities, use cases, adapters (what granularity?)
2. Retrieval strategy: Semantic vs hybrid vs graph-based (pros/cons)
3. Context injection: Where in agent pipeline (TaskPlanner? TeamRouter?)

Focus: Architecture patterns and data flow, NOT implementation.
Output: RAG pattern diagram + retrieval strategy comparison.""",
        priority=2,
        batch=1,
        dependencies=[]
    )
]


# ============================================================================
# BATCH 2: RAM Utilization & Model Selection (NEW - HIGH PRIORITY)
# ============================================================================

BATCH_2 = [
    ResearchTask(
        task_id="ram1",
        title="RAM Utilization Strategy (1TB+)",
        description="""Design optimal RAM utilization strategy for llama.cpp with 1TB+ available memory.

Context: Server with 1TB+ RAM running llama.cpp CPU inference
Model: IBM Granite 4.0-H Small (32B-A9B) - MoE architecture

Research Question: What's the best way to leverage massive RAM capacity?

Requirements:
1. Compare strategies:
   - Multiple models in RAM (routing complexity, use cases)
   - Single model + massive context windows (32K-128K tokens)
   - Aggressive KV cache (cache all prompts, context reuse)
   - Speculative decoding (draft model + target model in RAM)
   - Model ensemble (diversity of outputs)

2. For each strategy, analyze:
   - RAM footprint calculation
   - Throughput impact (requests/sec)
   - Latency characteristics
   - Complexity (routing, orchestration)
   - Use case fit (when is this optimal?)

3. Decision matrix:
   - When to use multiple models vs single model
   - How many models can fit in 1TB RAM (with different quantizations)
   - Trade-offs: flexibility vs simplicity

Focus: Strategy comparison with quantitative analysis.
Output: Decision matrix + RAM allocation recommendations.""",
        priority=1,  # USER PRIORITY
        batch=2,
        dependencies=["cpu1", "cpu2"]  # Need hardware info first
    ),

    ResearchTask(
        task_id="quant1",
        title="Quantization Selection for IBM Granite 32B-A9B",
        description="""Determine optimal GGUF quantization for IBM Granite 4.0-H Small on CPU inference.

Context:
- Model: IBM Granite 4.0-H Small (32B parameters, 9B active via MoE)
- Hardware: CPU inference, 1TB+ RAM available
- Goal: Balance quality, speed, and memory efficiency

Requirements:
1. Compare quantizations for 32B MoE model:
   - F16: Full precision (baseline quality)
   - Q8_0: High quality, moderate compression
   - Q5_K_M: Balanced quality/size
   - Q4_K_M: High compression, good quality
   - Q4_0: Maximum compression

2. For each quantization, estimate:
   - Total RAM footprint (model + KV cache + overhead)
   - Inference speed impact (tokens/sec on CPU)
   - Quality degradation (perplexity, benchmark scores)
   - How many instances fit in 1TB RAM

3. MoE-specific considerations:
   - Active parameters vs total parameters impact
   - Expert loading patterns
   - Memory access patterns

Focus: Data-driven quantization selection for our specific model and hardware.
Output: Quantization comparison table + recommendation.""",
        priority=1,
        batch=2,
        dependencies=["cpu2"]  # Need thread model
    ),

    ResearchTask(
        task_id="surrealdb1",
        title="SurrealDB Vector Store Integration",
        description="""Design integration between llama.cpp inference and SurrealDB vector database.

Context:
- Database: SurrealDB with vector search capabilities
- Use case: Store codebase embeddings for adaptive agent learning
- Goal: Real-time RAG with <100ms retrieval latency

Requirements:
1. SurrealDB vector capabilities:
   - Vector similarity search performance (ANN algorithms)
   - Embedding dimension limits (384, 768, 1024, 1536?)
   - Indexing strategies (HNSW, IVF, etc.)
   - Query performance with 10K-1M vectors

2. Embedding generation strategy:
   - Local embedding model (e.g., nomic-embed-text) vs API
   - Batch embedding vs real-time
   - Chunking strategy (code files, functions, classes?)
   - Embedding granularity for agent system

3. Integration architecture:
   - llama.cpp → SurrealDB connection pattern
   - Query flow: User prompt → retrieve context → augment prompt
   - Caching strategy (embed once, query many)
   - Update frequency (when to re-embed codebase?)

4. Performance optimization:
   - Hybrid search (semantic + keyword)
   - Re-ranking strategies
   - Context window management (top-k selection)

Focus: Production-ready architecture, not proof of concept.
Output: Integration diagram + performance expectations + data flow.""",
        priority=2,
        batch=2,
        dependencies=["rag1"]  # Need RAG architecture first
    )
]


# ============================================================================
# BATCH 3: Optimization & Integration (Follow-up)
# ============================================================================

BATCH_3 = [
    ResearchTask(
        task_id="batch1",
        title="Batch Processing & Throughput Optimization",
        description="""Design batch processing strategy to maximize throughput with 1TB RAM.

Context: CPU inference with massive RAM, multi-user workload expected
Goal: Maximize requests/second while maintaining acceptable latency

Requirements:
1. Batching strategies:
   - Static batching (fixed batch size)
   - Dynamic batching (continuous batching)
   - Chunked prefill (split prompt processing)
   - KV cache sharing (similar prompts)

2. For 1TB RAM scenario:
   - Optimal batch sizes (decode vs prefill)
   - Parallel request limits (--parallel flag)
   - Memory allocation per request
   - Context switching overhead

3. Multi-model scenario (if RAM-1 recommends it):
   - Request routing logic
   - Load balancing across models
   - Failover strategies

Focus: Throughput optimization leveraging massive RAM.
Output: Batch size recommendations + parallel request limits.""",
        priority=3,
        batch=3,
        dependencies=["ram1", "quant1"]  # Need RAM strategy first
    ),

    ResearchTask(
        task_id="integration1",
        title="Complete System Integration Architecture",
        description="""Design end-to-end architecture for llama.cpp + SurrealDB + agent system.

Context: Autonomous agent system (HTN planning, multi-agent teams) enhanced with LLM + RAG
Goal: Seamless integration with minimal latency overhead

Requirements:
1. Component integration:
   - Agent system (TaskPlanner, TeamRouter, HTNNode)
   - llama.cpp inference server (REST API)
   - SurrealDB vector store (embeddings + metadata)
   - Embedding service (nomic-embed-text or similar)

2. Data flow patterns:
   - Agent task → retrieve context → generate prompt → inference
   - Result → extract learnings → embed → store
   - Feedback loop (agent performance → RAG optimization)

3. API design:
   - Agent → llama.cpp interface
   - llama.cpp → SurrealDB interface
   - Async vs sync operations
   - Error handling and retries

4. Performance considerations:
   - Latency budget (<200ms end-to-end?)
   - Caching strategies (prompt cache, context cache)
   - Monitoring and metrics

Focus: Production-grade system architecture.
Output: Architecture diagram + API specs + deployment topology.""",
        priority=3,
        batch=3,
        dependencies=["rag1", "surrealdb1", "ram1"]  # Need all foundations
    )
]


# ============================================================================
# Summary
# ============================================================================

ALL_TASKS = BATCH_1 + BATCH_2 + BATCH_3

def print_research_plan():
    """Print formatted research plan"""
    print("=" * 80)
    print("COMPREHENSIVE RESEARCH PLAN: llama.cpp + RAG Deployment")
    print("=" * 80)
    print()

    for batch_num in [1, 2, 3]:
        tasks = [t for t in ALL_TASKS if t.batch == batch_num]
        print(f"\n{'='*80}")
        print(f"BATCH {batch_num}: {len(tasks)} tasks")
        print(f"{'='*80}\n")

        for task in sorted(tasks, key=lambda t: t.priority):
            print(f"[P{task.priority}] {task.task_id.upper()}: {task.title}")
            if task.dependencies:
                print(f"    Dependencies: {', '.join(task.dependencies)}")
            print()

    print(f"\n{'='*80}")
    print(f"TOTAL: {len(ALL_TASKS)} research tasks across 3 batches")
    print(f"{'='*80}\n")

    print("Execution Strategy:")
    print("  - Batch 1: RUNNING (CPU-1, CPU-2, RAG-1)")
    print("  - Batch 2: Execute after Batch 1 completes (RAM-1, QUANT-1, SURREALDB-1)")
    print("  - Batch 3: Execute after Batch 2 completes (BATCH-1, INTEGRATION-1)")
    print()
    print("Dogfooding: All tasks executed via HybridTaskExecutor")
    print("  - Validates our multi-agent orchestration system")
    print("  - Measures: execution time, success rate, output quality")
    print()


if __name__ == "__main__":
    print_research_plan()

    # Export for programmatic use
    print("\nTask IDs for batch execution:")
    print(f"  BATCH_1_IDS = {[t.task_id for t in BATCH_1]}")
    print(f"  BATCH_2_IDS = {[t.task_id for t in BATCH_2]}")
    print(f"  BATCH_3_IDS = {[t.task_id for t in BATCH_3]}")
