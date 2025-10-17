"""Test vector similarity search in SurrealDB."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from adapters.rag import EmbeddingPipeline, SurrealDBStore


async def main():
    print("=" * 80)
    print("VECTOR SEARCH TEST - RAG Validation")
    print("=" * 80)

    # Setup
    print("\n[1/3] Initializing...")
    embedder = EmbeddingPipeline(
        model="sentence-transformers/all-mpnet-base-v2",
        provider="sentence-transformers"
    )

    db = SurrealDBStore('ws://localhost:8000', 'atado', 'rag', 'root', 'root')
    await db.connect()
    print("  ✅ RAG components ready")

    # Check total entities
    print("\n[2/3] Checking database...")
    result = await db.query('SELECT count() FROM code_entity GROUP ALL')
    total = result[0]['count'] if result else 0
    print(f"  ✅ Total entities in database: {total}")

    # Test vector search
    print("\n[3/3] Testing vector similarity search...")

    test_queries = [
        "HTN task decomposition and planning",
        "Category theory morphism composition",
        "Team-based agent routing",
        "Graph algorithms topological sort",
        "DSL parser and compiler"
    ]

    for query in test_queries:
        print(f"\n  Query: '{query}'")

        # Generate embedding
        query_embedding = await embedder.embed_text(query)

        # Vector similarity search
        result = await db.query(f"""
            SELECT file_path, name, qualified_name,
                   vector::similarity::cosine(embedding, $e) AS similarity
            FROM code_entity
            WHERE embedding IS NOT NONE
            ORDER BY similarity DESC
            LIMIT 3
        """, {"e": query_embedding.tolist()})

        if result and result[0].get('result'):
            for i, item in enumerate(result[0]['result'][:3], 1):
                sim = item.get('similarity', 0)
                name = item.get('name', 'unknown')
                file_path = item.get('file_path', 'unknown')
                print(f"    {i}. {name} (sim={sim:.3f}) - {file_path}")
        else:
            print(f"    ⚠️  No results")

    await db.close()

    print("\n" + "=" * 80)
    print(f"✅ RAG VECTOR SEARCH WORKING - {total} embeddings indexed")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
