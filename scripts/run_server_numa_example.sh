#!/usr/bin/env bash
# Example: start llama.cpp server with NUMA pinning (single socket/node)
# Usage:
#   NODE=0 PORT=8090 ./scripts/run_server_numa_example.sh
# Requires: numactl installed; adjust -t/-b/-c and model path as needed.
set -euo pipefail
NODE=${NODE:-0}
PORT=${PORT:-8090}
ARGS_FILE=${ARGS_FILE:-server_cpu_optimized.args}
if ! command -v numactl >/dev/null 2>&1; then
  echo "numactl not found; please install or run without NUMA binding" >&2
  exit 1
fi
export LLAMA_BLAS=${LLAMA_BLAS:-1}
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-40}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-40}
export OMP_PROC_BIND=${OMP_PROC_BIND:-TRUE}
export OMP_PLACES=${OMP_PLACES:-cores}
set -x
ARGS=$(awk 'BEGIN{ORS=" ";} /^[[:space:]]*-/ {gsub(/\r/," "); print $0}' "${ARGS_FILE}")
numactl --cpunodebind=${NODE} --membind=${NODE} \
  llama-server ${ARGS} --host 127.0.0.1 --port ${PORT}

