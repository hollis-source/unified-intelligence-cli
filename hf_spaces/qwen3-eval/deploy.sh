#!/bin/bash
# Quick deployment script for ZeroGPU Space

set -e

echo "🚀 Deploying Qwen3-8B Evaluation to HuggingFace ZeroGPU"
echo ""

# Check HF CLI
if ! command -v huggingface-cli &> /dev/null; then
    echo "❌ huggingface-cli not found. Installing..."
    pip install huggingface_hub
fi

# Check login
if ! huggingface-cli whoami &> /dev/null; then
    echo "🔑 Please login to HuggingFace:"
    huggingface-cli login
fi

# Get username
USERNAME=$(huggingface-cli whoami | grep "username:" | awk '{print $2}')
echo "✓ Logged in as: $USERNAME"

# Prompt for Space name
read -p "Space name [qwen3-eval]: " SPACE_NAME
SPACE_NAME=${SPACE_NAME:-qwen3-eval}

SPACE_URL="https://huggingface.co/spaces/$USERNAME/$SPACE_NAME"

echo ""
echo "📦 Space details:"
echo "  Owner: $USERNAME"
echo "  Name: $SPACE_NAME"
echo "  URL: $SPACE_URL"
echo ""

# Check if Space exists
if huggingface-cli space list | grep -q "$SPACE_NAME"; then
    echo "⚠️  Space already exists: $SPACE_URL"
    read -p "Continue and update existing Space? [y/N]: " CONTINUE
    if [[ ! $CONTINUE =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
else
    echo "📝 Creating new Space..."
    # Note: huggingface-cli create-space doesn't support --space-hardware yet
    # User must set ZeroGPU in web UI
    echo ""
    echo "⚠️  Please create the Space manually:"
    echo "  1. Go to: https://huggingface.co/new-space"
    echo "  2. Name: $SPACE_NAME"
    echo "  3. SDK: Gradio"
    echo "  4. Hardware: ZeroGPU (Nvidia H200)"
    echo "  5. Click 'Create Space'"
    echo ""
    read -p "Press Enter when Space is created..."
fi

# Clone or update repo
if [ -d ".git" ]; then
    echo "✓ Git repository already initialized"
else
    echo "🔧 Initializing git repository..."
    git init
fi

# Set remote
if git remote get-url origin &> /dev/null; then
    echo "✓ Remote 'origin' already set"
    git remote set-url origin "https://huggingface.co/spaces/$USERNAME/$SPACE_NAME"
else
    git remote add origin "https://huggingface.co/spaces/$USERNAME/$SPACE_NAME"
fi

echo "✓ Remote: https://huggingface.co/spaces/$USERNAME/$SPACE_NAME"

# Stage files
echo ""
echo "📋 Staging files..."
git add app.py requirements.txt README.md .gitattributes test_sample.jsonl DEPLOYMENT.md
git status --short

# Commit
echo ""
read -p "Commit message [Deploy ZeroGPU evaluation Space]: " COMMIT_MSG
COMMIT_MSG=${COMMIT_MSG:-Deploy ZeroGPU evaluation Space}

git commit -m "$COMMIT_MSG" || echo "No changes to commit"

# Push
echo ""
echo "🚀 Pushing to HuggingFace..."
git push -u origin main

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Space URL: $SPACE_URL"
echo ""
echo "Next steps:"
echo "  1. Wait for Space to build (~2-3 minutes)"
echo "  2. Go to $SPACE_URL"
echo "  3. Paste test data and run evaluation"
echo "  4. View results in real-time!"
echo ""
echo "📖 For detailed instructions, see DEPLOYMENT.md"
