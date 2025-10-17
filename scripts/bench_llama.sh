#!/usr/bin/env bash
# A/B thread-count benchmarking wrapper for llama-server.
# Requires: scripts/bench_client.py and a runnable llama-server command template.
# Example:
#   ./scripts/bench_llama.sh \
#     -H http://127.0.0.1:8080 \
#     -p "Write a short paragraph about NUMA." \
#     -n 128 -r 50 -c 8 \
#     -t 16,32,48,64 \
#     -C "numactl --cpunodebind=0 --membind=0 llama-server -m /models/llama.gguf -t {THREADS} --threads-batch 8 --parallel 2 -c 8192 -b 512 --ubatch 128 --host 0.0.0.0 --port 8080 --no-warmup"
set -euo pipefail

HOST=http://127.0.0.1:8080
PROMPT="Benchmarking llama-server"
NPRED=128
REQUESTS=50
CONCURRENCY=8
THREADS_LIST="16,32,64"
CMD_TEMPLATE=""
OUT_CSV="bench_results.csv"

while getopts ":H:p:n:r:c:t:C:o:" opt; do
  case $opt in
    H) HOST="$OPTARG" ;;
    p) PROMPT="$OPTARG" ;;
    n) NPRED="$OPTARG" ;;
    r) REQUESTS="$OPTARG" ;;
    c) CONCURRENCY="$OPTARG" ;;
    t) THREADS_LIST="$OPTARG" ;;
    C) CMD_TEMPLATE="$OPTARG" ;;
    o) OUT_CSV="$OPTARG" ;;
    *) echo "Unknown option" >&2; exit 2 ;;
  esac
done

if [[ -z "$CMD_TEMPLATE" ]]; then
  echo "ERROR: Provide -C command template with {THREADS} placeholder" >&2
  exit 1
fi

echo "threads,ok,errors,lat_p50,lat_p95,lat_p99,tps_avg" > "$OUT_CSV"

for T in ${THREADS_LIST//,/ } ; do
  echo "\n=== Testing threads=$T ===" >&2
  CMD=${CMD_TEMPLATE//\{THREADS\}/$T}
  # Start server in background
  bash -c "$CMD" >/tmp/llama_server_${T}.log 2>&1 &
  PID=$!
  # Wait for readiness
  for i in {1..60}; do
    if curl -fsS "$HOST/health" >/dev/null 2>&1 || curl -fsS "$HOST/" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  # Run client
  RES=$(python3 scripts/bench_client.py --url "$HOST" --prompt "$PROMPT" --n-predict "$NPRED" --requests "$REQUESTS" --concurrency "$CONCURRENCY")
  OK=$(echo "$RES" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["ok"])')
  ERR=$(echo "$RES" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["errors"])')
  P50=$(echo "$RES" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["latency_s"]["p50"])')
  P95=$(echo "$RES" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["latency_s"]["p95"])')
  P99=$(echo "$RES" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["latency_s"]["p99"])')
  TPS=$(echo "$RES" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["tokens_sec"]["avg"])')
  echo "$T,$OK,$ERR,$P50,$P95,$P99,$TPS" >> "$OUT_CSV"
  # Stop server
  kill $PID || true
  wait $PID 2>/dev/null || true
  sleep 2
done

echo "Results written to $OUT_CSV" >&2

