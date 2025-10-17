from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import numpy as np

from .embedding_pipeline import EmbeddingPipeline
from .surrealdb_store import SurrealDBStore
from .codebase_indexer import CodebaseIndexer


class CodebaseRAG:
    """End-to-end RAG helper for codebase learning with SurrealDB.

    Methods:
      - embed(repo_root): index codebase into SurrealDB
      - query(text, top_k): semantic code search
      - retrieve(task_text, top_k): hybrid retrieval (code + patterns)
    """

    def __init__(self, db: SurrealDBStore, embedder: Optional[EmbeddingPipeline] = None):
        self.db = db
        self.embedder = embedder or EmbeddingPipeline()

    async def embed(self, repo_root: str, include: Optional[List[str]] = None, exclude_dirs: Optional[List[str]] = None, batch_size: int = 64) -> int:
        indexer = CodebaseIndexer(self.db, self.embedder, repo_root)
        return await indexer.index(include=include, exclude_dirs=exclude_dirs, batch_size=batch_size)

    async def query(self, text: str, top_k: int = 5, language: Optional[str] = None) -> List[Dict[str, Any]]:
        q = await self.embedder.embed_text(text)
        return await self.db.search_similar_code(q, top_k=top_k, language=language)

    async def retrieve(self, text: str, top_k: int = 5, domain: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        q = await self.embedder.embed_text(text)
        code = await self.db.search_similar_code(q, top_k=top_k)
        patterns = await self.db.search_patterns(q, top_k=top_k, domain=domain)
        execs = await self.db.search_similar_execution(q, top_k=top_k, domain=domain)
        return {"code": code, "patterns": patterns, "executions": execs}

    def build_prompt_context(self, retrieve_result: Dict[str, List[Dict[str, Any]]], max_chars: int = 6000) -> str:
        """Compact retrieved items into a prompt-ready context under size budget."""
        parts: List[str] = []
        for c in retrieve_result.get("code", [])[:5]:
            parts.append(f"[CODE] {c.get('qualified_name')} ({c.get('file_path')}): sim={c.get('similarity'):.3f}")
        for p in retrieve_result.get("patterns", [])[:3]:
            parts.append(f"[PATTERN] {p.get('title')} tags={p.get('tags')}")
        for e in retrieve_result.get("executions", [])[:3]:
            parts.append(f"[EXEC] {e.get('agent_role')} success={e.get('success')} sim={e.get('similarity'):.3f}")
        text = "\n".join(parts)
        return text[:max_chars]

