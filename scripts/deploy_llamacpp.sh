#!/usr/bin/env bash
#
# Llama.cpp Deployment Script for Tongyi-DeepResearch-30B
#
# Hardware: AMD EPYC 9454P (48 cores, 1.2TB RAM, AVX-512)
# Model: Tongyi-DeepResearch-30B-A3B-Q8_0 (32.5 GB)
# Target: Agentic coordinator for unified-intelligence-cli
#
# Usage: ./scripts/deploy_llamacpp.sh
# Estimated time: 10-20 minutes (mostly model download)

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
LLAMA_DIR="$HOME/llama.cpp"
MODEL_DIR="$HOME/models/tongyi"
MODEL_FILE="Alibaba-NLP_Tongyi-DeepResearch-30B-A3B-Q8_0.gguf"
MODEL_PATH="$MODEL_DIR/$MODEL_FILE"
HUGGINGFACE_REPO="bartowski/Alibaba-NLP_Tongyi-DeepResearch-30B-A3B-GGUF"

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

# Step 1: Check prerequisites
log_info "Step 1/5: Checking prerequisites..."

# Check if running on correct hardware
CPU_MODEL=$(lscpu | grep "Model name" | head -1)
if [[ $CPU_MODEL == *"EPYC"* ]]; then
    log_info "✓ AMD EPYC CPU detected"
else
    log_warn "Expected AMD EPYC CPU, found: $CPU_MODEL"
fi

# Check RAM
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM" -lt 32 ]; then
    log_error "Insufficient RAM: ${TOTAL_RAM}GB (need 32GB+ for Q8_0)"
    exit 1
fi
log_info "✓ Sufficient RAM: ${TOTAL_RAM}GB"

# Check disk space
AVAILABLE_SPACE=$(df -BG "$HOME" | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "$AVAILABLE_SPACE" -lt 40 ]; then
    log_error "Insufficient disk space: ${AVAILABLE_SPACE}GB (need 40GB+)"
    exit 1
fi
log_info "✓ Sufficient disk space: ${AVAILABLE_SPACE}GB"

# Step 2: Install/verify build dependencies
log_info "Step 2/5: Installing build dependencies..."

if ! check_command make; then
    log_warn "make not found, attempting to install build-essential..."
    if sudo apt update && sudo apt install -y build-essential cmake; then
        log_info "✓ Build dependencies installed"
    else
        log_error "Failed to install build dependencies. Please run:"
        log_error "  sudo apt update && sudo apt install -y build-essential cmake"
        exit 1
    fi
else
    log_info "✓ Build tools already installed"
fi

# Verify compiler
if check_command gcc; then
    GCC_VERSION=$(gcc --version | head -1)
    log_info "✓ GCC: $GCC_VERSION"
else
    log_error "GCC not found after installation"
    exit 1
fi

# Step 3: Build llama.cpp
log_info "Step 3/5: Building llama.cpp with AVX-512 optimization..."

if [ ! -d "$LLAMA_DIR" ]; then
    log_warn "llama.cpp directory not found at $LLAMA_DIR"
    log_info "Cloning llama.cpp repository..."
    git clone https://github.com/ggerganov/llama.cpp "$LLAMA_DIR"
fi

cd "$LLAMA_DIR"

# Check if already built
if [ -f "llama-cli" ] && [ -x "llama-cli" ]; then
    log_info "llama-cli already built, checking for updates..."
    git pull
fi

# Build with all cores
log_info "Building with 48 cores (this will take 2-3 minutes)..."
make clean
make -j48

# Verify AVX-512 support
if ./llama-cli --version 2>&1 | grep -q "AVX512 = 1"; then
    log_info "✓ llama.cpp built with AVX-512 support"
else
    log_warn "AVX-512 not detected in build (performance may be reduced)"
fi

# Create symlinks (optional, may need sudo)
if [ -w /usr/local/bin ]; then
    ln -sf "$LLAMA_DIR/llama-cli" /usr/local/bin/llama-cli 2>/dev/null && \
        log_info "✓ Created symlink: /usr/local/bin/llama-cli"
else
    log_warn "Cannot create symlink in /usr/local/bin (requires sudo)"
    log_info "You can run llama-cli from: $LLAMA_DIR/llama-cli"
fi

# Step 4: Install HuggingFace CLI
log_info "Step 4/5: Installing HuggingFace CLI..."

if ! check_command huggingface-cli; then
    log_info "Installing huggingface-hub..."
    # Ubuntu 24.04 PEP 668: Use --break-system-packages for user tools
    pip3 install --break-system-packages huggingface-hub
    export PATH="$HOME/.local/bin:$PATH"
fi

if check_command huggingface-cli; then
    HF_VERSION=$(huggingface-cli --version 2>&1 | head -1 || echo "unknown")
    log_info "✓ HuggingFace CLI: $HF_VERSION"
else
    log_error "Failed to install huggingface-cli"
    exit 1
fi

# Step 5: Download model
log_info "Step 5/5: Downloading Tongyi-DeepResearch-30B model..."

mkdir -p "$MODEL_DIR"

if [ -f "$MODEL_PATH" ]; then
    EXISTING_SIZE=$(stat -c%s "$MODEL_PATH" 2>/dev/null || stat -f%z "$MODEL_PATH" 2>/dev/null)
    EXPECTED_SIZE=32500000000  # ~32.5 GB
    if [ "$EXISTING_SIZE" -gt $((EXPECTED_SIZE - 1000000000)) ]; then
        log_info "✓ Model already downloaded: $MODEL_PATH"
        log_info "  Size: $(du -h "$MODEL_PATH" | cut -f1)"
    else
        log_warn "Incomplete model file detected, re-downloading..."
        rm -f "$MODEL_PATH"
    fi
fi

if [ ! -f "$MODEL_PATH" ]; then
    log_info "Downloading $MODEL_FILE (32.5 GB)..."
    log_info "This will take 5-15 minutes depending on connection speed..."

    huggingface-cli download "$HUGGINGFACE_REPO" \
        "$MODEL_FILE" \
        --local-dir "$MODEL_DIR" \
        --local-dir-use-symlinks False

    if [ -f "$MODEL_PATH" ]; then
        log_info "✓ Model downloaded: $MODEL_PATH"
        log_info "  Size: $(du -h "$MODEL_PATH" | cut -f1)"
    else
        log_error "Model download failed"
        exit 1
    fi
fi

# Step 6: Validation
log_info "Running validation tests..."

log_info "Test 1: Basic inference (256 tokens)..."
VALIDATION_OUTPUT=$("$LLAMA_DIR/llama-cli" \
    -m "$MODEL_PATH" \
    -p "You are a coordinator agent. Break down this task: Build REST API with auth" \
    -n 256 -c 4096 -t 48 --temp 0.7 2>&1)

if echo "$VALIDATION_OUTPUT" | grep -q "llama_print_timings"; then
    # Extract tokens/second
    TOKENS_PER_SEC=$(echo "$VALIDATION_OUTPUT" | grep "eval time" | awk '{print $(NF-1)}')
    log_info "✓ Inference successful: ~${TOKENS_PER_SEC} tokens/second"

    if [ "${TOKENS_PER_SEC%.*}" -lt 20 ]; then
        log_warn "Performance below target (20+ tok/s expected)"
    fi
else
    log_warn "Could not parse inference output"
fi

log_info "Test 2: Model loading time..."
START_TIME=$(date +%s)
"$LLAMA_DIR/llama-cli" -m "$MODEL_PATH" -p "test" -n 1 &>/dev/null
END_TIME=$(date +%s)
LOAD_TIME=$((END_TIME - START_TIME))
log_info "✓ Model loads in ${LOAD_TIME}s (target: <60s)"

# Summary
echo ""
echo "========================================"
echo "  DEPLOYMENT COMPLETE"
echo "========================================"
echo ""
log_info "llama.cpp: $LLAMA_DIR/llama-cli"
log_info "Model: $MODEL_PATH"
log_info "Size: $(du -h "$MODEL_PATH" | cut -f1)"
echo ""
log_info "Test command:"
echo "  $LLAMA_DIR/llama-cli -m $MODEL_PATH \\"
echo "    -p 'You are a coordinator agent. Plan: Build REST API' \\"
echo "    -n 256 -c 4096 -t 48"
echo ""
log_info "Next steps:"
echo "  1. Implement TongyiDeepResearchAdapter (src/adapters/llm/tongyi_adapter.py)"
echo "  2. Run user simulation tests"
echo "  3. Deploy to production"
echo ""
log_info "Deployment documentation: LLAMA_CPP_DEPLOYMENT_PLAN.md"
echo ""