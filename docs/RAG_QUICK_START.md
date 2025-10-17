# RAG Quick Start Guide

**Quick implementation guide for RAG architecture with SurrealDB**

---

## 1. Setup (15 minutes)

### Install Dependencies

```bash
# Install SurrealDB
curl -sSf https://install.surrealdb.com | sh

# Install Python dependencies
pip install surrealdb openai numpy python-dotenv

# Start SurrealDB
surreal start --user root --pass root file://data/surrealdb
```

### Environment Variables

```bash
# .env
OPENAI_API_KEY=sk-...
SURREALDB_URL=ws://localhost:8000
SURREALDB_NAMESPACE=atado
SURREALDB_DATABASE=rag
```

---

## 2. Schema Setup (5 minutes)

```bash
# Run schema initialization
surreal sql --conn ws://localhost:8000 --user root --pass root --ns atado --db rag < scripts/init_rag_schema.sql
```

**scripts/init_rag_schema.sql**:
```sql
-- Execution patterns table
DEFINE TABLE execution_pattern SCHEMAFULL;
DEFINE FIELD execution_id ON execution_pattern TYPE string;
DEFINE FIELD timestamp ON execution_pattern TYPE datetime;
DEFINE FIELD task_description ON execution_pattern TYPE string;
DEFINE FIELD agent_role ON execution_pattern TYPE string;
DEFINE FIELD success ON execution_pattern TYPE bool;
DEFINE FIELD latency_seconds ON execution_pattern TYPE float;
DEFINE FIELD embedding ON execution_pattern TYPE array<float>;

-- Vector index
DEFINE INDEX idx_embedding ON execution_pattern FIELDS embedding HNSW DIMENSION 1536 DIST COSINE;

-- Agent table
DEFINE TABLE agent SCHEMAFULL;
DEFINE FIELD role ON agent TYPE string;
DEFINE FIELD tier ON agent TYPE int;
DEFINE FIELD avg_success_rate ON agent TYPE float DEFAULT 0.0;

-- Team table
DEFINE TABLE team SCHEMAFULL;
DEFINE FIELD name ON team TYPE string;
DEFINE FIELD domain ON team TYPE string;

-- Relationships
DEFINE TABLE executed_by TYPE RELATION FROM execution_pattern TO agent;
DEFINE TABLE part_of TYPE RELATION FROM agent TO team;
```

---

## 3. Minimal Implementation (30 minutes)

### Step 1: Embedding Pipeline

```python
# src/adapters/rag/embedding_pipeline.py
from openai import AsyncOpenAI
import numpy as np
import os

class EmbeddingPipeline:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "text-embedding-3-small"
    
    async def embed(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        response = await self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return np.array(response.data[0].embedding)
```

### Step 2: SurrealDB Store

```python
# src/adapters/rag/surrealdb_store.py
from surrealdb import Surreal
import numpy as np
from typing import List, Dict

class SurrealDBStore:
    def __init__(self, url: str, namespace: str, database: str):
        self.url = url
        self.namespace = namespace
        self.database = database
        self.db = None
    
    async def connect(self):
        """Connect to SurrealDB."""
        self.db = Surreal()
        await self.db.connect(self.url)
        await self.db.signin({"user": "root", "pass": "root"})
        await self.db.use(self.namespace, self.database)
    
    async def store_pattern(
        self,
        execution_id: str,
        task_description: str,
        agent_role: str,
        success: bool,
        latency: float,
        embedding: np.ndarray
    ):
        """Store execution pattern."""
        await self.db.create("execution_pattern", {
            "execution_id": execution_id,
            "timestamp": "time::now()",
            "task_description": task_description,
            "agent_role": agent_role,
            "success": success,
            "latency_seconds": latency,
            "embedding": embedding.tolist()
        })
    
    async def search_similar(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5
    ) -> List[Dict]:
        """Search for similar patterns."""
        query = """
        SELECT 
            execution_id,
            task_description,
            agent_role,
            success,
            latency_seconds,
            vector::similarity::cosine(embedding, $query_embedding) AS similarity
        FROM execution_pattern
        WHERE embedding <|$top_k|> $query_embedding
        ORDER BY similarity DESC
        LIMIT $top_k
        """
        
        result = await self.db.query(query, {
            "query_embedding": query_embedding.tolist(),
            "top_k": top_k
        })
        
        return result[0]["result"] if result else []
```

### Step 3: RAG Retriever

```python
# src/adapters/rag/rag_retriever.py
from typing import List, Dict
from .embedding_pipeline import EmbeddingPipeline
from .surrealdb_store import SurrealDBStore

class RAGRetriever:
    def __init__(self, embedding_pipeline: EmbeddingPipeline, db_store: SurrealDBStore):
        self.embedding_pipeline = embedding_pipeline
        self.db_store = db_store
    
    async def retrieve_similar_patterns(
        self,
        task_description: str,
        top_k: int = 5
    ) -> List[Dict]:
        """Retrieve similar execution patterns."""
        
        # 1. Embed query
        query_embedding = await self.embedding_pipeline.embed(task_description)
        
        # 2. Search SurrealDB
        patterns = await self.db_store.search_similar(query_embedding, top_k)
        
        return patterns
```

### Step 4: Integration with TaskCoordinator

```python
# src/use_cases/rag_task_coordinator.py
from typing import List, Optional
from src.entity import Task, Agent, ExecutionResult, ExecutionContext
from src.use_cases.task_coordinator import TaskCoordinatorUseCase
from src.adapters.rag import RAGRetriever, SurrealDBStore, EmbeddingPipeline
import uuid
import time

class RAGTaskCoordinator(TaskCoordinatorUseCase):
    """
    Task coordinator with RAG pattern capture.

    Extends base coordinator to capture execution patterns.
    """

    def __init__(
        self,
        task_planner,
        agent_executor,
        rag_retriever: RAGRetriever,
        db_store: SurrealDBStore,
        embedding_pipeline: EmbeddingPipeline,
        **kwargs
    ):
        super().__init__(task_planner, agent_executor, **kwargs)
        self.rag_retriever = rag_retriever
        self.db_store = db_store
        self.embedding_pipeline = embedding_pipeline

    async def coordinate(
        self,
        tasks: List[Task],
        agents: List[Agent],
        context: Optional[ExecutionContext] = None
    ) -> List[ExecutionResult]:
        """
        Coordinate with pattern capture.
        """

        # Execute tasks (base implementation)
        results = await super().coordinate(tasks, agents, context)

        # Capture patterns for learning
        await self._capture_patterns(tasks, agents, results)

        return results

    async def _capture_patterns(
        self,
        tasks: List[Task],
        agents: List[Agent],
        results: List[ExecutionResult]
    ):
        """Capture execution patterns to SurrealDB."""

        for task, result in zip(tasks, results):
            # Extract agent from result metadata
            agent_role = result.metadata.get("agent_role", "unknown")

            # Generate embedding
            embedding = await self.embedding_pipeline.embed(task.description)

            # Store pattern
            await self.db_store.store_pattern(
                execution_id=str(uuid.uuid4()),
                task_description=task.description,
                agent_role=agent_role,
                success=(result.status.value == "success"),
                latency=result.metadata.get("latency_seconds", 0.0),
                embedding=embedding
            )
```

---

## 4. Usage Example (5 minutes)

```python
# example_rag_usage.py
import asyncio
from src.adapters.rag import EmbeddingPipeline, SurrealDBStore, RAGRetriever
from src.use_cases.rag_task_coordinator import RAGTaskCoordinator
from src.entity import Task, Agent
import os

async def main():
    # 1. Initialize RAG components
    embedding_pipeline = EmbeddingPipeline()

    db_store = SurrealDBStore(
        url=os.getenv("SURREALDB_URL"),
        namespace=os.getenv("SURREALDB_NAMESPACE"),
        database=os.getenv("SURREALDB_DATABASE")
    )
    await db_store.connect()

    rag_retriever = RAGRetriever(embedding_pipeline, db_store)

    # 2. Create task coordinator with RAG
    coordinator = RAGTaskCoordinator(
        task_planner=...,  # Your task planner
        agent_executor=...,  # Your agent executor
        rag_retriever=rag_retriever,
        db_store=db_store,
        embedding_pipeline=embedding_pipeline
    )

    # 3. Execute tasks (patterns automatically captured)
    tasks = [
        Task(description="Implement user authentication", priority=1),
        Task(description="Write unit tests for auth module", priority=2)
    ]

    agents = [
        Agent(role="backend-specialist", capabilities=["python", "auth"], tier=3),
        Agent(role="test-engineer", capabilities=["pytest", "testing"], tier=3)
    ]

    results = await coordinator.coordinate(tasks, agents)

    # 4. Retrieve similar patterns for new task
    new_task = "Add OAuth2 support to authentication"
    similar_patterns = await rag_retriever.retrieve_similar_patterns(new_task, top_k=3)

    print(f"\nSimilar patterns for '{new_task}':")
    for pattern in similar_patterns:
        print(f"  - {pattern['task_description']}")
        print(f"    Agent: {pattern['agent_role']}")
        print(f"    Success: {pattern['success']}")
        print(f"    Similarity: {pattern['similarity']:.3f}\n")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 5. Testing (10 minutes)

### Test 1: Embedding Generation

```python
# tests/test_embedding_pipeline.py
import pytest
from src.adapters.rag.embedding_pipeline import EmbeddingPipeline

@pytest.mark.asyncio
async def test_embedding_generation():
    pipeline = EmbeddingPipeline()

    text = "Implement user authentication"
    embedding = await pipeline.embed(text)

    assert embedding.shape == (1536,)  # OpenAI text-embedding-3-small
    assert embedding.dtype == np.float64
```

### Test 2: Pattern Storage

```python
# tests/test_surrealdb_store.py
import pytest
from src.adapters.rag.surrealdb_store import SurrealDBStore
import numpy as np

@pytest.mark.asyncio
async def test_pattern_storage():
    store = SurrealDBStore("ws://localhost:8000", "test", "rag")
    await store.connect()

    embedding = np.random.rand(1536)

    await store.store_pattern(
        execution_id="test-123",
        task_description="Test task",
        agent_role="test-agent",
        success=True,
        latency=1.5,
        embedding=embedding
    )

    # Verify storage
    patterns = await store.search_similar(embedding, top_k=1)
    assert len(patterns) == 1
    assert patterns[0]["execution_id"] == "test-123"
```

### Test 3: RAG Retrieval

```python
# tests/test_rag_retriever.py
import pytest
from src.adapters.rag import RAGRetriever, EmbeddingPipeline, SurrealDBStore

@pytest.mark.asyncio
async def test_rag_retrieval():
    pipeline = EmbeddingPipeline()
    store = SurrealDBStore("ws://localhost:8000", "test", "rag")
    await store.connect()

    retriever = RAGRetriever(pipeline, store)

    # Store some patterns
    await store.store_pattern(
        execution_id="pattern-1",
        task_description="Implement authentication",
        agent_role="backend-specialist",
        success=True,
        latency=2.0,
        embedding=await pipeline.embed("Implement authentication")
    )

    # Retrieve similar
    patterns = await retriever.retrieve_similar_patterns(
        "Add OAuth2 authentication",
        top_k=1
    )

    assert len(patterns) == 1
    assert patterns[0]["agent_role"] == "backend-specialist"
    assert patterns[0]["similarity"] > 0.7  # High similarity
```

---

## 6. Monitoring (5 minutes)

### Basic Metrics

```python
# src/adapters/rag/rag_metrics.py
from dataclasses import dataclass
from typing import List

@dataclass
class RAGMetrics:
    total_patterns: int
    avg_retrieval_latency: float
    avg_similarity_score: float
    cache_hit_rate: float

async def collect_metrics(db_store: SurrealDBStore) -> RAGMetrics:
    """Collect RAG metrics from SurrealDB."""

    # Total patterns
    result = await db_store.db.query("SELECT count() FROM execution_pattern")
    total_patterns = result[0]["result"][0]["count"]

    # Avg similarity (from recent retrievals)
    # ... implement based on your logging

    return RAGMetrics(
        total_patterns=total_patterns,
        avg_retrieval_latency=0.0,  # Implement
        avg_similarity_score=0.0,  # Implement
        cache_hit_rate=0.0  # Implement
    )
```

### Dashboard Query

```sql
-- SurrealDB: Get performance summary
SELECT
    count() AS total_patterns,
    math::mean(latency_seconds) AS avg_latency,
    math::sum(success) / count() AS success_rate,
    count(DISTINCT agent_role) AS unique_agents
FROM execution_pattern
WHERE timestamp > time::now() - 7d;
```

---

## 7. Troubleshooting

### Issue 1: Slow Vector Search

**Symptom**: Queries take >1 second

**Solution**:
```sql
-- Verify HNSW index exists
INFO FOR TABLE execution_pattern;

-- Rebuild index if needed
REMOVE INDEX idx_embedding ON execution_pattern;
DEFINE INDEX idx_embedding ON execution_pattern FIELDS embedding HNSW DIMENSION 1536 DIST COSINE;
```

### Issue 2: Low Similarity Scores

**Symptom**: All similarity scores < 0.5

**Solution**:
- Check embedding model consistency (same model for storage and retrieval)
- Verify embedding dimensions match (1536 for text-embedding-3-small)
- Inspect task descriptions (too generic or too specific)

### Issue 3: Connection Errors

**Symptom**: `ConnectionRefusedError`

**Solution**:
```bash
# Check SurrealDB is running
ps aux | grep surreal

# Restart SurrealDB
surreal start --user root --pass root file://data/surrealdb

# Test connection
surreal sql --conn ws://localhost:8000 --user root --pass root
```

---

## 8. Next Steps

1. **Scale Up**: Add more execution patterns (target: 1,000+)
2. **Optimize**: Tune retrieval parameters (top_k, similarity threshold)
3. **Enhance**: Add graph relationships (executed_by, part_of edges)
4. **Monitor**: Set up Grafana dashboard for metrics
5. **Iterate**: A/B test RAG vs baseline routing

---

## Resources

- **Full Architecture**: `docs/RAG_ARCHITECTURE_SURREALDB.md`
- **SurrealDB Docs**: https://surrealdb.com/docs
- **OpenAI Embeddings**: https://platform.openai.com/docs/guides/embeddings
- **ATADO Codebase**: `src/`

---

**Quick Start Complete!** 🎉

You now have a working RAG system. Next: Collect 100+ execution patterns and measure improvement.
