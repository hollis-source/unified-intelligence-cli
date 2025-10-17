# CPU-only Granite Inference Runbook (Q5_K_M)

Scope
- CPU-only llama.cpp serving (-ngl 0) for Granite 4.x h-small Q5_K_M
- OpenAI-compatible API; one server active at a time
- Append-only metrics and report updates

Model
- Path: /home/ui-cli_jake/unified-intelligence-cli/models/ibm-granite_granite-4.0-h-small-Q5_K_M.gguf

Environment (required)
```
export LLAMA_BLAS=1
export OMP_NUM_THREADS=40
export OPENBLAS_NUM_THREADS=40
export OMP_PROC_BIND=TRUE
export OMP_PLACES=cores
```

Flags (required)
```
-t 40 -c 4096 -b 512 -ngl 0
```

Start server
- Multi-socket default (NUMA-on bound to a single node):
```
numactl --cpunodebind=0 --membind=0 \
  llama-server -m /home/ui-cli_jake/unified-intelligence-cli/models/ibm-granite_granite-4.0-h-small-Q5_K_M.gguf \
  -t 40 -c 4096 -b 512 -ngl 0 \
  --host 127.0.0.1 --port 8080
```
- Fallback (single-socket or no numactl):
```
llama-server -m /home/ui-cli_jake/unified-intelligence-cli/models/ibm-granite_granite-4.0-h-small-Q5_K_M.gguf \
  -t 40 -c 4096 -b 512 -ngl 0 \
  --host 127.0.0.1 --port 8080
```

Health checks
```
curl -s http://127.0.0.1:8080/v1/models | jq .
# Smoke chat
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"models/ibm-granite_granite-4.0-h-small-Q5_K_M.gguf","messages":[{"role":"user","content":"hi"}],"max_tokens":8,"temperature":0.2}' | jq .
```

Quick L2 confirmation (append-only)
- Runs concurrency level 2 for small and medium, appends to metrics/llama_bench_load.csv, and prints acceptance vs single-stream baseline.
```
bash scripts/quick_l2_check.sh http://127.0.0.1:8080/v1
```
- Acceptance rule: err% < 1% and L2 tok/s_agg ≥ single-stream baseline tok/s (per prompt)

Operational defaults
- Interactive: concurrency level 1 (lowest p95 TTFT)
- Batch/throughput: concurrency level 2 (highest tok/s_agg)
- Request settings: max_tokens=256; temperature=0.2; prompts run separately

Rollback
- If err% ≥ 1% or material degradation in tok/s_agg or p95 TTFT:
  1) Stop the NUMA-on instance
  2) Start the last known-good (same env/flags; NUMA-off if needed)
  3) Retain all CSV/report rows for traceability

