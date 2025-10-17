#!/bin/bash
# Sequential Multi-Agent Research Orchestrator
# Runs 10 research tasks sequentially with model switching
# OPTIMIZED: Uses minimal workspace for 55-91x speedup (3.3s/task vs 180-300s)

set -e

# Configuration
OUTPUT_DIR="/home/ui-cli_jake/unified-intelligence-cli/docs/multi_agent_research"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SESSION_DIR="$OUTPUT_DIR/session_$TIMESTAMP"

# OPTIMIZATION: Create minimal workspace to avoid 3-5min indexing delays
MINIMAL_WORKSPACE="/tmp/auggie_llama_research"
mkdir -p "$MINIMAL_WORKSPACE"
echo "# LLM Research Workspace - $(date)" > "$MINIMAL_WORKSPACE/README.md"
echo "Minimal workspace created: $MINIMAL_WORKSPACE"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Create output directory
mkdir -p "$SESSION_DIR"

# Initialize progress tracking
TOTAL_TASKS=10
COMPLETED=0
FAILED=0

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Multi-Agent Sequential Research${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Session: $TIMESTAMP"
echo "Output: $SESSION_DIR"
echo "Total Tasks: $TOTAL_TASKS"
echo ""

# Progress bar function
progress_bar() {
    local current=$1
    local total=$2
    local width=40
    local percentage=$((current * 100 / total))
    local filled=$((width * current / total))
    local empty=$((width - filled))

    printf "\r["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "] %d/%d (%d%%)" $current $total $percentage
}

# Task execution function
run_task() {
    local task_num=$1
    local model=$2
    local task_name=$3
    local prompt=$4

    echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Task $task_num/$TOTAL_TASKS: $task_name${NC}"
    echo -e "${BLUE}Model: $model${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    local output_file="$SESSION_DIR/task_${task_num}_${task_name// /_}.md"
    local start_time=$(date +%s)

    # OPTIMIZED: Run auggie with minimal workspace, session disabled, max-turns limited
    # This achieves 55-91x speedup (3.3s vs 180-300s per task)
    if auggie --print --quiet \
        --workspace-root "$MINIMAL_WORKSPACE" \
        --dont-save-session \
        --max-turns 1 \
        --model "$model" \
        "$prompt" 2>&1 | tee "$output_file"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        echo -e "\n${GREEN}✓ Completed in ${duration}s${NC}"
        echo -e "  Output: $output_file"

        # Add metadata header to output file
        {
            echo "# Task $task_num: $task_name"
            echo ""
            echo "**Model**: $model"
            echo "**Duration**: ${duration}s"
            echo "**Timestamp**: $(date -d @$start_time '+%Y-%m-%d %H:%M:%S')"
            echo ""
            echo "---"
            echo ""
            cat "$output_file"
        } > "${output_file}.tmp" && mv "${output_file}.tmp" "$output_file"

        ((COMPLETED++))
        return 0
    else
        echo -e "\n${RED}✗ Failed${NC}"
        ((FAILED++))
        return 1
    fi
}

# Define all 10 tasks
# Each task: run_task <num> <model> <name> <prompt>

# ==================== CPU Optimization Branch ====================

run_task 1 "sonnet4.5" "CPU-1_Hardware_Detection" \
"CPU-1: Hardware Detection Strategy

Design a detection strategy for auto-configuring llama.cpp on unknown server hardware.

Requirements:
1. List Linux commands/tools to detect: CPU cores, NUMA nodes, memory channels, cache sizes
2. Create decision tree: When to enable/disable NUMA based on socket count
3. Output format: JSON schema for hardware specs

Focus: Strategy and tooling approach, NOT implementation code.
Deliverable: Detection workflow diagram + decision matrix for NUMA configuration."

run_task 2 "sonnet4.5" "CPU-2_Thread_Allocation" \
"CPU-2: Thread Allocation Architecture

Design optimal thread allocation model for llama.cpp with 1TB+ RAM.

Requirements:
1. Formula for optimal threads based on memory bandwidth (not core count)
2. Strategy to avoid bandwidth saturation
3. Trade-offs: physical cores vs hyperthreads

Focus: Mathematical model and allocation patterns, NOT configuration scripts.
Deliverable: Thread count formula + allocation decision matrix."

run_task 3 "gpt5" "CPU-3_Detection_Script" \
"CPU-3: Hardware Detection Implementation

Create a Python script that detects server hardware for llama.cpp optimization.

Requirements:
1. Use lscpu, numactl, /proc/meminfo to gather hardware specs
2. Output JSON matching the schema from CPU-1
3. Handle edge cases: missing tools, no NUMA, etc.
4. Include error handling and fallbacks

Dependencies: Builds on CPU-1 strategy
Deliverable: Complete Python script (hw_detect.py) ready to run."

run_task 4 "gpt5" "CPU-4_Config_Generator" \
"CPU-4: llama.cpp Configuration Generator

Create a Python script that generates optimal llama-server configurations.

Requirements:
1. Input: Hardware JSON from CPU-3
2. Apply thread allocation model from CPU-2
3. Output: llama-server command with optimal flags (threads, context, NUMA binding)
4. Support multiple instances for multi-socket systems

Dependencies: Builds on CPU-2 model + CPU-3 output
Deliverable: Complete Python script (auto_config.py) with examples."

# ==================== RAG Implementation Branch ====================

run_task 5 "sonnet4.5" "RAG-1_Architecture" \
"RAG-1: RAG Architecture Pattern

Design RAG pattern for adaptive agent learning using codebase embeddings.

Context: Python autonomous agent system (HTN planning, multi-agent teams)
Goal: Agents learn from execution patterns to self-optimize

Requirements:
1. How to embed: entities, use cases, adapters (what granularity?)
2. Retrieval strategy: Semantic vs hybrid vs graph-based (pros/cons)
3. Context injection: Where in agent pipeline (TaskPlanner? TeamRouter?)
4. Data flow: Codebase → Embeddings → Retrieval → Agent Enhancement

Focus: Architecture patterns and data flow, NOT implementation.
Deliverable: RAG pattern diagram + retrieval strategy comparison + integration points."

run_task 6 "gpt5" "RAG-2_SurrealDB_Schema" \
"RAG-2: SurrealDB Schema Design

Design SurrealDB schema for storing codebase embeddings and execution patterns.

Requirements:
1. Tables: code_entities, execution_logs, agent_learnings, optimization_patterns
2. Vector fields for embeddings (specify dimensions)
3. Relationships: Code → Execution → Metrics → Learnings
4. SurrealQL queries for semantic search

Dependencies: Builds on RAG-1 architecture
Deliverable: Complete SurrealDB schema (init_schema.surql) + example queries."

run_task 7 "gpt5" "RAG-3_Embedding_Pipeline" \
"RAG-3: Embedding Pipeline Implementation

Create Python module for embedding codebase using sentence-transformers.

Requirements:
1. CodebaseIndexer class: Parse Python AST, extract functions/classes
2. EmbeddingPipeline class: Generate embeddings (all-MiniLM-L6-v2 default)
3. Batch processing support (64 items/batch)
4. Incremental updates (content hashing to skip unchanged code)

Dependencies: Builds on RAG-1 architecture
Deliverable: Complete Python module (src/adapters/rag/embedding_pipeline.py) + usage example."

run_task 8 "sonnet4.5" "RAG-4_Integration_Strategy" \
"RAG-4: RAG Integration Strategy

Design strategy for integrating RAG into existing TaskPlanner and TeamRouter.

Context: Existing codebase uses TaskCoordinator, TaskPlanner, TeamRouter
Goal: Inject retrieved codebase knowledge into agent prompts

Requirements:
1. Integration points: Where to call RAG retrieval? (before planning/routing)
2. Context window management: How to fit retrieved code in token limits?
3. Prompt engineering: How to format retrieved context for LLM?
4. Fallback strategy: What if retrieval fails or returns irrelevant results?

Dependencies: Builds on RAG-1 architecture + RAG-2 schema + RAG-3 pipeline
Deliverable: Integration architecture + prompt templates + error handling strategy."

run_task 9 "gpt5" "RAG-5_Adaptive_Learning" \
"RAG-5: Adaptive Learning Implementation

Create adaptive learning coordinator that captures execution patterns.

Requirements:
1. RAGTaskCoordinator class: Wraps existing TaskCoordinator
2. Capture patterns: Task → Agent → Result → Embedding → Store to SurrealDB
3. Learning queries: Retrieve successful patterns for similar tasks
4. Integration: Wire into orchestration pipeline

Dependencies: Builds on RAG-2 schema + RAG-3 pipeline + RAG-4 integration
Deliverable: Complete Python module (src/use_cases/rag_task_coordinator.py) + wiring guide."

# ==================== Final Integration ====================

run_task 10 "gpt5" "CPU-5_Benchmarking" \
"CPU-5: Benchmarking Suite

Create benchmarking suite for validating llama.cpp configuration.

Requirements:
1. Benchmark script: Test different thread counts, context sizes
2. Metrics: tokens/sec, latency (p50/p95/p99), memory usage
3. Comparison tool: Compare configurations side-by-side
4. Systemd service template for production deployment

Dependencies: Builds on CPU-3 + CPU-4
Deliverable: Complete benchmarking suite (scripts/benchmark_llama.sh) + systemd template."

# ==================== Summary ====================

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}  Execution Summary${NC}"
echo -e "${BLUE}========================================${NC}\n"

progress_bar $COMPLETED $TOTAL_TASKS
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tasks completed successfully!${NC}"
else
    echo -e "\n${YELLOW}⚠ Completed: $COMPLETED, Failed: $FAILED${NC}"
fi

echo -e "\n${BLUE}Output Directory:${NC}"
echo "  $SESSION_DIR"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Review outputs: cd $SESSION_DIR && ls -lh"
echo "  2. Synthesize into deployment guide"
echo "  3. Implement scripts from generated code"
echo ""

# Create index file
cat > "$SESSION_DIR/INDEX.md" << EOF
# Multi-Agent Research Session: $TIMESTAMP

## Summary

- **Total Tasks**: $TOTAL_TASKS
- **Completed**: $COMPLETED
- **Failed**: $FAILED
- **Success Rate**: $(( COMPLETED * 100 / TOTAL_TASKS ))%

## Tasks

### CPU Optimization Branch

1. [CPU-1: Hardware Detection Strategy](task_1_CPU-1_Hardware_Detection.md) - Model: sonnet4.5
2. [CPU-2: Thread Allocation Architecture](task_2_CPU-2_Thread_Allocation.md) - Model: sonnet4.5
3. [CPU-3: Hardware Detection Script](task_3_CPU-3_Detection_Script.md) - Model: gpt5
4. [CPU-4: Config Generator](task_4_CPU-4_Config_Generator.md) - Model: gpt5
5. [CPU-5: Benchmarking Suite](task_10_CPU-5_Benchmarking.md) - Model: gpt5

### RAG Implementation Branch

6. [RAG-1: Architecture Pattern](task_5_RAG-1_Architecture.md) - Model: sonnet4.5
7. [RAG-2: SurrealDB Schema](task_6_RAG-2_SurrealDB_Schema.md) - Model: gpt5
8. [RAG-3: Embedding Pipeline](task_7_RAG-3_Embedding_Pipeline.md) - Model: gpt5
9. [RAG-4: Integration Strategy](task_8_RAG-4_Integration_Strategy.md) - Model: sonnet4.5
10. [RAG-5: Adaptive Learning](task_9_RAG-5_Adaptive_Learning.md) - Model: gpt5

## Model Distribution

- **Sonnet 4.5**: 4 tasks (Architecture, Strategy, Design)
- **GPT-5**: 6 tasks (Implementation, Scripts, Code)

## Timeline

$(ls -1t task_*.md | while read f; do
    timestamp=$(grep "Timestamp:" "$f" 2>/dev/null | cut -d: -f2- | xargs)
    duration=$(grep "Duration:" "$f" 2>/dev/null | cut -d: -f2 | xargs)
    echo "- \$(basename \$f .md): \$timestamp (\$duration)"
done)

---

Generated by: run_multi_agent_sequential.sh
EOF

echo -e "${GREEN}✓ Index created: $SESSION_DIR/INDEX.md${NC}\n"
