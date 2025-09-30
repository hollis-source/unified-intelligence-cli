#!/bin/bash
# Basic UI-CLI Task Examples
# 
# Prerequisites:
#   - ui-cli installed (pip install unified-intelligence-cli)
#   - XAI_API_KEY set in environment or .env file

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  UI-CLI Basic Task Examples"
echo "════════════════════════════════════════════════════════════════"
echo

# Check if API key is set
if [ -z "$XAI_API_KEY" ]; then
    echo "ERROR: XAI_API_KEY not set"
    echo "Set it with: export XAI_API_KEY=your_key_here"
    exit 1
fi

# Example 1: Simple single task
echo "Example 1: Simple Single Task"
echo "────────────────────────────────────────────────────────────────"
ui-cli "What are the 3 core principles of clean architecture?"
echo
echo

# Example 2: Multiple sequential tasks
echo "Example 2: Multiple Sequential Tasks"
echo "────────────────────────────────────────────────────────────────"
ui-cli \
  "Explain: What is dependency injection?" \
  "Benefits: List 3 key benefits" \
  "Example: Provide a Python code example"
echo
echo

# Example 3: Parallel execution for speed
echo "Example 3: Parallel Execution"
echo "────────────────────────────────────────────────────────────────"
ui-cli --parallel \
  "Define: What is SOLID?" \
  "Define: What is DRY?" \
  "Define: What is KISS?"
echo
echo

# Example 4: Code review task
echo "Example 4: Code Review"
echo "────────────────────────────────────────────────────────────────"
ui-cli "Review this Python function and suggest improvements:

def process_data(data):
    result = []
    for i in range(len(data)):
        if data[i] > 0:
            result.append(data[i] * 2)
    return result
"
echo
echo

# Example 5: Research and summarize
echo "Example 5: Research and Summarize"
echo "────────────────────────────────────────────────────────────────"
ui-cli \
  "Research: What is the difference between Docker and Kubernetes?" \
  "Summarize: Create a comparison table with pros/cons" \
  "Recommend: Which should a small startup use?"
echo
echo

# Example 6: Problem solving
echo "Example 6: Problem Solving"
echo "────────────────────────────────────────────────────────────────"
ui-cli \
  "Problem: My Python app is running slowly" \
  "Diagnose: List 5 common performance issues" \
  "Solutions: Suggest specific tools for each issue"
echo
echo

# Example 7: JSON output (for scripting)
echo "Example 7: JSON Output for Scripting"
echo "────────────────────────────────────────────────────────────────"
RESULT=$(ui-cli --output json "List 3 design patterns with brief descriptions")
echo "$RESULT" | python3 -m json.tool
echo
echo

echo "════════════════════════════════════════════════════════════════"
echo "  All examples completed!"
echo "════════════════════════════════════════════════════════════════"
