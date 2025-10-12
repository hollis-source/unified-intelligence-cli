#!/usr/bin/env bash
#
# Install build tools required for llama.cpp compilation
# This is the ONLY command that requires sudo
#
# Run this once: ./INSTALL_BUILD_TOOLS.sh
# Then deployment can proceed without sudo
#

set -e

echo "================================"
echo "Installing Build Tools"
echo "================================"
echo ""
echo "This will install:"
echo "  - build-essential (gcc, g++, make)"
echo "  - cmake"
echo "  - python3-pip (for HuggingFace CLI)"
echo ""
echo "After this, no more sudo needed!"
echo ""

sudo apt update
sudo apt install -y build-essential cmake python3-pip

echo ""
echo "✓ Build tools installed!"
echo ""
echo "Verify installation:"
gcc --version
make --version
cmake --version

echo ""
echo "Now run: ./scripts/deploy_llamacpp.sh"
echo ""