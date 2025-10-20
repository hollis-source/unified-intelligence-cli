# Caching Guide (Development)

Phase 1 adds safe, controllable caching for LLM responses.

Key points
- Backend: Redis (development only)
- Enable/disable via CLI/env
- TTL configurable
- Namespaced keys for selective clears
- Safe clear script provided

Controls
- Disable cache: `--no-cache` or `ATADO_CACHE=0`
- TTL: `ATADO_CACHE_TTL_SECONDS` (default 14400s)
- Namespace prefix: `ATADO_CACHE_NAMESPACE` (default: `atado:${ATADO_ENV:-dev}:llm:response:`)
- Environment: `ATADO_ENV=dev|staging|prod` (prod disables cache by policy unless explicitly enabled)

Where caching is used
- Module: `src/adapters/agent/llm_cache.py` (Redis-based)
- Wired via: `LLMAgentExecutor` in `src/composition.py`
- Key schema: `${NAMESPACE}${sha256(messages,task,model)[:16]}`

Safe clearing
- Script: `scripts/clear_cache.sh`
- Default mode: SCAN+DEL by namespace
- FLUSHDB: Only in `ATADO_ENV=dev` and requires interactive confirmation

Examples
```bash
# Clear only LLM response cache keys
bash scripts/clear_cache.sh --namespace atado:dev:llm:response:

# Disable cache for fresh runs
ATADO_CACHE=0 python -m src.main --task "..."

# Set TTL to 1 hour
ATADO_CACHE_TTL_SECONDS=3600 python -m src.main --task "..."
```

Notes
- If Redis is unavailable, caching auto-disables (non-fatal)
- Namespacing allows coexisting caches for different envs/components
- Never run FLUSHDB outside dev

