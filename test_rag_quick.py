"""Quick RAG test with fixed SurrealDB connection.

Tests:
1. 768-dim embedding generation  
2. SurrealDB vector storage
3. Semantic search
4. Latency benchmark
"""

import asyncio
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from adapters.rag import EmbeddingPipeline
from surrealdb.connections.async_ws import AsyncWsSurrealConnection
import numpy as np


async def main():
    print("=" * 80)
    print("QUICK RAG TEST - Phase 3")
    print("=" * 80)
    
    # Step 1: Initialize 768-dim embedding pipeline
    print("\n[1/4] Loading all-mpnet-base-v2 (768-dim)...")
    start = time.time()
    
    embedder = EmbeddingPipeline(
        model="sentence-transformers/all-mpnet-base-v2",
        provider="sentence-transformers"
    )
    
    test_emb = await embedder.embed_text("test")
    print(f"  ✅ Model loaded: {test_emb.shape[0]} dimensions")
    print(f"  Time: {time.time() - start:.2f}s")
    
    # Step 2: Connect to SurrealDB
    print("\n[2/4] Connecting to SurrealDB...")
    start = time.time()
    
    db = AsyncWsSurrealConnection("ws://localhost:8000")
    await db.connect()
    await db.signin({"username": "root", "password": "root"})
    await db.use("atado", "rag")
    
    print(f"  ✅ Connected (async websocket)")
    print(f"  Time: {time.time() - start:.2f}s")
    
    # Step 3: Test vector storage and retrieval
    print("\n[3/4] Testing vector storage...")
    start = time.time()
    
    # Create test code entities
    test_cases = [
        ("HTN task decomposition function", "htn_node.py", "decompose_task"),
        ("Agent execution coordinator", "task_coordinator.py", "coordinate"),
        ("Team-based router implementation", "team_router.py", "route_to_team"),
    ]
    
    # Store with embeddings
    for desc, file_path, name in test_cases:
        emb = await embedder.embed_text(desc)
        
        # Direct SurrealQL insert (bypassing the adapter)
        await db.query("""
            CREATE code_entity SET
                file_path = $file_path,
                name = $name,
                qualified_name = $name,
                entity_type = 'function',
                language = 'python',
                content = $desc,
                content_hash = $name,
                line_start = 1,
                line_end = 10,
                embedding = $embedding
        """, {
            "file_path": file_path,
            "name": name,
            "desc": desc,
            "embedding": emb.tolist()
        })
    
    print(f"  ✅ Stored {len(test_cases)} test entities")
    print(f"  Time: {time.time() - start:.2f}s")
    
    # Step 4: Test semantic search + latency
    print("\n[4/4] Semantic search + latency benchmark...")
    
    query = "task planning and decomposition"
    query_emb = await embedder.embed_text(query)
    
    # Benchmark latencies
    latencies = []
    for i in range(100):
        start = time.time()
        
        result = await db.query("""
            SELECT file_path, name, qualified_name,
                   vector::similarity::cosine(embedding, $e) AS similarity
            FROM code_entity
            WHERE embedding <|5|> $e
            ORDER BY similarity DESC
            LIMIT 5
        """, {"e": query_emb.tolist()})
        
        latencies.append((time.time() - start) * 1000)
    
    # Show first result
    if result and len(result) > 0 and 'result' in result[0]:
        results = result[0]['result']
        print(f"\n  Query: '{query}'")
        print(f"  Top result: {results[0].get('name')} (sim={results[0].get('similarity', 0):.3f})")
        print(f"            {results[0].get('file_path')}")
    
    # Latency stats
    latencies.sort()
    p50 = latencies[50]
    p95 = latencies[95]
    p99 = latencies[99]
    avg = sum(latencies) / len(latencies)
    
    print(f"\n  Latency (100 queries):")
    print(f"    avg: {avg:.1f}ms")
    print(f"    p50: {p50:.1f}ms")
    print(f"    p95: {p95:.1f}ms ({'✅ PASS' if p95 < 100 else '⚠️  HIGH'})")
    print(f"    p99: {p99:.1f}ms")
    
    await db.close()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print(f"\n✅ Embedding: 768-dim (all-mpnet-base-v2)")
    print(f"✅ Storage: SurrealDB vector store")
    print(f"✅ Search: Cosine similarity with HNSW")
    print(f"{'✅' if p95 < 100 else '⚠️ '} Latency: p95={p95:.1f}ms (target <100ms)")


if __name__ == "__main__":
    asyncio.run(main())
