#!/bin/bash
# Find unified-intelligence-cli on syd2 and deploy RAG metrics
#
# This script searches for the project directory and deploys there.
#
# Usage (run on syd2):
#   bash find_and_deploy_syd2.sh

set -e

echo "================================================================================"
echo "FIND AND DEPLOY RAG METRICS TO SYD2"
echo "================================================================================"
echo ""

echo "Step 1: Searching for unified-intelligence-cli directory..."
echo "--------------------------------------------------------------------------------"

# Common locations to check
SEARCH_PATHS=(
    "/root/unified-intelligence-cli"
    "/home/ubuntu/unified-intelligence-cli"
    "/home/*/unified-intelligence-cli"
    "/opt/unified-intelligence-cli"
    "/var/www/unified-intelligence-cli"
    "$HOME/unified-intelligence-cli"
)

PROJECT_DIR=""

# Check common locations first
for path in "${SEARCH_PATHS[@]}"; do
    if [ -d "$path" ] && [ -f "$path/scripts/rag_metrics_server.py" ]; then
        PROJECT_DIR="$path"
        echo "✅ Found project at: $PROJECT_DIR"
        break
    fi
done

# If not found, do a full search
if [ -z "$PROJECT_DIR" ]; then
    echo "⚠️  Not found in common locations, searching entire filesystem..."
    echo "   (This may take a minute...)"
    
    FOUND=$(find / -name "unified-intelligence-cli" -type d 2>/dev/null | head -1)
    
    if [ -n "$FOUND" ] && [ -f "$FOUND/scripts/rag_metrics_server.py" ]; then
        PROJECT_DIR="$FOUND"
        echo "✅ Found project at: $PROJECT_DIR"
    else
        echo "❌ Could not find unified-intelligence-cli directory"
        echo ""
        echo "Please specify the project directory manually:"
        echo "  export PROJECT_DIR=/path/to/unified-intelligence-cli"
        echo "  bash $0"
        exit 1
    fi
fi

echo ""
echo "Project directory: $PROJECT_DIR"
echo ""

# Navigate to project
cd "$PROJECT_DIR"

echo "Step 2: Verify project structure..."
echo "--------------------------------------------------------------------------------"

# Check for required files
REQUIRED_FILES=(
    "scripts/deploy_syd2_root.sh"
    "scripts/rag_metrics_server.py"
    "src/adapters/web/rag_metrics_server.py"
)

MISSING_FILES=()

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo "❌ Missing required files:"
    for file in "${MISSING_FILES[@]}"; do
        echo "   - $file"
    done
    echo ""
    echo "Please extract the deployment package first:"
    echo "  cd $PROJECT_DIR"
    echo "  tar -xzf /tmp/rag-metrics-deployment.tar.gz"
    exit 1
fi

echo "✅ All required files present"
echo ""

echo "Step 3: Running deployment..."
echo "--------------------------------------------------------------------------------"

# Make deployment script executable
chmod +x scripts/deploy_syd2_root.sh

# Run deployment
./scripts/deploy_syd2_root.sh

echo ""
echo "================================================================================"
echo "DEPLOYMENT COMPLETE"
echo "================================================================================"

