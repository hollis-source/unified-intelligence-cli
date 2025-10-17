#!/usr/bin/env bash
set -euo pipefail
# Benchmark local OpenAI-compatible Granite endpoint(s) for TTFT and tokens/sec
# Requires: python3 (requests)
# Usage:
#   scripts/benchmark_local.sh [--endpoint URL] [--label NAME]
# Output: prints metrics and appends CSV to metrics/llama_bench.csv

ENDPOINT="http://localhost:8080/v1"
LABEL="run"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --endpoint) ENDPOINT="$2"; shift 2 ;;
    --label) LABEL="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

python3 scripts/benchmark_local.py --endpoint "$ENDPOINT" --label "$LABEL"

