#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import sys

from src.adapters.rag import EmbeddingPipeline, SurrealDBStore, CodebaseRAG


async def main() -> None:
    repo_root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

    url = os.getenv("SURREALDB_URL", "ws://localhost:8000")
    ns = os.getenv("SURREALDB_NAMESPACE", "atado")
    db = os.getenv("SURREALDB_DATABASE", "rag")

    store = SurrealDBStore(url=url, namespace=ns, database=db)
    await store.connect()

    # Ensure schema exists
    schema_path = os.path.join(os.path.dirname(__file__), "init_surreal_schema.surql")
    if os.path.exists(schema_path):
        await store.init_schema_from_file(schema_path)

    rag = CodebaseRAG(db=store)
    count = await rag.embed(repo_root=repo_root)
    print(f"Indexed/updated code entities: {count}")

    await store.close()


if __name__ == "__main__":
    asyncio.run(main())

