"""Granite LLM adapter v2 - With lazy RAG initialization to fix event loop issues.

Clean Architecture: Implements ITextGenerator interface for dependency inversion.

Key Improvement: RAG components initialized lazily in thread-local storage,
avoiding async event loop conflicts.

Features:
- Load balancing across multiple llama.cpp instances (round-robin)
- Thread-safe lazy RAG initialization (no event loop conflicts)
- 512K context window support
- Zero-cost local inference
"""

import requests
from typing import List, Dict, Any, Optional
import itertools
import asyncio
import threading

from src.interface import ITextGenerator, LLMConfig
from src.adapters.llm.rag_config import RAGConfig


class GraniteAdapterV2(ITextGenerator):
    """
    IBM Granite 4.0-H adapter with lazy RAG support.

    Deployment: llama.cpp servers (2 instances × 512K context × Q8_0 cache)
    Performance: 15.67 tok/s per instance, 31.34 tok/s aggregate

    Architecture:
        User Query → RAG Retrieval (lazy init) → Load Balancer → llama.cpp → Response

    RAG Design: Thread-local lazy initialization prevents event loop conflicts.
    """

    def __init__(
        self,
        instances: Optional[List[str]] = None,
        enable_rag: bool = False,
        rag_config: Optional[RAGConfig] = None,
        timeout: int = 300
    ):
        """
        Initialize Granite adapter.

        Args:
            instances: List of llama.cpp server URLs
            enable_rag: Enable RAG context injection
            rag_config: RAG configuration for lazy initialization
            timeout: Request timeout in seconds (default: 300s for complex analyses)
        """
        self.instances = instances or [
            "http://localhost:8080",
            "http://localhost:8081"
        ]
        self.enable_rag = enable_rag
        self.timeout = timeout

        # Round-robin load balancer
        self._instance_cycle = itertools.cycle(self.instances)

        # RAG configuration (not initialized components)
        if enable_rag:
            if not rag_config:
                raise ValueError("RAG enabled but rag_config not provided")
            self.rag_config = rag_config
        else:
            self.rag_config = None

        # Thread-local storage for RAG components
        # Each thread gets its own SurrealDB connection and embedder
        # This avoids event loop conflicts
        self._thread_local = threading.local()

    def generate(
        self,
        messages: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None
    ) -> str:
        """
        Generate text response using Granite.

        Implements ITextGenerator interface.

        Args:
            messages: Conversation in standard format
                     [{"role": "system", "content": "..."},
                      {"role": "user", "content": "..."}]
            config: Optional LLM configuration

        Returns:
            Generated text response
        """
        # Extract user query
        user_messages = [m for m in messages if m["role"] == "user"]
        if not user_messages:
            return "Error: No user message provided"

        query = user_messages[-1]["content"]

        # RAG retrieval (if enabled)
        rag_context = None
        if self.enable_rag:
            try:
                rag_context = self._retrieve_rag_context_sync(query)
                if rag_context:
                    messages = self._inject_rag_context(messages, rag_context)
            except Exception as e:
                # RAG failure shouldn't block generation
                print(f"Warning: RAG retrieval failed: {e}")

        # Format prompt for llama.cpp
        prompt = self._format_messages(messages)

        # Load balance across instances
        instance = self._get_next_instance()

        # Call llama.cpp
        try:
            response = requests.post(
                f"{instance}/completion",
                json={
                    "prompt": prompt,
                    "n_predict": config.max_tokens if config and config.max_tokens else 500,
                    "temperature": config.temperature if config and config.temperature else 0.7,
                    "stop": ["\n\n\n", "Human:", "User:"],
                },
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            return result.get("content", "").strip()

        except requests.exceptions.Timeout:
            return f"Error: Request to {instance} timed out after {self.timeout}s"
        except requests.exceptions.RequestException as e:
            return f"Error: Failed to query {instance}: {e}"

    def _retrieve_rag_context_sync(self, query: str) -> Optional[str]:
        """
        Synchronous RAG context retrieval with lazy initialization.

        All async operations (init + retrieval) happen in single asyncio.run() call
        to avoid event loop conflicts.

        Args:
            query: User query for semantic search

        Returns:
            Formatted context string or None
        """
        # Run all async operations in a single event loop
        return asyncio.run(self._retrieve_rag_context_async_all(query))

    async def _retrieve_rag_context_async_all(self, query: str) -> Optional[str]:
        """
        Async wrapper that handles both initialization and retrieval.

        Creates fresh components on EVERY call to avoid event loop conflicts.
        Components cannot be reused across different asyncio.run() calls.

        Args:
            query: User query for semantic search

        Returns:
            Formatted context string or None
        """
        from src.adapters.rag import SurrealDBStore, EmbeddingPipeline

        # Create fresh components for this request
        # Cannot reuse across asyncio.run() boundaries
        embedder = EmbeddingPipeline(
            model=self.rag_config.embedding_model,
            provider=self.rag_config.embedding_provider
        )

        db = SurrealDBStore(
            url=self.rag_config.db_url,
            namespace=self.rag_config.db_namespace,
            database=self.rag_config.db_database,
            user=self.rag_config.db_user,
            password=self.rag_config.db_password
        )

        # Connect to database (async, within same event loop)
        await db.connect()

        # Retrieve context
        try:
            return await self._retrieve_rag_context(query, db, embedder)
        finally:
            # Clean up connection
            await db.close()

    def _get_next_instance(self) -> str:
        """Get next instance using round-robin load balancing."""
        return next(self._instance_cycle)

    def _format_messages(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format messages for llama.cpp completion API.

        Converts OpenAI-style message format to simple prompt.
        Adds English language enforcement for multilingual models.
        """
        prompt_parts = []

        for i, msg in enumerate(messages):
            role = msg["role"]
            content = msg["content"]

            # Prepend English instruction to first system message
            if role == "system" and i == 0:
                content = "IMPORTANT: You MUST respond in English only. All outputs must be in English.\n\n" + content
                prompt_parts.append(f"System: {content}\n")
            elif role == "system":
                prompt_parts.append(f"System: {content}\n")
            elif role == "user":
                prompt_parts.append(f"User: {content}\n")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}\n")

        # Add final prompt for assistant with English reminder
        prompt_parts.append("Assistant: (responding in English)")

        return "\n".join(prompt_parts)

    async def _retrieve_rag_context(
        self,
        query: str,
        db,
        embedder,
    ) -> Optional[str]:
        """
        Retrieve relevant code context via RAG.

        Args:
            query: User query for semantic search
            db: SurrealDB connection (thread-local)
            embedder: Embedding pipeline (thread-local)

        Returns:
            Formatted context string or None if no relevant results
        """
        if not self.enable_rag:
            return None

        # Generate query embedding
        query_emb = await embedder.embed_text(query)

        # Semantic search in SurrealDB
        top_k = self.rag_config.top_k
        result = await db.query(f"""
            SELECT name, file_path, content,
                   vector::similarity::cosine(embedding, $e) AS similarity
            FROM code_entity
            ORDER BY similarity DESC
            LIMIT {top_k}
        """, {"e": query_emb.tolist()})

        if not result:
            return None

        # Format context
        snippets = []
        for item in result:
            sim = item.get('similarity', 0)
            if sim < self.rag_config.similarity_threshold:
                continue

            snippets.append(
                f"# {item['file_path']}:{item['name']}\n"
                f"{item['content'][:self.rag_config.snippet_max_length]}\n"
            )

        if not snippets:
            return None

        return "\n".join(snippets)

    def _inject_rag_context(
        self,
        messages: List[Dict[str, Any]],
        rag_context: str
    ) -> List[Dict[str, Any]]:
        """
        Inject RAG context into messages.

        Adds retrieved code snippets before the final user message.
        """
        if not rag_context:
            return messages

        # Find last user message
        for i in range(len(messages) - 1, -1, -1):
            if messages[i]["role"] == "user":
                # Inject context before user query
                original_content = messages[i]["content"]
                messages[i]["content"] = f"""Relevant code from the codebase:

{rag_context}

---

User query: {original_content}"""
                break

        return messages
