"""Async Text Generator Interface - Modern async-native LLM interface.

Clean Architecture: Abstract interface for dependency inversion.

This is the async-native evolution of ITextGenerator, designed to eliminate
sync/async boundary issues with RAG and other async components.

Migration Path:
- New adapters should implement IAsyncTextGenerator
- Legacy adapters can continue using ITextGenerator
- LLMAgentExecutor supports both (detects at runtime)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from src.interface.llm_provider import LLMConfig, GenerationResult


class IAsyncTextGenerator(ABC):
    """
    Async text generation interface for LLM providers.

    Benefits over sync ITextGenerator:
    1. No event loop conflicts with async components (RAG, DB, etc.)
    2. Enables connection reuse and pooling
    3. Natural async composition
    4. Better performance (no asyncio.run() overhead)

    Example Implementation:

    ```python
    class MyLLMAdapter(IAsyncTextGenerator):
        def __init__(self):
            self.db = None  # Lazy init

        async def generate(self, messages, config):
            # Initialize async components once
            if not self.db:
                self.db = await connect_to_db()

            # Use components naturally
            context = await self.db.query(...)
            return await self.llm.complete(messages)
    ```
    """

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None
    ) -> GenerationResult:
        """
        Generate text response asynchronously.

        Args:
            messages: Conversation in standard format
                     [{"role": "system", "content": "..."},
                      {"role": "user", "content": "..."}]
            config: Optional LLM configuration (temperature, max_tokens, etc.)

        Returns:
            GenerationResult containing:
                - content: Generated text response
                - usage: Token usage (prompt_tokens, completion_tokens, total_tokens)
                - metadata: Optional additional metadata

        Raises:
            Exception: On generation failure (implementation-specific)

        Note:
            Implementations should handle initialization of async resources
            (DB connections, embedding models) lazily on first call and
            reuse them across subsequent calls within the same event loop.
        """
        pass

    async def close(self) -> None:
        """
        Clean up async resources (connections, sessions, etc.).

        Optional method. Implementations should override if they manage
        long-lived async resources that need explicit cleanup.

        Called when:
        - Agent execution completes
        - LLMAgentExecutor is destroyed
        - Application shutdown

        Default: No-op (override if needed)
        """
        pass
