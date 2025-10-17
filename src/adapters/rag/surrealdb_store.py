from __future__ import annotations

import asyncio
import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

try:
    from surrealdb import AsyncSurreal
except Exception:  # pragma: no cover - optional at import time
    AsyncSurreal = None  # type: ignore


class SurrealDBStore:
    """Thin async adapter around SurrealDB for RAG storage/retrieval.

    Clean Architecture: adapter for external DB, no business logic.
    """

    def __init__(self, url: str, namespace: str, database: str, user: str = "root", password: str = "root"):
        self.url = url
        self.namespace = namespace
        self.database = database
        self.user = user
        self.password = password
        self.db = None

    async def connect(self) -> None:
        if AsyncSurreal is None:
            raise RuntimeError("surrealdb package not installed. pip install surrealdb")
        self.db = AsyncSurreal(self.url)
        await self.db.connect()
        await self.db.signin({"username": self.user, "password": self.password})
        await self.db.use(self.namespace, self.database)

    async def close(self) -> None:
        if self.db:
            await self.db.close()
            self.db = None

    # -------------------------
    # Schema initialization
    # -------------------------
    async def init_schema_from_file(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        await self.query(schema_sql)

    # -------------------------
    # Low-level query
    # -------------------------
    async def query(self, sql: str, vars: Optional[Dict[str, Any]] = None) -> Any:
        assert self.db is not None, "Not connected"
        return await self.db.query(sql, vars or {})

    # -------------------------
    # Code entities
    # -------------------------
    async def upsert_code_entity(
        self,
        *,
        file_path: str,
        name: str,
        qualified_name: str,
        language: str,
        entity_type: str,
        start_line: int,
        end_line: int,
        content: str,
        content_hash: str,
        docstring: Optional[str],
        tags: Optional[List[str]],
        embedding: np.ndarray,
        embedding_model: str,
    ) -> None:
        sql = """
        LET $id = (SELECT id FROM code_entity WHERE file_path = $file_path AND name = $name LIMIT 1)[0].id;
        IF $id THEN UPDATE $id SET file_path = $file_path, name = $name, qualified_name = $qualified_name,
           language = $language, entity_type = $entity_type, start_line = $start_line, end_line = $end_line,
           content = $content, content_hash = $content_hash, docstring = $docstring, tags = $tags,
           embedding = $embedding, embedding_model = $embedding_model, updated_at = time::now();
        ELSE CREATE code_entity SET id = rand::uuid(), file_path = $file_path, name = $name,
           qualified_name = $qualified_name, language = $language, entity_type = $entity_type,
           start_line = $start_line, end_line = $end_line, content = $content, content_hash = $content_hash,
           docstring = $docstring, tags = $tags, embedding = $embedding, embedding_model = $embedding_model;
        END;
        """
        await self.query(
            sql,
            {
                "file_path": file_path,
                "name": name,
                "qualified_name": qualified_name,
                "language": language,
                "entity_type": entity_type,
                "start_line": start_line,
                "end_line": end_line,
                "content": content,
                "content_hash": content_hash,
                "docstring": docstring,
                "tags": tags or [],
                "embedding": embedding.tolist(),
                "embedding_model": embedding_model,
            },
        )

    async def get_code_entity_hash(self, file_path: str, name: str) -> Optional[str]:
        sql = "SELECT content_hash FROM code_entity WHERE file_path = $file_path AND name = $name LIMIT 1;"
        res = await self.query(sql, {"file_path": file_path, "name": name})
        try:
            rows = res[0]["result"]
            if rows:
                return rows[0].get("content_hash")
        except Exception:
            pass
        return None

    async def search_similar_code(self, query_embedding: np.ndarray, top_k: int = 5, language: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = (
            "SELECT id, file_path, name, qualified_name, language, start_line, end_line, "
            "vector::similarity::cosine(embedding, $e) AS similarity FROM code_entity "
            "WHERE embedding <|$k|> $e "
        )
        if language:
            sql += "AND language = $lang "
        sql += "ORDER BY similarity DESC LIMIT $k;"
        res = await self.query(sql, {"e": query_embedding.tolist(), "k": top_k, "lang": language})
        try:
            return res[0]["result"]
        except Exception:
            return []

    # -------------------------
    # Execution logs/patterns
    # -------------------------
    async def store_execution_log(
        self,
        *,
        execution_id: str,
        task_description: str,
        task_domain: Optional[str],
        agent_role: Optional[str],
        success: bool,
        status: str,
        latency_seconds: float,
        output_excerpt: str,
        embedding: Optional[np.ndarray],
        embedding_model: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        sql = """
        CREATE execution_log SET
            id = $id,
            task_description = $task_description,
            task_domain = $task_domain,
            agent_role = $agent_role,
            success = $success,
            status = $status,
            latency_seconds = $latency,
            output_excerpt = $excerpt,
            embedding = $embedding,
            embedding_model = $embedding_model,
            metadata = $metadata;
        """
        await self.query(
            sql,
            {
                "id": execution_id,
                "task_description": task_description,
                "task_domain": task_domain,
                "agent_role": agent_role,
                "success": success,
                "status": status,
                "latency": latency_seconds,
                "excerpt": output_excerpt,
                "embedding": embedding.tolist() if isinstance(embedding, np.ndarray) else None,
                "embedding_model": embedding_model,
                "metadata": metadata or {},
            },
        )

    async def search_similar_execution(self, query_embedding: np.ndarray, top_k: int = 5, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = (
            "SELECT id, task_description, agent_role, success, latency_seconds, "
            "vector::similarity::cosine(embedding, $e) AS similarity FROM execution_log "
            "WHERE success = true AND embedding <|$k|> $e "
        )
        if domain:
            sql += "AND task_domain = $domain "
        sql += "ORDER BY similarity DESC LIMIT $k;"
        res = await self.query(sql, {"e": query_embedding.tolist(), "k": top_k, "domain": domain})
        try:
            return res[0]["result"]
        except Exception:
            return []

    # -------------------------
    # Learnings and optimization patterns
    # -------------------------
    async def store_agent_learning(
        self,
        *,
        pattern_id: str,
        hypothesis: str,
        confidence: float,
        evidence_ids: Optional[List[str]] = None,
        embedding: Optional[np.ndarray] = None,
        embedding_model: Optional[str] = None,
    ) -> None:
        sql = """
        CREATE agent_learning SET
            id = rand::uuid(),
            pattern_id = $pattern_id,
            hypothesis = $hypothesis,
            confidence = $confidence,
            evidence_ids = $evidence_ids,
            embedding = $embedding,
            embedding_model = $embedding_model;
        """
        await self.query(
            sql,
            {
                "pattern_id": pattern_id,
                "hypothesis": hypothesis,
                "confidence": confidence,
                "evidence_ids": evidence_ids or [],
                "embedding": embedding.tolist() if isinstance(embedding, np.ndarray) else None,
                "embedding_model": embedding_model,
            },
        )

    async def store_optimization_pattern(
        self,
        *,
        title: str,
        description: str,
        applies_to_domain: str,
        tags: Optional[List[str]] = None,
        snippet: Optional[str] = None,
        embedding: Optional[np.ndarray] = None,
        embedding_model: Optional[str] = None,
    ) -> None:
        sql = """
        CREATE optimization_pattern SET
            id = rand::uuid(),
            title = $title,
            description = $description,
            applies_to_domain = $domain,
            tags = $tags,
            snippet = $snippet,
            embedding = $embedding,
            embedding_model = $embedding_model;
        """
        await self.query(
            sql,
            {
                "title": title,
                "description": description,
                "domain": applies_to_domain,
                "tags": tags or [],
                "snippet": snippet,
                "embedding": embedding.tolist() if isinstance(embedding, np.ndarray) else None,
                "embedding_model": embedding_model,
            },
        )

    async def search_patterns(self, query_embedding: np.ndarray, top_k: int = 5, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = (
            "SELECT id, title, applies_to_domain, tags, "
            "vector::similarity::cosine(embedding, $e) AS similarity FROM optimization_pattern "
            "WHERE embedding <|$k|> $e "
        )
        if domain:
            sql += "AND applies_to_domain = $domain "
        sql += "ORDER BY similarity DESC LIMIT $k;"
        res = await self.query(sql, {"e": query_embedding.tolist(), "k": top_k, "domain": domain})
        try:
            return res[0]["result"]
        except Exception:
            return []

