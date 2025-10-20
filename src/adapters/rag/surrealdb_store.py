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
        # Lazy connection: connect on first use to avoid event loop conflicts
        if self.db is None:
            await self.connect()
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
        team_id: Optional[str] = None,
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
            task_id = $task_id,
            agent_id = $agent_id,
            task_description = $task_description,
            task_domain = $task_domain,
            agent_role = $agent_role,
            team_id = $team_id,
            success = $success,
            status = $status,
            latency_seconds = $latency,
            output_excerpt = $excerpt,
            embedding = $embedding,
            embedding_model = $embedding_model,
            metadata = $metadata,
            error_message = $error_message,
            routing_confidence = $routing_confidence,
            routing_domain = $routing_domain;
        """
        # Fill routing_domain from routing_decisions if missing
        routing_domain_val = (metadata.get("routing_domain") if metadata and metadata.get("routing_domain") else (task_domain or ""))
        routing_conf_val = float(metadata.get("routing_confidence", 0.0) if metadata else 0.0)
        if (not routing_domain_val) and metadata and metadata.get("task_id"):
            try:
                res = await self.query(
                    "SELECT task_domain, confidence FROM routing_decisions WHERE task_id = $task_id ORDER BY timestamp DESC LIMIT 1;",
                    {"task_id": metadata["task_id"]},
                )
                row = None
                if res and isinstance(res, list):
                    if isinstance(res[0], dict) and "task_domain" in res[0]:
                        row = res[0]
                    elif hasattr(res[0], 'get') and res[0].get("result"):
                        r0 = res[0].get("result")
                        row = r0[0] if r0 else None
                if row:
                    routing_domain_val = row.get("task_domain") or routing_domain_val
                    try:
                        routing_conf_val = float(row.get("confidence", routing_conf_val))
                    except Exception:
                        pass
            except Exception:
                pass
        # Final fallback: classify domain from description if still empty
        if not routing_domain_val and task_description:
            try:
                from src.routing.domain_classifier import DomainClassifier
                from src.entity import Task as CoreTask
                routing_domain_val = DomainClassifier().classify(CoreTask(description=task_description)) or routing_domain_val
            except Exception:
                pass


        await self.query(
            sql,
            {
                "id": execution_id,
                "task_id": metadata.get("task_id", "") if metadata else "",
                "agent_id": (metadata.get("agent_id") if metadata and metadata.get("agent_id") else (agent_role or "unknown")),
                "task_description": task_description or "",
                "task_domain": task_domain or "",
                "agent_role": agent_role or "",
                "team_id": team_id or "",
                "success": bool(success),
                "status": status or "",
                "latency": float(latency_seconds or 0.0),
                "excerpt": output_excerpt or "",
                "embedding": embedding.tolist() if isinstance(embedding, np.ndarray) else None,
                "embedding_model": embedding_model or "",
                "metadata": metadata or {},
                "error_message": (metadata.get("error_message") if metadata and metadata.get("error_message") else ""),
                "routing_confidence": routing_conf_val,
                "routing_domain": routing_domain_val,
            },
        )

    async def search_similar_execution(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        domain: Optional[str] = None,
        success_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Search for similar execution patterns.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            domain: Optional domain filter
            success_only: Only return successful executions (default: True)

        Returns:
            List of similar execution patterns with similarity scores
        """
        # Note: SurrealDB vector search <|k|> operator requires literal number, not parameter
        sql = (
            f"SELECT id, task_description, agent_role, team_id, task_domain, "
            f"success, latency_seconds, "
            f"vector::similarity::cosine(embedding, $e) AS similarity FROM execution_log "
            f"WHERE embedding <|{top_k}|> $e "
        )
        if success_only:
            sql += "AND success = true "
        if domain:
            sql += "AND task_domain = $domain "
        sql += f"ORDER BY similarity DESC LIMIT {top_k};"
        res = await self.query(sql, {"e": query_embedding.tolist(), "domain": domain})
        try:
            # Handle different result formats
            if res and isinstance(res, list):
                if isinstance(res[0], dict) and "task_description" in res[0]:
                    # Direct result format
                    return res
                elif hasattr(res[0], 'get') and res[0].get("result"):
                    # Nested result format
                    return res[0]["result"]
            return []
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

    # =============================
    # Agent Performance Methods
    # =============================

    async def update_agent_performance(
        self,
        agent_role: str,
        total_tasks: int,
        successful_tasks: int,
        failed_tasks: int,
        avg_latency_ms: float
    ) -> None:
        """Update or create agent performance record."""
        success_rate = (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0.0

        sql = """
        CREATE agent_performance SET
            agent_role = $agent_role,
            total_tasks = $total_tasks,
            successful_tasks = $successful_tasks,
            failed_tasks = $failed_tasks,
            avg_latency_ms = $avg_latency_ms,
            success_rate = $success_rate;
        """

        await self.query(
            sql,
            {
                "agent_role": agent_role,
                "total_tasks": total_tasks,
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "avg_latency_ms": avg_latency_ms,
                "success_rate": success_rate,
            },
        )

    async def get_agent_performance(self, agent_role: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for a specific agent."""
        sql = "SELECT * FROM agent_performance WHERE agent_role = $role LIMIT 1;"
        res = await self.query(sql, {"role": agent_role})
        try:
            results = res[0]["result"]
            return results[0] if results else None
        except Exception:
            return None

    async def get_top_performing_agents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top performing agents by success rate."""
        sql = "SELECT * FROM agent_performance ORDER BY success_rate DESC LIMIT $limit;"
        res = await self.query(sql, {"limit": limit})
        try:
            return res[0]["result"]
        except Exception:
            return []

    # =============================
    # Routing Decisions Methods
    # =============================

    async def store_routing_decision(
        self,
        task_id: str,
        task_description: str,
        task_domain: str,
        selected_agent: str,
        selected_team: Optional[str],
        routing_strategy: str,
        confidence: float,
        success: Optional[bool],
        actual_agent: Optional[str] = None,
        fallback_used: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store a routing decision for feedback learning."""
        import uuid

        sql = """
        CREATE routing_decisions SET
            id = $id,
            task_id = $task_id,
            task_description = $task_description,
            task_domain = $task_domain,
            selected_agent = $selected_agent,
            selected_team = $selected_team,
            routing_strategy = $routing_strategy,
            confidence = $confidence,
            success = $success,
            actual_agent = $actual_agent,
            fallback_used = $fallback_used,
            metadata = $metadata;
        """

        await self.query(
            sql,
            {
                "id": str(uuid.uuid4()),
                "task_id": task_id,
                "task_description": task_description,
                "task_domain": task_domain,
                "selected_agent": selected_agent,
                "selected_team": selected_team,
                "routing_strategy": routing_strategy,
                "confidence": confidence,
                "success": success,
                "actual_agent": actual_agent or selected_agent,
                "fallback_used": fallback_used,
                "metadata": metadata or {},
            },
        )

    async def get_routing_accuracy(self, strategy: Optional[str] = None, limit: int = 100) -> float:
        """Calculate routing accuracy for a given strategy."""
        sql = "SELECT success FROM routing_decisions "
        if strategy:
            sql += "WHERE routing_strategy = $strategy "
        sql += "LIMIT $limit;"

        res = await self.query(sql, {"strategy": strategy, "limit": limit})
        try:
            # Handle different result formats
            results = None
            if res and isinstance(res, list):
                if isinstance(res[0], dict) and "success" in res[0]:
                    results = res
                elif hasattr(res[0], 'get') and res[0].get("result"):
                    results = res[0]["result"]

            if not results:
                return 0.0

            # Filter out None values (tasks not yet completed)
            completed = [r for r in results if r.get("success") is not None]
            if not completed:
                return 0.0

            successful = sum(1 for r in completed if r.get("success"))
            return (successful / len(completed)) * 100
        except Exception as e:
            print(f"Error calculating routing accuracy: {e}")
            return 0.0

    async def get_recent_routing_decisions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent routing decisions for analysis."""
        sql = "SELECT * FROM routing_decisions LIMIT $limit;"
        res = await self.query(sql, {"limit": limit})
        try:
            # Handle different result formats
            if res and isinstance(res, list):
                if isinstance(res[0], dict) and "task_id" in res[0]:
                    return res
                elif hasattr(res[0], 'get') and res[0].get("result"):
                    return res[0]["result"]
            return []
        except Exception:
            return []

    # =============================
    # Audit Log Methods
    # =============================

    async def store_audit_log(
        self,
        *,
        action: str,
        actor: str = "system",
        reason: Optional[str] = None,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store an audit log entry.

        Schema (SurrealDB):
          CREATE audit_log SET
            id = rand::uuid(),
            ts = time::now(),
            action = <string>,
            actor = <string>,
            reason = <string|null>,
            before = <object|null>,
            after = <object|null>,
            metadata = <object|null>;
        """
        sql = (
            "CREATE audit_log SET id = rand::uuid(), ts = time::now(), "
            "action = $action, actor = $actor, reason = $reason, before = $before, after = $after, metadata = $metadata;"
        )
        await self.query(
            sql,
            {
                "action": action,
                "actor": actor,
                "reason": reason,
                "before": before or {},
                "after": after or {},
                "metadata": metadata or {},
            },
        )

    # =============================
    # Routing Weight Helpers
    # =============================

    async def fetch_weights_for_domains(self, domains: list[str]) -> List[Dict[str, Any]]:
        if not domains:
            return []
        sql = "SELECT domain, agent, weight FROM routing_weight WHERE domain IN $domains"
        rows = await self.query(sql, {"domains": domains})
        # Surreal returns list of result sets; flatten if needed
        if isinstance(rows, list) and rows and isinstance(rows[0], list):
            out = []
            for rs in rows:
                out.extend(rs)
            return out
        return rows or []

    async def apply_domain_multipliers(self, weights: Dict[str, float]) -> None:
        """Multiply weights per domain by given multipliers with clamp [0.1, 2.0]."""
        for domain, mult in (weights or {}).items():
            sql = (
                "UPDATE routing_weight SET weight = math::max(0.1, math::min(2.0, weight * $mult)), "
                "update_count = update_count + 1, last_updated = time::now() WHERE domain = $domain"
            )
            await self.query(sql, {"domain": domain, "mult": float(mult)})

