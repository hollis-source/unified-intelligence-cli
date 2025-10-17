#!/usr/bin/env bash
set -euo pipefail
# Quick L2 throughput confirmation for CPU-only Granite Q5_K_M
# - Runs concurrency level 2 for small and medium prompts
# - Appends results to metrics/llama_bench_load.csv via scripts/benchmark_load.py
# - Prints acceptance vs single-stream baseline (metrics/llama_bench.csv), if available

ENDPOINT="${1:-http://127.0.0.1:8080/v1}"
LABEL_PREFIX="${LABEL_PREFIX:-q5-numa}"
DURATION="${DURATION_SECONDS:-60}"
WARMUP="${WARMUP_SECONDS:-10}"
CSV="metrics/llama_bench_load.csv"
PROMPTS=(small medium)

if [[ ! -f scripts/benchmark_load.py ]]; then
  echo "ERROR: scripts/benchmark_load.py not found" >&2
  exit 1
fi

run_one() {
  local prompt="$1"
  local label="${LABEL_PREFIX}-${prompt}"
  echo "Running ${prompt} @ L2 for ${DURATION}s (warmup ${WARMUP}s) on ${ENDPOINT} ..." >&2
  ./scripts/benchmark_load.py \
    --endpoint "${ENDPOINT}" \
    --label "${label}" \
    --concurrency-levels 2 \
    --duration-seconds "${DURATION}" \
    --warmup-seconds "${WARMUP}" \
    --prompt-set "${prompt}" \
    --csv "${CSV}"

  # Pull the last matching row for label/endpoint/level=2
  local last
  last=$(awk -F, -v LBL="${label}" -v EP="${ENDPOINT}" '($2==LBL && $3==EP && $7==2){print $0}' "${CSV}" | tail -n 1)
  if [[ -z "${last}" ]]; then
    echo "WARN: no matching row found for ${label} on ${ENDPOINT}" >&2
    return 0
  fi
  # CSV columns: date,label,endpoint,model,quant,prompt,level,ttft_p50_ms,ttft_p95_ms,req_s,tok_s_avg,tok_s_agg,err_rate,cpu_pct,rss_mb
  IFS="," read -r _date _label _endpoint _model _quant _prompt _level p50 p95 req_s tok_avg tok_agg err_rate cpu_pct rss_mb <<<"${last}"
  echo "Result: ${_prompt}@L${_level} tok/s_agg=${tok_agg} err%=${err_rate} p95=${p95} ms" >&2

  # Baseline single-stream tok/s from metrics/llama_bench.csv (last row by prompt)
  local baseline_ts
  baseline_ts=$(awk -F, -v P="${_prompt}" '($5==P){ts=$9} END{if (ts!="") print ts;}' metrics/llama_bench.csv 2>/dev/null || true)

  if [[ -n "${baseline_ts:-}" ]]; then
    # Acceptance: err% < 1% and tok/s_agg >= baseline
    awk -v tok_agg="${tok_agg}" -v err="${err_rate}" -v base="${baseline_ts}" -v label="${label}" 'BEGIN {
      pass = (err+0.0 < 0.01) && (tok_agg+0.0 >= base+0.0);
      status = pass ? "PASS" : "FAIL";
      printf("Acceptance: %s | tok/s_agg %.2f vs baseline %.2f | err%% %.2f\n", status, tok_agg, base, err*100);
    }'
  else
    echo "Note: baseline not found; skipped acceptance compare" >&2
  fi
}

for p in "${PROMPTS[@]}"; do
  run_one "$p"
  echo "---" >&2
done

