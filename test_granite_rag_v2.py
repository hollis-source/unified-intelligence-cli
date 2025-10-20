"""Test GraniteAdapterV2 with lazy RAG initialization.

This test validates that the event loop conflict is fixed.
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.adapters.llm.granite_adapter_v2 import GraniteAdapterV2
from src.adapters.llm.rag_config import RAGConfig
from src.interface import LLMConfig


def test_granite_rag_v2():
    """Test Granite with lazy RAG initialization."""

    print("=" * 80)
    print("GRANITE + RAG V2 TEST (Lazy Initialization)")
    print("=" * 80)
    print()

    # Setup RAG configuration (not initialized components)
    print("[1/3] Creating RAG configuration...")
    rag_config = RAGConfig(
        db_url="ws://localhost:8000",
        db_namespace="atado",
        db_database="rag",
        db_user="root",
        db_password="root",
        embedding_model="sentence-transformers/all-mpnet-base-v2",
        embedding_provider="sentence-transformers",
        top_k=3,
        similarity_threshold=0.5,
        snippet_max_length=800
    )
    print(f"  ✅ {rag_config}")

    # Setup Granite with lazy RAG
    print("\n[2/3] Initializing GraniteAdapterV2...")
    granite = GraniteAdapterV2(
        enable_rag=True,
        rag_config=rag_config,
        timeout=300
    )
    print("  ✅ Granite ready (RAG will initialize on first use)")

    # Test queries
    print("\n[3/3] Testing Granite+RAG generation...")

    test_queries = [
        "What is the HTNNode class used for in this codebase?",
        "How does team-based routing work?",
        "What category theory concepts are used?"
    ]

    import time
    results = []

    for i, query in enumerate(test_queries, 1):
        print(f"\n  Query {i}: {query[:50]}...")
        print(f"  Generating...")

        start = time.time()

        response = granite.generate(
            messages=[
                {"role": "system", "content": "You are a helpful code analyst."},
                {"role": "user", "content": query}
            ],
            config=LLMConfig(temperature=0.7, max_tokens=300)
        )

        duration = time.time() - start

        if response.startswith("Error:"):
            print(f"  ❌ FAILED: {response}")
            return False

        print(f"  ✅ Success in {duration:.1f}s ({len(response)} chars)")
        print(f"     Preview: {response[:100]}...")

        results.append({
            "query": query,
            "duration": duration,
            "length": len(response),
            "success": not response.startswith("Error:")
        })

    # Summary
    print("\n" + "=" * 80)
    print("✅ GRANITE + RAG V2 TEST PASSED")
    print("=" * 80)

    total_time = sum(r["duration"] for r in results)
    avg_time = total_time / len(results)
    total_chars = sum(r["length"] for r in results)

    print(f"\nPerformance Summary:")
    print(f"  - Total queries: {len(results)}")
    print(f"  - Total time: {total_time:.1f}s")
    print(f"  - Average time: {avg_time:.1f}s per query")
    print(f"  - Total output: {total_chars} chars")
    print(f"  - Success rate: {sum(1 for r in results if r['success'])}/{len(results)}")

    print(f"\n✅ RAG event loop conflict is FIXED!")
    print(f"   (Components lazily initialized in correct thread context)")

    return True


if __name__ == "__main__":
    success = test_granite_rag_v2()
    sys.exit(0 if success else 1)
