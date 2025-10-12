#!/bin/bash
# Integration Test 2: Multi-task goal with artifact generation
# Goal designed to complete successfully and generate multiple artifacts

set -e

# Load environment
export PB_DB_TYPE=surrealdb
export PB_DB_HOST=localhost
export PB_DB_PORT=8001
export PB_DB_NAMESPACE=project_builder
export PB_DB_DATABASE=production
export PB_DB_USER=root
export PB_DB_PASSWORD=$(grep '^PB_DB_PASSWORD=' .env | cut -d'=' -f2-)
export XAI_API_KEY=$(grep '^XAI_API_KEY=' .env | cut -d'=' -f2-)

# Clean up previous test
echo "Cleaning up previous test..."
curl -s -X POST "http://localhost:8001/sql" \
  --user "root:${PB_DB_PASSWORD}" \
  -H "Accept: application/json" \
  --data-raw "USE NS project_builder; USE DB production; DELETE projects WHERE project_id = 'integration-test-2';" > /dev/null

# Activate virtual environment
source venv/bin/activate

echo "=========================================="
echo "INTEGRATION TEST 2: Multi-Task Workflow"
echo "=========================================="
echo "Goal: Write Python code that defines three constants: PI=3.14159, E=2.71828, and GOLDEN_RATIO=1.61803"
echo "Expected: Multiple tasks, artifact generation, state accumulation"
echo ""

# Run test
python -m src.project_builder.cli.command \
  "Write Python code that defines three constants: PI=3.14159, E=2.71828, and GOLDEN_RATIO=1.61803" \
  --project-id integration-test-2 \
  --model grok \
  --parallel \
  --verbose \
  --output-dir projects/integration-tests/test-2

echo ""
echo "=========================================="
echo "TEST COMPLETED"
echo "=========================================="
