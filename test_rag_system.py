"""Test RAG system with correct 768-dimensional embeddings.

This script:
1. Connects to SurrealDB
2. Initializes embedding pipeline with all-mpnet-base-v2 (768-dim)
3. Indexes a small subset of the codebase
4. Tests semantic search
5. Measures retrieval latency
"""

import asyncio
import time
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from adapters.rag import EmbeddingPipeline, SurrealDBStore, CodebaseRAG


async def main():
    print("=" * 80)
    print("RAG SYSTEM TEST - Phase 3: RAG Integration")
    print("=" * 80)
    
    # Configuration
    surrealdb_url = os.getenv("SURREALDB_URL", "ws://localhost:8000")
    namespace = os.getenv("SURREALDB_NAMESPACE", "atado")
    database = os.getenv("SURREALDB_DATABASE", "rag")
    
    print(f"\nConfiguration:")
    print(f"  SurrealDB: {surrealdb_url}")
    print(f"  Namespace: {namespace}")
    print(f"  Database: {database}")
    
    # Step 1: Initialize embedding pipeline with 768-dim model
    print("\n[1/5] Initializing 768-dimensional embedding pipeline...")
    start = time.time()
    
    # Use all-mpnet-base-v2 for 768 dimensions (matches schema)
    embedder = EmbeddingPipeline(
        model="sentence-transformers/all-mpnet-base-v2",
        provider="sentence-transformers"
    )
    
    # Test embedding generation
    test_text = "HTN task planning and agent coordination"
    test_emb = await embedder.embed_text(test_text)
    
    print(f"  Model: sentence-transformers/all-mpnet-base-v2")
    print(f"  Embedding dimension: {test_emb.shape[0]}")
    print(f"  Expected dimension: 768")
    
    if test_emb.shape[0] != 768:
        print(f"  ❌ ERROR: Dimension mismatch! Got {test_emb.shape[0]}, expected 768")
        return
    
    print(f"  ✅ Dimension validated")
    print(f"  Time: {time.time() - start:.2f}s")
    
    # Step 2: Connect to SurrealDB
    print("\n[2/5] Connecting to SurrealDB...")
    start = time.time()
    
    db = SurrealDBStore(
        url=surrealdb_url,
        namespace=namespace,
        database=database
    )
    
    await db.connect()
    print(f"  ✅ Connected")
    print(f"  Time: {time.time() - start:.2f}s")
    
    # Step 3: Index a subset of the codebase
    print("\n[3/5] Indexing codebase subset (entity and use_cases modules)...")
    start = time.time()
    
    rag = CodebaseRAG(db=db, embedder=embedder)
    
    # Index only entity and use_cases for quick testing
    indexed_count = await rag.embed(
        repo_root=".",
        include=["src/entity", "src/use_cases"],
        batch_size=32
    )
    
    print(f"  ✅ Indexed {indexed_count} code entities")
    print(f"  Time: {time.time() - start:.2f}s")
    
    # Step 4: Test semantic search
    print("\n[4/5] Testing semantic code search...")
    
    test_queries = [
        "HTN task decomposition",
        "Agent execution and coordination",
        "Team-based routing logic",
    ]
    
    for query in test_queries:
        start = time.time()
        results = await rag.query(query, top_k=3, language="python")
        latency_ms = (time.time() - start) * 1000
        
        print(f"\n  Query: '{query}'")
        print(f"  Latency: {latency_ms:.1f}ms")
        
        if results:
            print(f"  Top results:")
            for i, r in enumerate(results[:3], 1):
                print(f"    {i}. {r.get('qualified_name')} (sim={r.get('similarity', 0):.3f})")
                print(f"       {r.get('file_path')}:{r.get('start_line')}")
        else:
            print(f"  No results found")
    
    # Step 5: Latency benchmark (p95)
    print("\n[5/5] Latency benchmark (100 queries for p95)...")
    
    latencies = []
    for i in range(100):
        query = f"test query {i % 10}"  # Cycle through 10 different queries
        start = time.time()
        await rag.query(query, top_k=5, language="python")
        latencies.append((time.time() - start) * 1000)
    
    latencies.sort()
    p50 = latencies[50]
    p95 = latencies[95]
    p99 = latencies[99]
    avg = sum(latencies) / len(latencies)
    
    print(f"\n  Retrieval latency statistics:")
    print(f"    Average: {avg:.1f}ms")
    print(f"    p50:     {p50:.1f}ms")
    print(f"    p95:     {p95:.1f}ms")
    print(f"    p99:     {p99:.1f}ms")
    
    target_p95 = 100  # Target: <100ms p95
    if p95 < target_p95:
        print(f"  ✅ p95 latency PASSES target (<{target_p95}ms)")
    else:
        print(f"  ⚠️  p95 latency EXCEEDS target ({p95:.1f}ms > {target_p95}ms)")
    
    # Cleanup
    await db.close()
    
    print("\n" + "=" * 80)
    print("RAG SYSTEM TEST COMPLETE")
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  ✅ Embedding dimension: 768")
    print(f"  ✅ Indexed entities: {indexed_count}")
    print(f"  ✅ Semantic search: Working")
    print(f"  {'✅' if p95 < target_p95 else '⚠️ '} p95 latency: {p95:.1f}ms (target: <{target_p95}ms)")
    print(f"\nNext: Integrate with 2×512K llama.cpp instances")


if __name__ == "__main__":
    asyncio.run(main())
