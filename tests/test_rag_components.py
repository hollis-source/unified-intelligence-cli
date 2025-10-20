"""Unit tests for RAG components.

Tests:
- SurrealDBStore (basic functionality)
- EmbeddingPipeline (basic functionality)
- RAGTeamRouter (integration)
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.rag.embedding_pipeline import EmbeddingPipeline
from src.routing.rag_team_router import RAGTeamRouter


class TestSurrealDBStore:
    """Unit tests for SurrealDBStore."""
    
    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to SurrealDB."""
        store = SurrealDBStore(
            url="ws://localhost:8000",
            namespace="test",
            database="test",
            user="root",
            password="root"
        )
        
        # Mock the AsyncSurreal client
        with patch('src.adapters.rag.surrealdb_store.AsyncSurreal') as mock_surreal:
            mock_db = AsyncMock()
            mock_surreal.return_value = mock_db
            
            await store.connect()
            
            # Verify connection sequence
            mock_db.connect.assert_called_once()
            mock_db.signin.assert_called_once_with({"username": "root", "password": "root"})
            mock_db.use.assert_called_once_with("test", "test")
    
    @pytest.mark.asyncio
    async def test_store_execution_log(self):
        """Test storing execution log."""
        store = SurrealDBStore(
            url="ws://localhost:8000",
            namespace="test",
            database="test"
        )

        with patch('src.adapters.rag.surrealdb_store.AsyncSurreal') as mock_surreal:
            mock_db = AsyncMock()
            mock_surreal.return_value = mock_db
            await store.connect()

            # Test storing execution log with correct parameters
            embedding = np.random.rand(1536)
            await store.store_execution_log(
                execution_id="test-123",
                task_description="Test task",
                task_domain="testing",
                agent_role="test-agent",
                team_id="test-team",
                success=True,
                status="completed",
                latency_seconds=1.0,
                output_excerpt="Test output",
                embedding=embedding,
                embedding_model="text-embedding-3-small"
            )

            # Verify query was called
            mock_db.query.assert_called()
    
    @pytest.mark.asyncio
    async def test_search_similar_execution(self):
        """Test searching for similar executions."""
        store = SurrealDBStore(
            url="ws://localhost:8000",
            namespace="test",
            database="test"
        )
        
        with patch('src.adapters.rag.surrealdb_store.AsyncSurreal') as mock_surreal:
            mock_db = AsyncMock()
            mock_surreal.return_value = mock_db
            
            # Mock query result
            mock_db.query.return_value = [{
                "result": [
                    {
                        "task_description": "Similar task",
                        "agent_role": "test-agent",
                        "similarity": 0.95
                    }
                ]
            }]
            
            await store.connect()
            
            # Test search
            query_embedding = np.random.rand(1536)
            results = await store.search_similar_execution(
                query_embedding=query_embedding,
                top_k=5,
                success_only=True
            )
            
            # Verify results
            assert len(results) == 1
            assert results[0]["similarity"] == 0.95
    
    @pytest.mark.asyncio
    async def test_store_routing_decision(self):
        """Test storing routing decision."""
        store = SurrealDBStore(
            url="ws://localhost:8000",
            namespace="test",
            database="test"
        )
        
        with patch('src.adapters.rag.surrealdb_store.AsyncSurreal') as mock_surreal:
            mock_db = AsyncMock()
            mock_surreal.return_value = mock_db
            await store.connect()
            
            # Test storing routing decision
            await store.store_routing_decision(
                task_id="test-123",
                task_description="Test task",
                task_domain="testing",
                selected_agent="test-agent",
                selected_team="test-team",
                routing_strategy="rag",
                confidence=0.85,
                success=None,
                fallback_used=False,
                metadata={"test": "data"}
            )
            
            # Verify query was called
            mock_db.query.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_routing_accuracy(self):
        """Test calculating routing accuracy."""
        store = SurrealDBStore(
            url="ws://localhost:8000",
            namespace="test",
            database="test"
        )
        
        with patch('src.adapters.rag.surrealdb_store.AsyncSurreal') as mock_surreal:
            mock_db = AsyncMock()
            mock_surreal.return_value = mock_db
            
            # Mock query result - 3 successful, 1 failed
            mock_db.query.return_value = [
                {"success": True},
                {"success": True},
                {"success": True},
                {"success": False}
            ]
            
            await store.connect()
            
            # Test accuracy calculation
            accuracy = await store.get_routing_accuracy(strategy="rag", limit=100)
            
            # Verify accuracy is 75% (3/4)
            assert accuracy == 75.0


class TestEmbeddingPipeline:
    """Unit tests for EmbeddingPipeline."""

    def test_init_default(self):
        """Test EmbeddingPipeline initialization with defaults."""
        pipeline = EmbeddingPipeline()

        # Should default to sentence-transformers if no OPENAI_API_KEY
        assert pipeline.provider in ["openai", "sentence-transformers"]
        assert pipeline.model is not None

    def test_init_openai(self):
        """Test EmbeddingPipeline initialization with OpenAI."""
        pipeline = EmbeddingPipeline(
            model="text-embedding-3-small",
            provider="openai"
        )

        assert pipeline.provider == "openai"
        assert pipeline.model == "text-embedding-3-small"

    def test_init_sentence_transformers(self):
        """Test EmbeddingPipeline initialization with sentence-transformers."""
        pipeline = EmbeddingPipeline(
            model="all-MiniLM-L6-v2",
            provider="sentence-transformers"
        )

        assert pipeline.provider == "sentence-transformers"
        assert pipeline.model == "all-MiniLM-L6-v2"

    @pytest.mark.asyncio
    async def test_embed_text_with_mock(self):
        """Test text embedding with mocked OpenAI."""
        pipeline = EmbeddingPipeline(
            model="text-embedding-3-small",
            provider="openai"
        )

        # Mock OpenAI client
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch('openai.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client

                # Mock embedding response
                mock_response = Mock()
                mock_response.data = [Mock(embedding=[0.1] * 1536)]
                mock_client.embeddings.create.return_value = mock_response

                # Test embedding
                embedding = await pipeline.embed_text("Test text")

                # Verify embedding
                assert isinstance(embedding, np.ndarray)
                assert len(embedding) == 1536


class TestRAGTeamRouter:
    """Unit tests for RAGTeamRouter."""

    def test_init(self):
        """Test RAGTeamRouter initialization."""
        from src.routing.domain_classifier import DomainClassifier

        mock_store = Mock()
        mock_embedder = Mock()
        classifier = DomainClassifier()

        router = RAGTeamRouter(
            domain_classifier=classifier,
            db_store=mock_store,
            embedding_pipeline=mock_embedder,
            top_k=3,
            similarity_threshold=0.5
        )

        assert router.domain_classifier == classifier
        assert router.db_store == mock_store
        assert router.embedding_pipeline == mock_embedder
        assert router.top_k == 3
        assert router.similarity_threshold == 0.5

    def test_fallback_to_base_routing(self):
        """Test that RAGTeamRouter falls back to base routing."""
        from src.routing.domain_classifier import DomainClassifier
        from src.entity import Task
        from src.factories.team_factory import TeamFactory

        mock_store = Mock()
        mock_embedder = Mock()
        classifier = DomainClassifier()

        router = RAGTeamRouter(
            domain_classifier=classifier,
            db_store=mock_store,
            embedding_pipeline=mock_embedder
        )

        # Create a simple task
        task = Task(task_id="test-1", description="Create REST API endpoint")

        # Create teams
        team_factory = TeamFactory()
        teams = team_factory.create_default_teams()

        # Test base routing (sync method)
        agent = router.route(task, teams)

        # Should return an agent
        assert agent is not None
        assert hasattr(agent, 'role')


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

