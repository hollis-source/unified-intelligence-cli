#!/usr/bin/env bash
#
# Docker-based Llama.cpp Deployment for Tongyi-DeepResearch-30B
#
# Hardware: AMD EPYC 9454P (48 cores, 1.2TB RAM, AVX-512)
# Model: Tongyi-DeepResearch-30B-A3B-Q8_0 (32.5 GB)
# Target: Agentic coordinator for unified-intelligence-cli
#
# Prerequisites: Docker installed (run ./INSTALL_DOCKER.sh first)
# Usage: ./scripts/deploy_llamacpp_docker.sh
# Estimated time: 5-15 minutes (model download + image pull)

set -e
set -u

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
MODEL_DIR="$HOME/models/tongyi"
MODEL_FILE="Alibaba-NLP_Tongyi-DeepResearch-30B-A3B-Q8_0.gguf"
MODEL_PATH="$MODEL_DIR/$MODEL_FILE"
HUGGINGFACE_REPO="bartowski/Alibaba-NLP_Tongyi-DeepResearch-30B-A3B-GGUF"
CONTAINER_NAME="llama-cpp-server"
HOST_PORT=8080
CONTAINER_PORT=8080

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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

# Header
echo ""
echo "=========================================="
echo "  Llama.cpp Docker Deployment"
echo "=========================================="
echo ""
log_info "Model: Tongyi-DeepResearch-30B-Q8_0"
log_info "Container: $CONTAINER_NAME"
log_info "Port: $HOST_PORT"
echo ""

# Step 1: Verify Docker
log_step "Step 1/6: Verifying Docker installation..."

if ! check_command docker; then
    log_error "Docker not found. Please run: ./INSTALL_DOCKER.sh"
    exit 1
fi

# Check if user can run docker without sudo
if ! docker ps &>/dev/null; then
    log_error "Cannot run docker without sudo. Please:"
    log_error "  1. Run: ./INSTALL_DOCKER.sh"
    log_error "  2. Logout and login"
    log_error "  3. Verify: docker ps"
    exit 1
fi

log_info "✓ Docker ready: $(docker --version)"

# Step 2: Check system resources
log_step "Step 2/6: Checking system resources..."

TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM" -lt 32 ]; then
    log_error "Insufficient RAM: ${TOTAL_RAM}GB (need 32GB+ for Q8_0)"
    exit 1
fi
log_info "✓ RAM: ${TOTAL_RAM}GB"

AVAILABLE_SPACE=$(df -BG "$HOME" | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "$AVAILABLE_SPACE" -lt 40 ]; then
    log_error "Insufficient disk space: ${AVAILABLE_SPACE}GB (need 40GB+)"
    exit 1
fi
log_info "✓ Disk space: ${AVAILABLE_SPACE}GB available"

# Step 3: Install HuggingFace CLI (if needed)
log_step "Step 3/6: Installing HuggingFace CLI..."

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

# Step 4: Download model
log_step "Step 4/6: Downloading model..."

mkdir -p "$MODEL_DIR"

if [ -f "$MODEL_PATH" ]; then
    EXISTING_SIZE=$(stat -c%s "$MODEL_PATH" 2>/dev/null || stat -f%z "$MODEL_PATH" 2>/dev/null)
    EXPECTED_SIZE=32500000000  # ~32.5 GB
    if [ "$EXISTING_SIZE" -gt $((EXPECTED_SIZE - 1000000000)) ]; then
        log_info "✓ Model already downloaded: $MODEL_PATH"
        log_info "  Size: $(du -h "$MODEL_PATH" | cut -f1)"
    else
        log_warn "Incomplete model file, re-downloading..."
        rm -f "$MODEL_PATH"
    fi
fi

if [ ! -f "$MODEL_PATH" ]; then
    log_info "Downloading $MODEL_FILE (32.5 GB)..."
    log_info "This may take 5-15 minutes depending on connection..."

    huggingface-cli download "$HUGGINGFACE_REPO" \
        "$MODEL_FILE" \
        --local-dir "$MODEL_DIR" \
        --local-dir-use-symlinks False

    if [ -f "$MODEL_PATH" ]; then
        log_info "✓ Model downloaded: $(du -h "$MODEL_PATH" | cut -f1)"
    else
        log_error "Model download failed"
        exit 1
    fi
fi

# Step 5: Pull llama.cpp Docker image
log_step "Step 5/6: Pulling llama.cpp Docker image..."

log_info "Pulling ghcr.io/ggerganov/llama.cpp:server-cuda..."
if docker pull ghcr.io/ggerganov/llama.cpp:server-cuda; then
    log_info "✓ Docker image pulled"
else
    log_warn "CUDA image failed, trying CPU-only image..."
    docker pull ghcr.io/ggerganov/llama.cpp:server
    log_info "✓ CPU image pulled"
fi

# Step 6: Start llama.cpp server container
log_step "Step 6/6: Starting llama.cpp server..."

# Stop existing container if running
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log_info "Stopping existing container..."
    docker stop "$CONTAINER_NAME" || true
    docker rm "$CONTAINER_NAME" || true
fi

log_info "Starting container: $CONTAINER_NAME"
log_info "Port mapping: localhost:$HOST_PORT -> container:$CONTAINER_PORT"

docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$HOST_PORT:$CONTAINER_PORT" \
    -v "$MODEL_DIR:/models" \
    --cpus="48" \
    --memory="128g" \
    ghcr.io/ggerganov/llama.cpp:server-cuda \
    -m "/models/$MODEL_FILE" \
    -c 8192 \
    -t 48 \
    --host 0.0.0.0 \
    --port $CONTAINER_PORT \
    || docker run -d \
        --name "$CONTAINER_NAME" \
        -p "$HOST_PORT:$CONTAINER_PORT" \
        -v "$MODEL_DIR:/models" \
        --cpus="48" \
        --memory="128g" \
        ghcr.io/ggerganov/llama.cpp:server \
        -m "/models/$MODEL_FILE" \
        -c 8192 \
        -t 48 \
        --host 0.0.0.0 \
        --port $CONTAINER_PORT

# Wait for server to start
log_info "Waiting for server to start..."
sleep 5

# Check if container is running
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log_info "✓ Container running"
else
    log_error "Container failed to start. Check logs:"
    log_error "  docker logs $CONTAINER_NAME"
    exit 1
fi

# Validation
log_step "Running validation tests..."

log_info "Test 1: Health check..."
if curl -s http://localhost:$HOST_PORT/health | grep -q "ok"; then
    log_info "✓ Server responding"
else
    log_warn "Health check endpoint not available (may not be implemented)"
fi

log_info "Test 2: Inference test (this may take 30-60s for first load)..."
RESPONSE=$(curl -s http://localhost:$HOST_PORT/completion \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "You are a coordinator agent. Plan: Build REST API",
        "n_predict": 128,
        "temperature": 0.7
    }' || echo "ERROR")

if echo "$RESPONSE" | grep -q "content"; then
    log_info "✓ Inference successful"
    TOKEN_COUNT=$(echo "$RESPONSE" | grep -o '"tokens_predicted":[0-9]*' | grep -o '[0-9]*' || echo "unknown")
    log_info "  Generated tokens: $TOKEN_COUNT"
else
    log_warn "Inference test inconclusive. Check manually:"
    log_warn "  curl http://localhost:$HOST_PORT/completion -H 'Content-Type: application/json' -d '{\"prompt\":\"test\",\"n_predict\":10}'"
fi

# Summary
echo ""
echo "=========================================="
echo "  DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
log_info "Container: $CONTAINER_NAME (running)"
log_info "API: http://localhost:$HOST_PORT"
log_info "Model: $MODEL_FILE ($(du -h "$MODEL_PATH" | cut -f1))"
echo ""
log_info "Useful commands:"
echo "  # Check status"
echo "  docker ps"
echo ""
echo "  # View logs"
echo "  docker logs $CONTAINER_NAME -f"
echo ""
echo "  # Test inference"
echo "  curl http://localhost:$HOST_PORT/completion -H 'Content-Type: application/json' \\"
echo "    -d '{\"prompt\": \"You are a coordinator. Plan: Build REST API\", \"n_predict\": 256}'"
echo ""
echo "  # Stop server"
echo "  docker stop $CONTAINER_NAME"
echo ""
echo "  # Start server"
echo "  docker start $CONTAINER_NAME"
echo ""
echo "  # Remove container"
echo "  docker rm -f $CONTAINER_NAME"
echo ""
log_info "Next steps:"
echo "  1. Implement TongyiDeepResearchAdapter with HTTP client"
echo "  2. Point to http://localhost:$HOST_PORT/completion"
echo "  3. Run integration tests"
echo ""
log_info "API Documentation: https://github.com/ggerganov/llama.cpp/tree/master/examples/server"
echo ""