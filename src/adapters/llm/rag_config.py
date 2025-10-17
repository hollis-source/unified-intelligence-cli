"""RAG configuration for lazy initialization in GraniteAdapter.

Clean Architecture: Configuration object for dependency injection.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RAGConfig:
    """
    Configuration for RAG components.

    Used for lazy initialization to avoid event loop conflicts.
    Components are created fresh in each thread that needs them.
    """

    # SurrealDB connection
    db_url: str = "ws://localhost:8000"
    db_namespace: str = "atado"
    db_database: str = "rag"
    db_user: str = "root"
    db_password: str = "root"

    # Embedding model
    embedding_model: str = "sentence-transformers/all-mpnet-base-v2"
    embedding_provider: str = "sentence-transformers"

    # RAG retrieval parameters
    top_k: int = 3
    similarity_threshold: float = 0.5
    snippet_max_length: int = 800

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"RAGConfig(db={self.db_url}/{self.db_namespace}/{self.db_database}, "
            f"model={self.embedding_model}, top_k={self.top_k})"
        )
