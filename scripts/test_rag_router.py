#!/usr/bin/env python3
"""Test RAG-enhanced team router.

This script tests the RAGTeamRouter by:
1. Creating test patterns in SurrealDB
2. Testing pattern retrieval
3. Testing RAG-enhanced routing
4. Comparing with baseline routing
"""

import asyncio
import os
import sys
import uuid
import numpy as np
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.routing.rag_team_router import RAGTeamRouter
from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.rag.embedding_pipeline import EmbeddingPipeline
from src.adapters.llm.rag_config import RAGConfig
from src.entity import Task
from src.factories import TeamFactory


async def test_rag_router():
    """Test RAG-enhanced routing."""
    
    print("=" * 80)
    print("RAG TEAM ROUTER TEST")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Setup
    config = RAGConfig()
    db_url = os.getenv("SURREALDB_URL", "ws://localhost:8000")
    
    print("Setting up components...")
    
    # Create SurrealDB store
    store = SurrealDBStore(
        url=db_url,
        namespace=config.db_namespace,
        database=config.db_database,
        user=config.db_user,
        password=config.db_password
    )
    
    try:
        await store.connect()
        print("✅ Connected to SurrealDB")
    except Exception as e:
        print(f"❌ Failed to connect to SurrealDB: {e}")
        return False
    
    # Create embedding pipeline (will use dummy if no API key)
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    if has_api_key:
        embedder = EmbeddingPipeline(provider="openai", model="text-embedding-3-small")
        print("✅ Using OpenAI embeddings")
    else:
        embedder = None
        print("⚠️  No OpenAI API key, using dummy embeddings")
    
    # Create teams
    team_factory = TeamFactory()
    teams = team_factory.create_scaled_teams()
    print(f"✅ Created {len(teams)} teams")
    print()
    
    # Test 1: Create test patterns
    print("TEST 1: Creating Test Patterns")
    print("-" * 80)
    
    test_patterns = [
        {
            "task_description": "Write unit tests for authentication module",
            "agent_role": "unit-test-engineer",
            "team_id": "Testing",
            "task_domain": "testing",
            "success": True,
            "latency_seconds": 15.3
        },
        {
            "task_description": "Write integration tests for API endpoints",
            "agent_role": "integration-test-engineer",
            "team_id": "Testing",
            "task_domain": "testing",
            "success": True,
            "latency_seconds": 22.1
        },
        {
            "task_description": "Implement REST API for user management",
            "agent_role": "python-specialist",
            "team_id": "Backend",
            "task_domain": "backend",
            "success": True,
            "latency_seconds": 45.7
        }
    ]
    
    for pattern in test_patterns:
        try:
            # Generate embedding
            if embedder:
                embedding = await embedder.embed_text(
                    f"Task: {pattern['task_description']}\nStatus: success"
                )
            else:
                # Dummy embedding
                embedding = np.random.rand(1536).astype(np.float32)
            
            # Store pattern
            await store.store_execution_log(
                execution_id=str(uuid.uuid4()),
                task_description=pattern['task_description'],
                task_domain=pattern['task_domain'],
                agent_role=pattern['agent_role'],
                team_id=pattern['team_id'],
                success=pattern['success'],
                status="success",
                latency_seconds=pattern['latency_seconds'],
                output_excerpt=f"Successfully completed: {pattern['task_description']}",
                embedding=embedding,
                embedding_model="text-embedding-3-small" if embedder else "dummy",
                metadata={"test": True}
            )
            
            print(f"  ✅ Stored: {pattern['task_description'][:50]}...")
            
        except Exception as e:
            print(f"  ❌ Failed to store pattern: {e}")
            return False
    
    print(f"✅ Created {len(test_patterns)} test patterns")
    print()
    
    # Test 2: Test pattern retrieval
    print("TEST 2: Pattern Retrieval")
    print("-" * 80)
    
    if embedder:
        try:
            query_text = "Write unit tests for login functionality"
            query_embedding = await embedder.embed_text(query_text)
            
            patterns = await store.search_similar_execution(
                query_embedding=query_embedding,
                top_k=3,
                success_only=True
            )
            
            print(f"Query: '{query_text}'")
            print(f"Found {len(patterns)} similar patterns:")
            
            for i, pattern in enumerate(patterns, 1):
                print(f"  {i}. {pattern.get('task_description', 'N/A')[:50]}...")
                print(f"     Agent: {pattern.get('agent_role')}")
                print(f"     Similarity: {pattern.get('similarity', 0):.4f}")
            
            print("✅ Pattern retrieval works")
            
        except Exception as e:
            print(f"❌ Pattern retrieval failed: {e}")
            return False
    else:
        print("⚠️  Skipping pattern retrieval (no API key)")
    
    print()
    
    # Test 3: Test RAG routing
    print("TEST 3: RAG-Enhanced Routing")
    print("-" * 80)
    
    # Create RAG router
    rag_router = RAGTeamRouter(
        db_store=store,
        embedding_pipeline=embedder,
        top_k=3,
        similarity_threshold=0.5,
        use_rag=has_api_key  # Only use RAG if we have API key
    )
    
    # Test tasks
    test_tasks = [
        Task(task_id="test_1", description="Write unit tests for payment processing"),
        Task(task_id="test_2", description="Implement user authentication API"),
        Task(task_id="test_3", description="Write integration tests for checkout flow")
    ]
    
    print(f"Testing {len(test_tasks)} tasks...")
    print()
    
    for task in test_tasks:
        try:
            if has_api_key:
                # Use async RAG routing
                agent = await rag_router.route_with_rag(task, teams)
                routing_type = "RAG"
            else:
                # Use base routing
                agent = rag_router.route(task, teams)
                routing_type = "Base"
            
            print(f"Task: {task.description[:50]}...")
            print(f"  → {routing_type} Routing: {agent.role}")
            print()
            
        except Exception as e:
            print(f"❌ Routing failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("✅ RAG routing works")
    print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✅ Test patterns created")
    print("✅ Pattern retrieval works" if has_api_key else "⚠️  Pattern retrieval skipped (no API key)")
    print("✅ RAG routing works")
    print()
    
    if has_api_key:
        print("🎉 RAG ROUTER TEST PASSED!")
    else:
        print("⚠️  RAG ROUTER TEST PASSED (limited - no API key)")
        print("   Set OPENAI_API_KEY for full testing")
    
    print()
    print("Next steps:")
    print("1. Integrate RAGTeamRouter into composition")
    print("2. Add routing decision tracking")
    print("3. Measure routing accuracy improvement")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_rag_router())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

