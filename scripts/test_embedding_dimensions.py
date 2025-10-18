#!/usr/bin/env python3
"""Test script to verify embedding dimensions are correct.

This script tests that:
1. EmbeddingPipeline generates 1536-dim embeddings with OpenAI
2. RAGConfig is properly configured for OpenAI
3. Dimensions align with schema expectations
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.adapters.rag.embedding_pipeline import EmbeddingPipeline
from src.adapters.llm.rag_config import RAGConfig


async def test_embedding_dimensions():
    """Test embedding dimensions."""
    
    print("=" * 80)
    print("EMBEDDING DIMENSION TEST")
    print("=" * 80)
    
    # Test 1: RAGConfig
    print("\n1. Testing RAGConfig...")
    config = RAGConfig()
    print(f"   Provider: {config.embedding_provider}")
    print(f"   Model: {config.embedding_model}")
    print(f"   Expected: openai / text-embedding-3-small")
    
    assert config.embedding_provider == "openai", f"Expected openai, got {config.embedding_provider}"
    assert config.embedding_model == "text-embedding-3-small", f"Expected text-embedding-3-small, got {config.embedding_model}"
    print("   ✅ RAGConfig correct")
    
    # Test 2: EmbeddingPipeline with OpenAI
    print("\n2. Testing EmbeddingPipeline with OpenAI...")
    
    # Check if OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        print("   ⚠️  OPENAI_API_KEY not set - skipping OpenAI test")
        print("   To test OpenAI embeddings, set OPENAI_API_KEY environment variable")
        return
    
    pipeline = EmbeddingPipeline(provider="openai", model="text-embedding-3-small")
    
    # Generate test embedding
    test_text = "This is a test sentence for embedding generation."
    print(f"   Generating embedding for: '{test_text}'")
    
    embedding = await pipeline.embed_text(test_text)
    
    print(f"   Embedding shape: {embedding.shape}")
    print(f"   Embedding dimension: {len(embedding)}")
    print(f"   Expected dimension: 1536")
    
    assert len(embedding) == 1536, f"Expected 1536 dimensions, got {len(embedding)}"
    print("   ✅ Embedding dimension correct (1536)")
    
    # Test 3: Batch embeddings
    print("\n3. Testing batch embeddings...")
    texts = [
        "First test sentence",
        "Second test sentence",
        "Third test sentence"
    ]
    
    embeddings = await pipeline.embed_batch(texts)
    print(f"   Batch size: {len(embeddings)}")
    print(f"   Each embedding dimension: {len(embeddings[0])}")
    
    assert len(embeddings) == 3, f"Expected 3 embeddings, got {len(embeddings)}"
    assert all(len(emb) == 1536 for emb in embeddings), "Not all embeddings are 1536-dim"
    print("   ✅ Batch embeddings correct")
    
    print("\n" + "=" * 80)
    print("ALL TESTS PASSED ✅")
    print("=" * 80)
    print("\nSummary:")
    print("  • RAGConfig uses OpenAI provider")
    print("  • Embedding model: text-embedding-3-small")
    print("  • Embedding dimension: 1536")
    print("  • Aligns with schema expectations")
    print("\nDimension mismatch FIXED! ✅")


if __name__ == "__main__":
    try:
        asyncio.run(test_embedding_dimensions())
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

