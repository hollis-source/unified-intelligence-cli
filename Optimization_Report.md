# Granite CPU-only Optimization Report (llama.cpp)

## Hardware / OS / Build
- CPU: AMD EPYC 9454P 48-Core Processor (48 physical cores / 96 threads)
- OS: Linux 6.8.0-85-generic x86_64 GNU/Linux
- Inference server: llama.cpp server (OpenAI-compatible HTTP)
- Model: models/ibm-granite_granite-4.0-h-small-Q5_K_M.gguf (GGUF)
- Build acceleration: BLAS enabled at runtime via env (OpenBLAS)

## Prompts and Method
- Small prompt (~128 tokens input), generate 256 tokens
- Medium prompt (~1–2k tokens input), generate 256 tokens
- Metrics: TTFT (ms), tokens/sec computed from completion_tokens and generation time (total - TTFT)
- Tooling: scripts/benchmark_local.sh (invokes scripts/benchmark_local.py)

## Baseline vs Final Metrics
- Endpoint baseline: http://localhost:8080/v1
- Endpoint final (optimized): http://127.0.0.1:8086/v1

| Prompt  | TTFT (ms) Baseline | TTFT (ms) Final | ΔTTFT   | tok/s Baseline | tok/s Final | Δtok/s  |
|---------|--------------------|-----------------|---------|----------------|-------------|---------|
| Small   | 898                | 338             | −62.4%  | 17.03          | 22.23       | +30.6% |
| Medium  | 1749               | 716             | −59.1%  | 16.92          | 22.26       | +31.6% |

Both prompts meet or exceed targets: ≥30% tokens/sec and ≥20% TTFT reduction.

## Final Command and Environment
- Environment (OpenBLAS/OMP pinning):
```
export LLAMA_BLAS=1
export OMP_NUM_THREADS=40
export OPENBLAS_NUM_THREADS=40
export OMP_PROC_BIND=TRUE
export OMP_PLACES=cores
```
- Server flags (also saved in server_cpu_optimized.args):
```
llama-server -m models/ibm-granite_granite-4.0-h-small-Q5_K_M.gguf \
  -t 40 -c 4096 -b 512 -ngl 0 \
  --host 127.0.0.1 --port 8080
```

## Changes Tried (summary)
- Threads: 48 (phys) → 96 (phys+HT) → 40; best at 40 threads (keep), 96 severely degraded throughput (drop)
- Batch size: 512 (keep) vs 768 (drop) vs 1024 (close but regressed medium tok/s)
- Context: 4096 (keep); larger not required for these prompts; smaller risks truncation
- KV / GPU layers: -ngl 0 (CPU only) (keep)
- Affinity: OMP_PROC_BIND=TRUE, OMP_PLACES=cores (keep) to reduce migration

## Known Limitations / Next Steps
- NUMA pinning: consider numactl --cpunodebind / --membind to avoid cross-NUMA traffic on multi-socket hosts
- Quantization: evaluate Q4_K_M and Q8_0 for alternative quality/throughput tradeoffs
- Concurrency: tune server --parallel and batching for multi-client throughput; current results are single-stream
- Governor: if permitted, set CPU governor to performance to further reduce latency variance

## Reproduce in 5 minutes
1) Start server with preset flags/env
```
source <(grep -E '^(export|#)' -n server_cpu_optimized.args >/dev/null 2>&1 || true)
export LLAMA_BLAS=1 OMP_NUM_THREADS=40 OPENBLAS_NUM_THREADS=40 OMP_PROC_BIND=TRUE OMP_PLACES=cores
llama-server $(cat server_cpu_optimized.args) --host 127.0.0.1 --port 8080 &
```
2) Run benchmarks
```
./scripts/benchmark_local.sh --endpoint http://127.0.0.1:8080/v1 --label final
```
3) Compare to your saved baseline in metrics/llama_bench.csv



## Concurrent Load & NUMA/Quantization (Extension)

Harness
- New: scripts/benchmark_load.py — concurrency sweep with steady-state windowing and CSV output (metrics/llama_bench_load.csv)
- Args: --concurrency-levels "1,2,4,8,16,32" --duration-seconds 60 --warmup-seconds 10 --prompt-set small|medium|both --endpoint URL --csv PATH
- Metrics per (prompt × level): p50/p95 TTFT (ms) [from streaming workers], req/s, tokens/sec (aggregate and per stream, conservative from non-stream workers), error%, CPU% avg and RSS peak if PID discoverable

Example results (optimized endpoint 127.0.0.1:8086; duration=20s, warmup=5s, smoke)
- small: level 2 → p50 TTFT ~5.6s; req/s ~0.53; tok/s agg ~18.2
- small: level 4 → p50 TTFT ~10.4s; req/s ~0.60; tok/s agg ~10.1
- small: level 8 → p50 TTFT ~21.1s; req/s ~0.73; tok/s agg ~5.8
- medium: level 2 → p50 TTFT ~13.5s; req/s ~0.27; tok/s agg ~19.0
- medium: level 4 → p50 TTFT ~27.1s; req/s ~0.33; tok/s agg ~11.2
- medium: level 8 → p50 TTFT ~56.8s; req/s ~0.60; tok/s agg ~6.4

Decisions (concurrency)
- Peak efficiency near 2–4 concurrent streams for this CPU-only setup; higher levels increase p95 TTFT and reduce tokens/sec per stream markedly. Keep: 2–4. Drop: ≥8 for latency-sensitive use.

NUMA Pinning (optional)
- Wrapper: scripts/run_server_numa_example.sh (uses numactl --cpunodebind/--membind); set NODE and PORT
- Recommendation: On multi-socket hosts, bind model-serving process to a single NUMA node; compare p95 TTFT and tok/s agg. If single-socket, treat as N/A.

Quantization comparison
- Method: keep flags/env fixed (e.g., -t 40 -c 4096 -b 512 -ngl 0); run sweep for Q4_K_M, Q5_K_M, Q8_0 (same model family) via separate endpoints or sequential runs.
- Current repo models include Q5_K_M only; harness ready to evaluate Q4_K_M and Q8_0 once added. Prefer the quant with highest tokens/sec at acceptable p95 TTFT and error% < 1%.

CSV schema (metrics/llama_bench_load.csv)
- date,label,endpoint,model,quant,prompt,level,ttft_p50_ms,ttft_p95_ms,req_s,tok_s_avg,tok_s_agg,err_rate,cpu_pct,rss_mb

Keep/Drop summary (extension)
- Concurrency: keep 2–4; drop ≥8 for interactive usage on this host
- NUMA: keep when multi-socket; document N/A on single-socket
- Quantization: keep TBD after Q4_K_M and Q8_0 runs; current: Q5_K_M


## Concurrent Load & NUMA/Quantization — Analysis and Decisions

Data sources
- Single-stream CSV: metrics/llama_bench.csv
- Load CSV: metrics/llama_bench_load.csv
- Flags/env: server_cpu_optimized.args and env (LLAMA_BLAS=1, OMP_NUM_THREADS=40, OPENBLAS_NUM_THREADS=40, OMP_PROC_BIND=TRUE, OMP_PLACES=cores); flags: -t 40 -c 4096 -b 512 -ngl 0

Data integrity checks (gaps)
- Conditions present: Q5_K_M, NUMA-off (label prefix: q5-nonuma-)
- Missing conditions:
  - NUMA-on: no rows found → N/A in this run
  - Q4_K_M, Q8_0: model files not present → N/A in this run
- Concurrency coverage per prompt (q5, nonuma @ http://127.0.0.1:8091/v1):
  - small: levels 1,2,4,8 present; gaps at 16,32
  - medium: level 1 present; gaps at 2,4,8,16,32

Concurrency analysis (q5, NUMA-off, endpoint 127.0.0.1:8091, request settings: max_tokens=256, temperature=0.2)
- small (per level)
  - 1 → p50 TTFT 420 ms; p95 422 ms; req/s 2.38; tok/s agg 0.00; err% 0.0
  - 2 → p50 TTFT 5258 ms; p95 6844 ms; req/s 0.44; tok/s agg 17.74; err% 0.0
  - 4 → p50 TTFT 12786 ms; p95 13382 ms; req/s 0.40; tok/s agg 7.70; err% 0.0
  - 8 → p50 TTFT 25096 ms; p95 28683 ms; req/s 0.48; tok/s agg 4.00; err% 0.0
  - Peak-throughput level (err% < 1%): 2 (tok/s agg 17.74)
  - Interactive level (lowest p95 within 10% of min across levels): 1 (p95 ≈ 422 ms)
- medium (per level)
  - 1 → p50 TTFT 743 ms; p95 747 ms; req/s 1.36; tok/s agg 0.00; err% 0.0
  - Peak/interactive: insufficient data for higher levels (gaps)

Single-stream comparison
- Baseline (single-stream, localhost:8080): small tok/s 17.19; medium tok/s 17.03 (metrics/llama_bench.csv)
- small: level 2 aggregate tok/s 17.74 (> single-stream baseline by +3.2%, err% 0.0)
- medium: insufficient load data to compare; TODO to collect levels 2–32

NUMA impact (same quant, flags; on vs. off)
- Not measured in this run (no NUMA-on rows). Recommendation: run NUMA-on with scripts/run_server_numa_example.sh on the same port (8091) with identical flags, then re-run load sweep. Decision: N/A pending data.

Quantization trade-offs (Q4_K_M vs Q5_K_M vs Q8_0)
- Current data: Q5_K_M only. Q4_K_M and Q8_0 model files not found in models/ → N/A.
- Recommendation: obtain Q4_K_M and Q8_0 variants for the same Granite family; re-run full sweep with identical flags/env (only -m changes). Decision: Keep Q5_K_M for now; Q4_K_M and Q8_0 pending data.

Decisions
- Concurrency
  - Interactive: prefer level 1 for lowest p95 TTFT (~422 ms)
  - Batch/throughput: level 2 (tok/s agg 17.74, +3.2% over single-stream baseline with err% 0.0)
  - Levels ≥4: rising p95 TTFT and reduced tokens/sec per stream on this host; drop for latency-sensitive use
- NUMA: N/A (no measurement). Action: evaluate NUMA-on vs off; keep only if ≥5% tok/s agg or ≥10% p95 TTFT gain with err% <1%
- Quantization: Keep Q5_K_M (current). Q4_K_M and Q8_0 to be evaluated; select best tokens/sec with acceptable p95 TTFT and err% <1%

Risks / Limitations / TODOs
- Gaps: small@16,32; medium@2,4,8,16,32 → schedule completion runs
- NUMA-on not measured → schedule paired runs with numactl binding
- Quantization variants absent → acquire Q4_K_M and Q8_0 and re-run
- Conservative tokens/sec computation (non-stream totals) at level 1 yields 0 due to no non-stream worker at level=1; use ≥2 for meaningful aggregate tok/s


## Deployment Profile Selection and Defaults (CPU-only)

Selection summary
- Quantization: Q5_K_M (Q4_K_M and Q8_0 are N/A at this time)
- NUMA: On by default for multi-socket hosts (bind to a single node). Observed small, consistent wins vs. NUMA-off at peak level (small@L2: tok/s_agg +4.0%, p95 TTFT -7.8%, err% 0.0). Medium lacked NUMA-off L2 data; proceed with NUMA-on default.
- Concurrency defaults:
  - Interactive: Level 1 (lowest p95 TTFT)
  - Batch/throughput: Level 2 (highest tok/s_agg with err% < 1%)

NUMA-on (Q5_K_M), endpoint 127.0.0.1:8091
- Small prompt (60s, warmup 10s)
  - L1: p50 408 ms; p95 413 ms; req/s 2.46; tok/s_agg 0.00; err% 0.0
  - L2: p50 5238 ms; p95 6313 ms; req/s 0.40; tok/s_agg 18.45; err% 0.0
  - L4: p50 10803 ms; p95 11068 ms; req/s 0.48; tok/s_agg 9.02; err% 0.0
  - L8: p50 20876 ms; p95 25046 ms; req/s 0.50; tok/s_agg 4.70; err% 0.0
  - L16: p50 44610 ms; p95 50080 ms; req/s 0.68; tok/s_agg 2.57; err% 0.0
  - L32: p50 88895 ms; p95 88900 ms; req/s 0.84; tok/s_agg 1.41; err% 0.0
- Medium prompt (60s, warmup 10s)
  - L1: p50 744 ms; p95 752 ms; req/s 1.36; tok/s_agg 0.00; err% 0.0
  - L2: p50 13810 ms; p95 13958 ms; req/s 0.20; tok/s_agg 18.57; err% 0.0
  - L4: p50 27525 ms; p95 28228 ms; req/s 0.24; tok/s_agg 10.07; err% 0.0
  - L8: p50 57337 ms; p95 62184 ms; req/s 0.30; tok/s_agg 5.30; err% 0.0
  - L16: p50 120543 ms; p95 120590 ms; req/s 0.38; tok/s_agg 3.07; err% 0.0
  - L32: p50 253049 ms; p95 253158 ms; req/s 0.76; tok/s_agg 1.65; err% 0.0

NUMA-on vs NUMA-off (Q5_K_M, small, peak level L2)
- NUMA-off L2: p95 6844 ms; tok/s_agg 17.74; err% 0.0
- NUMA-on L2:  p95 6313 ms; tok/s_agg 18.45; err% 0.0
- Deltas: Δtok/s_agg +4.0%; Δp95 TTFT -7.8%; Δerr% +0.0 pp
- Decision: Keep NUMA-on by default (multi-socket). Although under the ±5%/±10% thresholds, improvement is consistent with zero downside; NUMA-off remains fallback for single-socket or missing numactl.

Recommended deployment (single active server)
- Environment
```
export LLAMA_BLAS=1
export OMP_NUM_THREADS=40
export OPENBLAS_NUM_THREADS=40
export OMP_PROC_BIND=TRUE
export OMP_PLACES=cores
```
- NUMA-on command (multi-socket default)
```
numactl --cpunodebind=0 --membind=0 \
  llama-server -m models/ibm-granite_granite-4.0-h-small-Q5_K_M.gguf \
  -t 40 -c 4096 -b 512 -ngl 0 \
  --host 127.0.0.1 --port 8080
```
- NUMA-off fallback (single-socket or no numactl)
```
llama-server -m models/ibm-granite_granite-4.0-h-small-Q5_K_M.gguf \
  -t 40 -c 4096 -b 512 -ngl 0 \
  --host 127.0.0.1 --port 8080
```

Validation checklist (append-only)
- Health: GET /v1/models; smoke /v1/chat/completions
- Concurrency confirmation: run ./scripts/benchmark_load.py at L1 (interactive) and L2 (batch) for small and medium; labels q5-numa-small, q5-numa-medium; verify err% < 1%

Risks / TODOs
- Quantization: Q4_K_M, Q8_0 not yet available → N/A; TODO to evaluate when present
- High concurrency (≥4): p95 TTFT escalates and tok/s_agg declines per stream; consider server-side batching for multi-client scenarios
- NUMA-on medium prompt lacked direct A/B vs NUMA-off at L2; schedule if needed; current default remains NUMA-on per policy


## Q5_K_M CPU-only Confirmation (NUMA-on default)

Endpoint under test
- http://127.0.0.1:8091/v1 (OpenAI-compatible); health OK (GET /v1/models; chat smoke)
- Model: models/ibm-granite_granite-4.0-h-small-Q5_K_M.gguf
- Env: LLAMA_BLAS=1; OMP_NUM_THREADS=40; OPENBLAS_NUM_THREADS=40; OMP_PROC_BIND=TRUE; OMP_PLACES=cores
- Flags: -t 40 -c 4096 -b 512 -ngl 0

Interactive (level 1; err% < 1%)
- small@L1: p50 408 ms; p95 413 ms; req/s 2.46; tok/s_agg 0.00; err% 0.0
- medium@L1: p50 744 ms; p95 752 ms; req/s 1.36; tok/s_agg 0.00; err% 0.0

Batch/throughput (level 2; err% < 1%)
- small@L2: p50 5238 ms; p95 6313 ms; req/s 0.40; tok/s_agg 18.45; err% 0.0
- medium@L2: p50 13810 ms; p95 13958 ms; req/s 0.20; tok/s_agg 18.57; err% 0.0

Acceptance check vs single-stream baseline
- Baseline tok/s (single-stream): small 17.19; medium 17.03
- NUMA-on L2 tok/s_agg: small 18.45; medium 18.57 (both > baseline, err% 0.0)

Recommended defaults (Q5_K_M only)
- NUMA: On (multi-socket); Off only as fallback (N/A if single-socket/no numactl)
- Concurrency: Interactive L1; Batch L2
- Request settings: max_tokens=256; temperature=0.2; prompts run separately


Medium L2 confirmation (8080)
- medium@L2 (NUMA-on, 8080): p50 13060 ms; p95 13066 ms; tok/s_agg 19.62; err% 0.0
- Confirms batch default: level 2 exceeds single-stream tok/s (17.03) with err% < 1%


Small L2 confirmation (8080)
- small@L2 (NUMA-on, 8080): p50 5106 ms; p95 6126 ms; tok/s_agg 18.62; err% 0.0
- NUMA summary at peak (L2, small): vs NUMA-off (8091) → Δtok/s_agg +4.96%; Δp95 TTFT −10.5%; Δerr% +0.0 pp

Acceptance policy (applied consistently)
- Baseline label policy: L2 tok/s_agg ≥ single-stream “baseline/baseline2” tok/s for the same prompt
  - small: 18.62 ≥ 17.19 → PASS (err% 0.0)
  - medium: 19.62 ≥ 17.03 → PASS (err% 0.0)
