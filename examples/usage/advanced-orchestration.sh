#!/bin/bash
# Advanced UI-CLI Orchestration Examples
#
# Demonstrates complex multi-task workflows and patterns

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  UI-CLI Advanced Orchestration Examples"
echo "════════════════════════════════════════════════════════════════"
echo

# Check if API key is set
if [ -z "$XAI_API_KEY" ]; then
    echo "ERROR: XAI_API_KEY not set"
    exit 1
fi

# Pattern 1: Analysis → Decision → Action
echo "Pattern 1: Analysis → Decision → Action Pipeline"
echo "────────────────────────────────────────────────────────────────"
ui-cli \
  "Analyze: Current state of microservices architecture trends" \
  "Evaluate: Pros and cons for a Python web application" \
  "Decide: Should we use microservices or monolith? Provide clear recommendation" \
  "Plan: If microservices, outline implementation steps"
echo
echo

# Pattern 2: Parallel research with synthesis
echo "Pattern 2: Parallel Research → Synthesis"
echo "────────────────────────────────────────────────────────────────"
ui-cli --parallel \
  "Research A: Investigate Redis caching strategies" \
  "Research B: Investigate Memcached performance" \
  "Research C: Investigate in-memory Python caching"

echo "Now synthesizing findings..."
ui-cli "Synthesize: Compare Redis, Memcached, and in-memory caching. Create decision matrix."
echo
echo

# Pattern 3: Iterative refinement
echo "Pattern 3: Iterative Refinement"
echo "────────────────────────────────────────────────────────────────"
ui-cli \
  "Draft: Write a Python function for rate limiting" \
  "Review: Identify issues in the draft" \
  "Refactor: Apply SOLID principles to improve the code" \
  "Test: Suggest unit tests for the refactored code"
echo
echo

# Pattern 4: Multi-perspective analysis
echo "Pattern 4: Multi-Perspective Analysis"
echo "────────────────────────────────────────────────────────────────"
ui-cli --parallel \
  "Security: Analyze security implications of JWT authentication" \
  "Performance: Analyze performance characteristics of JWT" \
  "Maintainability: Analyze code maintainability with JWT" \
  "Scalability: Analyze scalability considerations for JWT"
echo
echo

# Pattern 5: Error handling workflow
echo "Pattern 5: Error Handling and Recovery Workflow"
echo "────────────────────────────────────────────────────────────────"
RESULT=$(ui-cli "Attempt: Analyze a non-existent technology called 'QuantumFlux'" 2>&1) || {
    echo "Task failed, analyzing failure..."
    ui-cli "Debug: Why might an AI fail to analyze 'QuantumFlux'? Suggest alternatives."
}
echo
echo

# Pattern 6: Conditional execution based on output
echo "Pattern 6: Conditional Execution"
echo "────────────────────────────────────────────────────────────────"
SECURITY_SCORE=$(ui-cli --output json "Rate security of storing passwords in plain text (1-10)" | grep -o '"score":[0-9]*' || echo "0")

if [ "$SECURITY_SCORE" -lt 5 ]; then
    echo "Low security score detected, requesting recommendations..."
    ui-cli "Recommend: Best practices for password storage in Python"
fi
echo
echo

# Pattern 7: Batch processing
echo "Pattern 7: Batch Processing Multiple Files"
echo "────────────────────────────────────────────────────────────────"
FILES=("module1.py" "module2.py" "module3.py")

for file in "${FILES[@]}"; do
    echo "Analyzing $file..."
    ui-cli "Review: Analyze $file for code quality (simulated review)"
done
echo
echo

# Pattern 8: Chained tasks with context preservation
echo "Pattern 8: Context-Aware Task Chain"
echo "────────────────────────────────────────────────────────────────"
ui-cli \
  "Step 1: Design a RESTful API for user management" \
  "Step 2: Based on Step 1, identify required database tables" \
  "Step 3: Based on Step 2, write SQLAlchemy models" \
  "Step 4: Based on Step 3, create FastAPI endpoints"
echo
echo

# Pattern 9: A/B comparison
echo "Pattern 9: A/B Comparison and Recommendation"
echo "────────────────────────────────────────────────────────────────"
ui-cli --parallel \
  "Option A: Explain FastAPI framework with pros/cons" \
  "Option B: Explain Flask framework with pros/cons"

ui-cli "Compare: Create side-by-side comparison of FastAPI vs Flask. Recommend one for a new project."
echo
echo

# Pattern 10: Comprehensive project analysis
echo "Pattern 10: Comprehensive Project Analysis"
echo "────────────────────────────────────────────────────────────────"
ui-cli \
  "Architecture: Analyze clean architecture principles" \
  "Testing: Suggest testing strategy (unit, integration, e2e)" \
  "CI/CD: Recommend CI/CD pipeline setup" \
  "Documentation: Outline documentation structure" \
  "Deployment: Suggest deployment strategy" \
  "Summary: Create executive summary of all recommendations"
echo
echo

echo "════════════════════════════════════════════════════════════════"
echo "  Advanced orchestration examples completed!"
echo "════════════════════════════════════════════════════════════════"
