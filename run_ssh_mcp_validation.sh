#!/bin/bash
# SSH + Project Builder Validation Test
# Tests remote codebase access via Paramiko and improvement generation

set -e

echo "========================================="
echo "SSH + Project Builder Validation"
echo "========================================="
echo ""
echo "Target: Dad's codebase at syd2:/opt/grokmonster/cna-dad-release-v1.0"
echo "Goal: Fix bare except blocks in db_status.py"
echo ""

# Activate venv and run Project Builder with SSH integration
source venv/bin/activate && python -m src.project_builder.cli.command \
  "Read the file /opt/grokmonster/cna-dad-release-v1.0/src/services/db_status.py from the remote server and fix all bare except blocks by adding specific exception types and logging. Generate an improved version of the file." \
  --project-id ssh-mcp-validation-1 \
  --model qwen3_hf_inference \
  --remote-host root@syd2.jacobhollis.com \
  --verbose

echo ""
echo "========================================="
echo "Validation Complete"
echo "========================================="
echo ""
echo "Check projects/ssh-mcp-validation-1/ for generated improvements"
