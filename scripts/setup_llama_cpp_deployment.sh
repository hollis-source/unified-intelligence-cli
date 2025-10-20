#!/bin/bash
# Setup script for llama.cpp deployment with IBM Granite 4.0-H Small
# Optimized for 1TB+ RAM systems

set -e

echo "=== llama.cpp Deployment Setup ==="

# 1. System optimization
echo "[1/7] Applying system optimizations..."
sudo sysctl -w vm.swappiness=10  # Reduce swapping
echo 3 | sudo tee /proc/sys/vm/drop_caches  # Clear cache
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/enabled  # Disable THP

# 2. Install dependencies
echo "[2/7] Installing dependencies..."
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    git \
    python3-dev \
    python3-pip \
    libopenblas-dev \
    pkg-config \
    numactl \
    htop

# 3. Clone and compile llama.cpp (optimized for CPU)
echo "[3/7] Compiling llama.cpp with AVX512 optimizations..."
cd /home/ui-cli_jake
if [ -d "llama.cpp" ]; then
    echo "llama.cpp directory exists, updating..."
    cd llama.cpp && git pull
else
    git clone https://github.com/ggml-org/llama.cpp
    cd llama.cpp
fi

mkdir -p build && cd build
cmake .. \
    -DGGML_NATIVE=ON \
    -DGGML_AVX512=ON \
    -DGGML_BLAS=ON \
    -DGGML_BLAS_VENDOR=OpenBLAS \
    -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release -j $(nproc)

# 4. Install Python bindings
echo "[4/7] Installing llama-cpp-python with OpenBLAS support..."
pip3 install llama-cpp-python[server] --upgrade \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

# 5. Create models directory
echo "[5/7] Creating models directory..."
mkdir -p /home/ui-cli_jake/llama_models
cd /home/ui-cli_jake/llama_models

# 6. Download IBM Granite 4.0-H Small GGUF (multiple quantizations for RAM optimization)
echo "[6/7] Downloading IBM Granite 4.0-H Small GGUF models..."
echo "This will download multiple quantization levels to leverage 1TB RAM"

# Install huggingface-cli if not present
pip3 install huggingface-hub[cli] --upgrade

# Download multiple quantizations for A/B testing and task routing
# Q4_K_M: ~19.5GB - Fast inference, good quality
huggingface-cli download ibm-granite/granite-4.0-h-small-GGUF \
    granite-4.0-h-small.Q4_K_M.gguf \
    --local-dir . --local-dir-use-symlinks False

# Q5_K_M: ~22.9GB - Better quality, still fast
huggingface-cli download ibm-granite/granite-4.0-h-small-GGUF \
    granite-4.0-h-small.Q5_K_M.gguf \
    --local-dir . --local-dir-use-symlinks False

# Q8_0: ~34.3GB - Excellent quality, slightly slower
huggingface-cli download ibm-granite/granite-4.0-h-small-GGUF \
    granite-4.0-h-small.Q8_0.gguf \
    --local-dir . --local-dir-use-symlinks False

# F16: ~64.4GB - Full precision (if needed for critical tasks)
# Uncomment if you want full precision:
# huggingface-cli download ibm-granite/granite-4.0-h-small-GGUF \
#     granite-4.0-h-small.f16.gguf \
#     --local-dir . --local-dir-use-symlinks False

echo "[7/7] Setup complete!"
echo ""
echo "Models downloaded to: /home/ui-cli_jake/llama_models/"
echo "  - granite-4.0-h-small.Q4_K_M.gguf (~19.5GB)"
echo "  - granite-4.0-h-small.Q5_K_M.gguf (~22.9GB)"
echo "  - granite-4.0-h-small.Q8_0.gguf (~34.3GB)"
echo ""
echo "Total RAM usage: ~77GB for 3 models (plenty of room in 1TB!)"
echo ""
echo "Next steps:"
echo "  1. Run: ./scripts/start_llama_servers.sh"
echo "  2. Test: python3 scripts/test_llama_endpoint.py"
