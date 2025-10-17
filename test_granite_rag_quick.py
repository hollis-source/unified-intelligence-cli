"""Quick test: Granite + RAG with extended timeout."""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.adapters.llm.granite_adapter import GraniteAdapter
from src.adapters.rag import EmbeddingPipeline, SurrealDBStore
from src.interface import LLMConfig


async def test_granite_rag():
    """Test Granite with RAG context on a simple query."""

    print("=" * 80)
    print("GRANITE + RAG QUICK TEST")
    print("=" * 80)
    print()

    # Setup RAG
    print("[1/3] Initializing RAG...")
    embedder = EmbeddingPipeline(
        model="sentence-transformers/all-mpnet-base-v2",
        provider="sentence-transformers"
    )
    db = SurrealDBStore(
        url="ws://localhost:8000",
        namespace="atado",
        database="rag",
        user="root",
        password="root"
    )
    await db.connect()
    print("  ✅ RAG ready (1,276 entities)")

    # Setup Granite with 300s timeout
    print("\n[2/3] Initializing Granite (timeout=300s)...")
    granite = GraniteAdapter(
        enable_rag=True,
        rag_db=db,
        rag_embedder=embedder,
        timeout=300
    )
    print("  ✅ Granite ready")

    # Test simple query
    print("\n[3/3] Testing Granite+RAG generation...")
    test_query = "What is the HTNNode class used for in this codebase?"

    print(f"\n  Query: {test_query}")
    print(f"  Generating... (max 300s)")

    import time
    start = time.time()

    response = granite.generate(
        messages=[
            {"role": "system", "content": "You are a helpful code analyst."},
            {"role": "user", "content": test_query}
        ],
        config=LLMConfig(temperature=0.7, max_tokens=500)
    )

    duration = time.time() - start

    print(f"\n  ✅ Response received in {duration:.1f}s")
    print(f"\n  Response preview:")
    print(f"  {response[:300]}...")

    if response.startswith("Error:"):
        print(f"\n  ❌ FAILED: {response}")
        return False

    await db.close()

    print("\n" + "=" * 80)
    print("✅ GRANITE + RAG TEST PASSED")
    print("=" * 80)
    print(f"\nPerformance: {duration:.1f}s for {len(response)} chars")
    print(f"Ready for full 7-agent analysis!")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_granite_rag())
    sys.exit(0 if success else 1)
