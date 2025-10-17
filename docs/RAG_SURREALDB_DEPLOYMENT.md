# SurrealDB Vector RAG Deployment Guide

This guide brings up SurrealDB-backed RAG for ATADO and indexes your codebase for adaptive agent learning.

## 1) Install and Run SurrealDB

- Local CLI:
```
curl -sSf https://install.surrealdb.com | sh
surreal start --user root --pass root file://data/surrealdb
```
- Docker:
```
docker run --rm -p 8000:8000 surrealdb/surrealdb:latest start --user root --pass root memory
```

## 2) Configure Environment

Create .env (or export vars):
```
SURREALDB_URL=ws://localhost:8000
SURREALDB_NAMESPACE=atado
SURREALDB_DATABASE=rag
# Optional: for OpenAI embeddings (otherwise uses sentence-transformers)
# OPENAI_API_KEY=sk-...
```

## 3) Initialize Schema

Load schema (creates tables and indexes defined for vectors):
```
surreal sql --conn $SURREALDB_URL --user root --pass root \
  --ns $SURREALDB_NAMESPACE --db $SURREALDB_DATABASE \
  < scripts/init_surreal_schema.surql
```

## 4) Embed Your Codebase

Index repository (defaults to current repo):
```
python3 scripts/embed_codebase.py /path/to/repo
```
This walks Python files, extracts classes/functions, generates embeddings (local sentence-transformers by default), and upserts into SurrealDB with incremental hashing.

## 5) Test Retrieval

Quick semantic search example:
```
python - <<'PY'
import asyncio, os
from src.adapters.rag import SurrealDBStore, CodebaseRAG

async def run():
    store = SurrealDBStore(os.getenv('SURREALDB_URL','ws://localhost:8000'), os.getenv('SURREALDB_NAMESPACE','atado'), os.getenv('SURREALDB_DATABASE','rag'))
    await store.connect()
    rag = CodebaseRAG(store)
    res = await rag.query('HTN planning task assignment', top_k=5, language='python')
    for r in res:
        print(r['qualified_name'], r['file_path'], r['similarity'])
    await store.close()
asyncio.run(run())
PY
```

## 6) Connect to Local LLM (llama.cpp)

- Start llama.cpp server (example):
```
./server -m models/gguf/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf -c 4096 -ngl 35 -t 8 -p 8080
```
- Use any existing local LLM adapter in `src/adapters/llm/` (or create one) to call the server.
- Inject RAG context before planning/routing, e.g.:
```python
from src.adapters.rag import CodebaseRAG
rag_ctx = await rag.retrieve(task.description, top_k=5)
prompt_context = rag.build_prompt_context(rag_ctx)
# Prepend `prompt_context` to your LLM prompt in TaskPlanner/TeamRouter
```

## 7) Adaptive Learning Capture

Wrap the coordinator to persist execution feedback:
- Class: `src/use_cases/rag_task_coordinator.py` (captures results into `execution_log` with vector embeddings)
- Swap it in place of `TaskCoordinatorUseCase` where you construct the orchestrator.

## 8) Operational Notes

- Batch size: tune via `EmbeddingPipeline.embed_texts(batch_size=...)`
- Incremental updates: content hashes prevent re-embedding unchanged symbols
- Namespace/DB: keep separate DB per project or environment
- Backup: SurrealDB file storage path `file://data/surrealdb` is portable for dev backups

## 9) Example SurrealQL Queries

- Code semantic search:
```
SELECT id, file_path, name, qualified_name,
       vector::similarity::cosine(embedding, $e) AS sim
FROM code_entity WHERE embedding <|$k|> $e ORDER BY sim DESC LIMIT $k;
```
- Successful execution patterns for domain:
```
SELECT task_description, agent_role, latency_seconds,
       vector::similarity::cosine(embedding, $e) AS sim
FROM execution_log
WHERE success = true AND task_domain = $domain AND timestamp > time::now() - 30d
  AND embedding <|$k|> $e ORDER BY sim DESC LIMIT $k;
```

