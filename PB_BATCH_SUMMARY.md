# Project Builder Batch Processing — Research, Plan, Implement (Summary)

## Research (findings)
- Current single-project flow: orchestrator executes phases sequentially with ExecutionCoordinator iterating tasks in order (no cross-project parallelism).
- Parallelizable stages across projects: full project lifecycles (decompose → translate → execute) are independent; DB writes can contend if sharing one SQLite file.
- Bottlenecks: sequential per-project processing; LLM call latency; potential SQLite write-locks; remote SSH setup latency when used.
- Safe baseline runtime measurement was blocked by missing deps; qualitative code review indicates dominated by LLM calls and agent routing.

## Plan (architecture)
- Add ProjectBatchProcessor with:
  - Worker gate (max_workers) to process projects concurrently.
  - Shared LLM pool with token-bucket rate limiter (rps) and concurrency gate.
  - Per-project SQLite DB files to avoid contention.
- CLI: add --batch-file + tunables (--max-workers, --llm-rps, --llm-pool-size).
- Targets: 3–4x throughput; utilization improved by parallel projects while honoring provider limits.

## Implement (done)
- Added src/project_builder/execution/batch_processor.py (batch processor, rate limiter, provider pool).
- Updated src/project_builder/cli/command.py to accept --batch-file and batch options.
- Added tests/test_batch_processing.py (concurrency behavior via monkeypatch).

## Benchmarks (how-to)
- Run baseline (once deps installed):
  - single: time ./ui-cli build-project ... --model mock --sequential
  - batch: time ./ui-cli build-project --batch-file goals.txt --model mock --max-workers 4
- Expect ~3–4x throughput for N≫workers, bounded by LLM rps and task mix.
