"""Quick RAG setup test - check if codebase is indexed."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from adapters.rag import EmbeddingPipeline, SurrealDBStore, CodebaseRAG


async def main():
    print("=" * 80)
    print("RAG SETUP TEST")
    print("=" * 80)

    # Step 1: Initialize embedder
    print("\n[1/4] Loading embedding model...")
    try:
        embedder = EmbeddingPipeline(
            model="sentence-transformers/all-mpnet-base-v2",
            provider="sentence-transformers"
        )
        test_emb = await embedder.embed_text("test")
        print(f"  ✅ Embedder loaded: {test_emb.shape[0]} dimensions")
    except Exception as e:
        print(f"  ❌ Embedder failed: {e}")
        return

    # Step 2: Connect to SurrealDB
    print("\n[2/4] Connecting to SurrealDB...")
    try:
        db = SurrealDBStore(
            url="ws://localhost:8000",
            namespace="atado",
            database="rag",
            user="root",
            password="root"
        )
        await db.connect()
        print(f"  ✅ SurrealDB connected")
    except Exception as e:
        print(f"  ❌ SurrealDB connection failed: {e}")
        return

    # Step 3: Check if codebase is indexed
    print("\n[3/4] Checking if codebase is indexed...")
    try:
        # Try to query for code entities
        results = await db.search_similar_code(test_emb, top_k=1)
        if results:
            print(f"  ✅ Found {len(results)} code entities (codebase is indexed)")
            print(f"     Sample: {results[0].get('qualified_name', 'N/A')}")
        else:
            print(f"  ⚠️  No code entities found (codebase not indexed)")
    except Exception as e:
        print(f"  ⚠️  Query failed: {e}")
        print(f"     Codebase likely not indexed")

    # Step 4: Create CodebaseRAG instance
    print("\n[4/4] Creating CodebaseRAG instance...")
    try:
        rag = CodebaseRAG(db=db, embedder=embedder)
        print(f"  ✅ CodebaseRAG ready")
        print(f"\n{'=' * 80}")
        print(f"RAG SETUP: READY")
        print(f"{'=' * 80}")
        print(f"\nTo use with GraniteAdapter:")
        print(f"  granite = GraniteAdapter(")
        print(f"      enable_rag=True,")
        print(f"      rag_db=db,")
        print(f"      rag_embedder=embedder")
        print(f"  )")
        return db, embedder, rag
    except Exception as e:
        print(f"  ❌ CodebaseRAG failed: {e}")
        return None, None, None


if __name__ == "__main__":
    result = asyncio.run(main())
    if result and result[2]:
        print("\n✅ All RAG components initialized successfully")
    else:
        print("\n❌ RAG setup incomplete")
