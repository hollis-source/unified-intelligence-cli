#!/bin/bash
# Sequential Research: Baseline Architecture + LangGraph + Agent Metrics
# Uses proven minimal workspace pattern for 55-91x speedup
# Staggered execution across 2 models (Sonnet 4.5 + GPT-5)

set -e

# Configuration
OUTPUT_DIR="/home/ui-cli_jake/unified-intelligence-cli/docs"
TEMP_OUTPUT_DIR="/tmp/auggie_research_output"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# OPTIMIZATION: Create minimal workspace to avoid indexing delays
MINIMAL_WORKSPACE="/tmp/auggie_research_baseline"
mkdir -p "$MINIMAL_WORKSPACE"
mkdir -p "$TEMP_OUTPUT_DIR"
echo "# Research Workspace - $(date)" > "$MINIMAL_WORKSPACE/README.md"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Baseline Architecture Research${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Workspace: $MINIMAL_WORKSPACE"
echo "Output: $OUTPUT_DIR"
echo "Total Tasks: 3"
echo ""

# Task execution function
run_task() {
    local task_num=$1
    local model=$2
    local task_name=$3
    local output_file=$4
    local prompt=$5

    echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Task $task_num/3: $task_name${NC}"
    echo -e "${BLUE}Model: $model${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    local start_time=$(date +%s)

    # OPTIMIZED: Run auggie with minimal workspace
    if auggie --print --quiet \
        --workspace-root "$MINIMAL_WORKSPACE" \
        --dont-save-session \
        --model "$model" \
        "$prompt" 2>&1 | tee "$output_file"; then

        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        echo -e "\n${GREEN}✓ Completed in ${duration}s${NC}"
        echo -e "  Output: $output_file"

        # Add metadata header
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

        return 0
    else
        echo -e "\n${RED}✗ Failed${NC}"
        return 1
    fi
}

# ==================== Task 1: LangGraph Research ====================

run_task 1 "sonnet4.5" "LangGraph Integration Analysis" \
    "$TEMP_OUTPUT_DIR/LANGGRAPH_INTEGRATION_ANALYSIS.md" \
"Analyze LangGraph for integration into unified-intelligence-cli agent system.

CONTEXT:
We have a custom agent orchestration system using:
- Clean Architecture (entities, use cases, adapters, interfaces)
- Custom HTN (Hierarchical Task Network) DSL with category theory morphisms
- Team-based routing (though currently only 5 agents, not using teams yet)
- Multi-LLM support (Granite, OpenAI, Anthropic, Grok)

Current state: ~60% functionality, working but complex

RESEARCH QUESTIONS:
1. Can LangGraph be integrated as an adapter (preserving our Clean Architecture)?
2. Or does it require becoming the core (replacing our orchestration)?
3. How does LangGraph handle state management vs our current approach?
4. What does multi-agent coordination look like in LangGraph?
5. How do cycles/branches/human-in-loop work? (We need this)
6. Comparison: LangGraph vs our HTN/DSL approach - pros/cons
7. What would incremental migration look like? (We ship continuously)

OUTPUT FORMAT (markdown):
# LangGraph Integration Analysis

## Executive Summary
- Can it be an adapter? Yes/No/Partial
- Effort estimate: X days
- Risk level: Low/Medium/High

## Architecture Comparison
[Diagrams showing LangGraph vs current architecture]

## Integration Pattern
[Specific code showing how to integrate]

## Migration Path
[Incremental steps - we don't do big-bang migrations]

## Recommendation
[Data-driven recommendation with trade-offs]

IMPORTANT: Include code examples. Focus on practical integration, not theory."

# ==================== Task 2: Agent Metrics System ====================

run_task 2 "gpt5" "Agent Performance Measurement System" \
    "$TEMP_OUTPUT_DIR/AGENT_METRICS_SYSTEM.md" \
"Design agent performance measurement system for 5 specialist agents in unified-intelligence-cli.

CONTEXT:
Building 5 specialist agents:
1. Python Engineer - Code quality, refactoring, patterns
2. Software Architect - System design, Clean Architecture
3. Test Engineer - Unit, integration, E2E test generation
4. DevOps Engineer - CI/CD, deployment, monitoring
5. Research Analyst - Documentation, investigation, planning

Philosophy: Continuous improvement. Each agent starts at 20% baseline, improves weekly to 80%+.

REQUIREMENTS:
1. Define measurable metrics for each agent:
   - Task completion rate (%)
   - Output quality score (1-10, need scoring rubric)
   - Latency p95 (seconds)
   - Cost per task (tokens)
   - Specificity (% with code references like file:line)

2. Design test harness:
   - 20 real tasks per agent type (provide examples)
   - Automated scoring where possible
   - Human eval protocol for quality
   - Regression testing (don't break what works)

3. Create metrics tracking approach:
   - Track metrics over time
   - Show improvement trajectory (week-over-week)
   - Identify next optimization target (highest impact/lowest effort)

OUTPUT FORMAT (markdown with embedded code):
# Agent Performance Measurement System

## Metrics Definition
[Table with all metrics, formulas, targets]

## Scoring Rubrics
[Detailed rubrics for quality evaluation]

## Test Suite Design
[20 example tasks per agent type]

## Implementation Guide
[Python code snippets for measurement]

## Dashboard Concept
[How to visualize metrics and trends]

IMPORTANT: Make it actionable. We need to measure TODAY, not plan to measure."

# ==================== Task 3: Baseline Architecture Design ====================

run_task 3 "sonnet4.5" "Minimal Baseline Architecture" \
    "$TEMP_OUTPUT_DIR/BASELINE_ARCHITECTURE_DESIGN.md" \
"Design minimal baseline architecture for unified-intelligence-cli agent system.

CONTEXT:
Current system has grown complex:
- RAG (43% success, has bugs but architecture is sound)
- Category theory DSL (60% features used, rest is over-engineered)
- Team-based routing (0% used, only 5 agents so not needed yet)
- Hybrid orchestration (works but complex)

Philosophy: Strip to baseline, improve incrementally, measure continuously.

TASK:
Design minimal architecture that:
1. Keeps what works well:
   - Agent entity (clean abstraction)
   - Task entity (good model)
   - LLM provider adapters (Granite integration works great)
   - Basic orchestration (agents execute tasks)

2. Simplifies what's over-engineered:
   - RAG: Keep architecture, fix bugs iteratively (currently 43% → target 90%)
   - DSL: Reduce to actually-used subset (60% → 80% by removing unused)
   - Teams: Keep code but don't activate until 8+ agents
   - Orchestration: Simplify to single strategy (remove unused strategies)

3. Enables continuous improvement:
   - Clear component status (X% functionality)
   - Measurable improvement targets
   - Parallel development (no blocking dependencies)
   - Ship continuously

OUTPUT FORMAT (markdown + diagrams):
# Baseline Architecture Design

## Current State Analysis
[Component-by-component: what's working, what's not, usage data]

## Baseline Architecture
[Diagram showing minimal but functional system]

## Component Status Table
| Component | Current | Baseline Target | Keep/Simplify/Defer |
|-----------|---------|-----------------|---------------------|
| RAG | 43% | 90% | Keep + fix bug |
...

## Simplification Steps
[Incremental steps - each shippable independently]

## Success Metrics
[How do we know baseline is better than current?]

IMPORTANT: Baseline doesn't mean 'throw away'. It means 'simplify to working core, iterate from there'."

# ==================== Summary ====================

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}  Research Complete${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${GREEN}✓ All 3 tasks completed${NC}\n"

echo -e "${BLUE}Moving files to docs/${NC}"
mv "$TEMP_OUTPUT_DIR"/*.md "$OUTPUT_DIR/" 2>/dev/null || true

echo -e "${BLUE}Generated Files:${NC}"
echo "  1. $OUTPUT_DIR/LANGGRAPH_INTEGRATION_ANALYSIS.md"
echo "  2. $OUTPUT_DIR/AGENT_METRICS_SYSTEM.md"
echo "  3. $OUTPUT_DIR/BASELINE_ARCHITECTURE_DESIGN.md"
echo ""

echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Review outputs: cd $OUTPUT_DIR && ls -lh *.md"
echo "  2. Synthesize into action plan"
echo "  3. Apply continuous improvement philosophy"
echo ""

echo -e "${YELLOW}Cleanup:${NC}"
echo "  rm -rf $MINIMAL_WORKSPACE"
echo ""
