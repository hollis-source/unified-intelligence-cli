"""Granite LLM adapter - Integrates IBM Granite 4.0-H with ATADO via llama.cpp.

Clean Architecture: Implements ITextGenerator interface for dependency inversion.

Features:
- Load balancing across multiple llama.cpp instances (round-robin)
- Optional RAG context injection for codebase-aware responses
- 512K context window support
- Zero-cost local inference
"""

import requests
from typing import List, Dict, Any, Optional
import itertools
import asyncio
import concurrent.futures

from src.interface import ITextGenerator, LLMConfig


class GraniteAdapter(ITextGenerator):
    """
    IBM Granite 4.0-H adapter with RAG support.
    
    Deployment: llama.cpp servers (2 instances × 512K context × Q8_0 cache)
    Performance: 15.67 tok/s per instance, 31.34 tok/s aggregate
    
    Architecture:
        User Query → RAG Retrieval (optional) → Load Balancer → llama.cpp → Response
    """
    
    def __init__(
        self,
        instances: Optional[List[str]] = None,
        enable_rag: bool = False,
        rag_db=None,
        rag_embedder=None,
        timeout: int = 300
    ):
        """
        Initialize Granite adapter.
        
        Args:
            instances: List of llama.cpp server URLs
            enable_rag: Enable RAG context injection
            rag_db: SurrealDB connection for RAG (if enable_rag=True)
            rag_embedder: Embedding pipeline for RAG (if enable_rag=True)
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
        
        # RAG components (optional)
        if enable_rag:
            if not rag_db or not rag_embedder:
                raise ValueError("RAG enabled but rag_db or rag_embedder not provided")
            self.rag_db = rag_db
            self.rag_embedder = rag_embedder
    
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
                # Run async RAG retrieval in thread pool to avoid event loop conflicts
                # This works whether or not we're already in an event loop
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self._run_rag_sync, query)
                    rag_context = future.result(timeout=30)

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
    
    def _run_rag_sync(self, query: str) -> Optional[str]:
        """
        Synchronous wrapper for async RAG retrieval.

        Runs async code in a completely isolated thread to avoid event loop conflicts.

        Args:
            query: User query for semantic search

        Returns:
            Formatted context string or None
        """
        import threading

        result_container = {"result": None, "error": None}

        def run_async_in_thread():
            """Run async code in isolated thread with its own event loop."""
            try:
                # Create a fresh event loop for this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    # Run the coroutine
                    result_container["result"] = new_loop.run_until_complete(
                        self._retrieve_rag_context(query)
                    )
                finally:
                    new_loop.close()
            except Exception as e:
                result_container["error"] = e

        # Run in separate thread to completely isolate from any existing event loops
        thread = threading.Thread(target=run_async_in_thread, daemon=True)
        thread.start()
        thread.join(timeout=30)

        if thread.is_alive():
            raise TimeoutError("RAG retrieval timed out after 30s")

        if result_container["error"]:
            raise result_container["error"]

        return result_container["result"]

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
        top_k: int = 3
    ) -> Optional[str]:
        """
        Retrieve relevant code context via RAG.
        
        Args:
            query: User query for semantic search
            top_k: Number of code snippets to retrieve
        
        Returns:
            Formatted context string or None if no relevant results
        """
        if not self.enable_rag:
            return None
        
        # Generate query embedding
        query_emb = await self.rag_embedder.embed_text(query)
        
        # Semantic search in SurrealDB
        result = await self.rag_db.query(f"""
            SELECT name, file_path, content,
                   vector::similarity::cosine(embedding, $e) AS similarity
            FROM code_entity
            ORDER BY similarity DESC
            LIMIT {top_k}
        """, {"e": query_emb.tolist()})
        
        if not result or not result[0].get('result'):
            return None
        
        # Format context
        snippets = []
        for item in result[0]['result']:
            if item.get('similarity', 0) < 0.5:  # Relevance threshold
                continue
            
            snippets.append(
                f"# {item['file_path']}:{item['name']}\n"
                f"{item['content'][:800]}\n"  # Limit snippet length
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

Question: {original_content}

Please answer based on the code context provided above."""
                break
        
        return messages
    
    def supports_streaming(self) -> bool:
        """Check if streaming is supported (currently: no)."""
        return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Return model information."""
        return {
            "model": "IBM Granite 4.0-H Small (32B-A9B)",
            "context_window": 524288,  # 512K
            "instances": len(self.instances),
            "performance": "15.67 tok/s per instance",
            "rag_enabled": self.enable_rag
        }
