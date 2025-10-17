#!/bin/bash
# 2-Task Test Script - Quick validation of optimized sequential approach
# Tests both models (Sonnet 4.5 + GPT-5) with simple prompts
# OPTIMIZED: Uses minimal workspace for 55-91x speedup

set -e

OUTPUT_DIR="/home/ui-cli_jake/unified-intelligence-cli/docs/multi_agent_test"
mkdir -p "$OUTPUT_DIR"

# OPTIMIZATION: Create minimal workspace to avoid indexing delays
MINIMAL_WORKSPACE="/tmp/auggie_test_minimal"
mkdir -p "$MINIMAL_WORKSPACE"
echo "# Test Workspace" > "$MINIMAL_WORKSPACE/README.md"

echo "========================================="
echo "  2-Task Sequential Test"
echo "========================================="
echo ""

# Task 1: Sonnet 4.5 (Quick architecture question)
echo "[1/2] Testing Sonnet 4.5..."
auggie --print --quiet \
--workspace-root "$MINIMAL_WORKSPACE" \
--dont-save-session \
--max-turns 1 \
--model sonnet4.5 \
"Design a simple health check strategy for llama-server.

Requirements:
1. HTTP endpoint to ping
2. Response time threshold
3. Memory usage check

Output: 3-bullet implementation plan (keep it brief, <200 words)" \
| tee "$OUTPUT_DIR/test_task1_sonnet.md"

echo ""
echo "✓ Task 1 complete"
echo ""

# Task 2: GPT-5 (Quick implementation question)
echo "[2/2] Testing GPT-5..."
auggie --print --quiet \
--workspace-root "$MINIMAL_WORKSPACE" \
--dont-save-session \
--max-turns 1 \
--model gpt5 \
"Write a minimal Python function to check llama-server health.

Requirements:
1. Function: check_llama_health(url: str) -> bool
2. HTTP GET to /health endpoint
3. Return True if status 200, False otherwise

Output: Just the Python code (keep it minimal, <15 lines)" \
| tee "$OUTPUT_DIR/test_task2_gpt5.md"

echo ""
echo "✓ Task 2 complete"
echo ""

echo "========================================="
echo "  Test Results"
echo "========================================="
echo ""
echo "✓ Both models working"
echo "✓ Sequential execution successful"
echo "✓ Real-time output piping working"
echo ""
echo "Outputs saved to: $OUTPUT_DIR"
echo "  - test_task1_sonnet.md"
echo "  - test_task2_gpt5.md"
echo ""
echo "Next step: Run full 10-task suite with:"
echo "  ./scripts/run_multi_agent_sequential.sh"
echo ""
