# Quick Start (ATADO)

This guide gets you from zero to running your first task in under 15 minutes.

1) Prerequisites
- Python 3.12+
- Redis (optional for caching) — development only

2) Install
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
cp .env.example .env
```

3) Configure Provider (choose one)
- Mock (offline): default, no keys
- Grok: set XAI_API_KEY in .env
- Granite local: see docs/GRANITE_* docs

4) Run your first task
```bash
python -m src.main --task "Say hello" --provider mock --verbose
```

5) Team routing (recommended for scaled agents)
```bash
python -m src.main --task "Refactor router" --provider auto --routing team --agents scaled --verbose
```

6) Cache control (Phase 1)
- Disable cache: `--no-cache` or `ATADO_CACHE=0`
- TTL: `ATADO_CACHE_TTL_SECONDS=3600`
- Namespace (dev default): `ATADO_CACHE_NAMESPACE=atado:dev:llm:response:` (auto-derived from ATADO_ENV)
- Clear cache safely: `bash scripts/clear_cache.sh --namespace atado:dev:llm:response:`

7) Observability (routing trace)
- Add `--verbose` to see Domain → Team → Agent and top-3 domain scores
- All logs include a correlation ID (cid=...) for tracing

8) Troubleshooting
- No provider? Use `--provider mock`
- Redis unavailable? Cache auto-disables; run with `--no-cache` to force
- Need more detail? Use `--debug` for extra logs

