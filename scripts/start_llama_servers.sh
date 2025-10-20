#!/bin/bash
# Start multiple llama-server instances to leverage 1TB RAM
# Each model runs on different port for task-specific routing

set -e

MODELS_DIR="/home/ui-cli_jake/llama_models"
LLAMA_SERVER="/home/ui-cli_jake/llama.cpp/build/bin/llama-server"
LOG_DIR="/home/ui-cli_jake/unified-intelligence-cli/logs/llama_servers"

# Create log directory
mkdir -p "$LOG_DIR"

# Get physical core count (not hyperthreads)
PHYSICAL_CORES=$(lscpu | grep "Core(s) per socket" | awk '{print $4}')
SOCKETS=$(lscpu | grep "Socket(s)" | awk '{print $2}')
TOTAL_PHYSICAL_CORES=$((PHYSICAL_CORES * SOCKETS))

# Allocate threads per server (conservative for stability)
THREADS_PER_SERVER=$((TOTAL_PHYSICAL_CORES / 3))  # 3 servers = 1/3 cores each
BATCH_THREADS=$((TOTAL_PHYSICAL_CORES / 2))  # Batch can use more threads

echo "=== Starting llama-server instances ==="
echo "System: $TOTAL_PHYSICAL_CORES physical cores"
echo "Allocation: $THREADS_PER_SERVER threads per server, $BATCH_THREADS batch threads"
echo ""

# Check if servers are already running
if pgrep -f "llama-server.*granite" > /dev/null; then
    echo "Warning: llama-server instances already running!"
    echo "Run './scripts/stop_llama_servers.sh' first to restart"
    exit 1
fi

# Server 1: Granite Q5_K_M (Balanced - Default for most tasks)
# Port 8080 - General purpose, best quality/speed balance
echo "[1/3] Starting Granite Q5_K_M (Port 8080 - Default)..."
nohup "$LLAMA_SERVER" \
    --model "$MODELS_DIR/granite-4.0-h-small.Q5_K_M.gguf" \
    --host 0.0.0.0 \
    --port 8080 \
    --mlock \
    --flash-attn \
    --ctx-size 32768 \
    --threads $THREADS_PER_SERVER \
    --threads-batch $BATCH_THREADS \
    --parallel 4 \
    --cache-type-k q8_0 \
    --cache-type-v q8_0 \
    --metrics \
    --log-format json \
    > "$LOG_DIR/granite-q5-8080.log" 2>&1 &

echo "  PID: $!"
echo "  Log: $LOG_DIR/granite-q5-8080.log"
sleep 3

# Server 2: Granite Q4_K_M (Fast - For simple tasks, high throughput)
# Port 8081 - Fast inference for simple queries
echo "[2/3] Starting Granite Q4_K_M (Port 8081 - Fast)..."
nohup "$LLAMA_SERVER" \
    --model "$MODELS_DIR/granite-4.0-h-small.Q4_K_M.gguf" \
    --host 0.0.0.0 \
    --port 8081 \
    --mlock \
    --flash-attn \
    --ctx-size 16384 \
    --threads $THREADS_PER_SERVER \
    --threads-batch $BATCH_THREADS \
    --parallel 6 \
    --cache-type-k q8_0 \
    --cache-type-v q8_0 \
    --metrics \
    --log-format json \
    > "$LOG_DIR/granite-q4-8081.log" 2>&1 &

echo "  PID: $!"
echo "  Log: $LOG_DIR/granite-q4-8081.log"
sleep 3

# Server 3: Granite Q8_0 (High Quality - For complex reasoning, critical tasks)
# Port 8082 - Best quality for complex tasks
echo "[3/3] Starting Granite Q8_0 (Port 8082 - High Quality)..."
nohup "$LLAMA_SERVER" \
    --model "$MODELS_DIR/granite-4.0-h-small.Q8_0.gguf" \
    --host 0.0.0.0 \
    --port 8082 \
    --mlock \
    --flash-attn \
    --ctx-size 65536 \
    --threads $THREADS_PER_SERVER \
    --threads-batch $BATCH_THREADS \
    --parallel 2 \
    --cache-type-k q8_0 \
    --cache-type-v q8_0 \
    --metrics \
    --log-format json \
    > "$LOG_DIR/granite-q8-8082.log" 2>&1 &

echo "  PID: $!"
echo "  Log: $LOG_DIR/granite-q8-8082.log"
sleep 3

# Wait for servers to initialize
echo ""
echo "Waiting for servers to initialize (30 seconds)..."
sleep 30

# Health check
echo ""
echo "=== Health Check ==="
for port in 8080 8081 8082; do
    if curl -s http://localhost:$port/health > /dev/null; then
        echo "✓ Port $port: READY"
    else
        echo "✗ Port $port: NOT READY (check logs)"
    fi
done

echo ""
echo "=== Server Configuration ==="
echo "Port 8080: Granite Q5_K_M (~23GB RAM) - Default, balanced"
echo "Port 8081: Granite Q4_K_M (~19GB RAM) - Fast, simple tasks"
echo "Port 8082: Granite Q8_0 (~34GB RAM)   - High quality, complex tasks"
echo ""
echo "Total RAM usage: ~76GB (plenty of headroom in 1TB!)"
echo ""
echo "OpenAI-compatible endpoints:"
echo "  http://localhost:8080/v1/chat/completions"
echo "  http://localhost:8081/v1/chat/completions"
echo "  http://localhost:8082/v1/chat/completions"
echo ""
echo "Monitoring:"
echo "  tail -f $LOG_DIR/granite-q5-8080.log"
echo "  curl http://localhost:8080/metrics"
echo ""
echo "To stop servers: ./scripts/stop_llama_servers.sh"
