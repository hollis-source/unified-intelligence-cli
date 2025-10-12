#!/bin/bash
# Integration Test 1: Simple single-task goal
# Goal designed to complete successfully without environment preconditions

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
  --data-raw "USE NS project_builder; USE DB production; DELETE projects WHERE project_id = 'integration-test-1';" > /dev/null

# Activate virtual environment
source venv/bin/activate

echo "=========================================="
echo "INTEGRATION TEST 1: Simple Variable Creation"
echo "=========================================="
echo "Goal: Create a Python variable named 'message' with the string value 'Hello World'"
echo "Expected: Single task, no complex preconditions"
echo ""

# Run test
python -m src.project_builder.cli.command \
  "Create a Python variable named 'message' with the string value 'Hello World'" \
  --project-id integration-test-1 \
  --model grok \
  --parallel \
  --verbose \
  --output-dir projects/integration-tests/test-1

echo ""
echo "=========================================="
echo "TEST COMPLETED"
echo "=========================================="
