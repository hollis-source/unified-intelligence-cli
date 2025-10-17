#!/bin/bash
# Run specialist agent analysis with RAG enabled

echo "==================================="
echo "7-Agent Analysis with RAG"
echo "==================================="
echo ""
echo "Activating venv (sentence-transformers required)..."

# Activate venv
source venv/bin/activate

# Run analysis with venv Python
echo "Running analysis..."
python analyze_with_specialists.py

echo ""
echo "Analysis complete!"
