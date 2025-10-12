#!/bin/bash
set -e

# Explicitly set database configuration
# Reading from .env without sourcing (to avoid shell interpretation issues)
export PB_DB_TYPE=surrealdb
export PB_DB_HOST=localhost
export PB_DB_PORT=8001
export PB_DB_NAMESPACE=project_builder
export PB_DB_DATABASE=production
export PB_DB_USER=root
# Read password from .env (line 22, skip comments and empty lines)
export PB_DB_PASSWORD=$(grep '^PB_DB_PASSWORD=' .env | cut -d'=' -f2-)

# Read API keys
export XAI_API_KEY=$(grep '^XAI_API_KEY=' .env | cut -d'=' -f2-)

# Activate virtual environment
source venv/bin/activate

# Run project build with SurrealDB
python -m src.project_builder.cli.command \
  "Create a simple Python function that adds two numbers" \
  --project-id e2e-test-surrealdb \
  --model grok \
  --parallel \
  --verbose \
  --output-dir projects/e2e-test
