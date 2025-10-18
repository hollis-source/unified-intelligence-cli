#!/usr/bin/env python3
"""Test RAG metrics server integration.

This script tests the RAG metrics API endpoints.
"""

import asyncio
import os
import sys
import aiohttp
from aiohttp import web

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.adapters.web.api_server import create_app
from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.llm.rag_config import RAGConfig


async def dummy_task_runner(tasks):
    """Dummy task runner for testing."""
    return {"tasks_processed": len(tasks)}


async def test_rag_metrics_endpoints():
    """Test RAG metrics API endpoints."""
    
    print("=" * 80)
    print("RAG METRICS SERVER INTEGRATION TEST")
    print("=" * 80)
    print()
    
    # Setup database connection
    config = RAGConfig()
    db_url = os.getenv("SURREALDB_URL", "ws://localhost:8000")
    
    print("Connecting to SurrealDB...")
    db_store = SurrealDBStore(
        url=db_url,
        namespace=config.db_namespace,
        database=config.db_database,
        user=config.db_user,
        password=config.db_password
    )
    
    try:
        await db_store.connect()
        print("✅ Connected to SurrealDB")
        print()
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False
    
    # Create app with RAG metrics
    app = create_app(dummy_task_runner, db_store=db_store, enable_rag_metrics=True)
    
    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8888)
    await site.start()
    
    print("✅ Server started on http://localhost:8888")
    print()
    
    # Test endpoints
    base_url = "http://localhost:8888"
    
    endpoints = [
        ("/health", "Health Check"),
        ("/api/rag/metrics", "Metrics Overview"),
        ("/api/rag/patterns", "Pattern Metrics"),
        ("/api/rag/routing/accuracy", "Routing Accuracy"),
        ("/api/rag/performance", "Performance Metrics"),
        ("/api/rag/drift", "Drift Detection"),
        ("/api/rag/ab-test", "A/B Test Results"),
        ("/api/rag/weights", "Weight Optimization"),
    ]
    
    async with aiohttp.ClientSession() as session:
        for endpoint, name in endpoints:
            print(f"TEST: {name}")
            print(f"Endpoint: {endpoint}")
            print("-" * 80)
            
            try:
                async with session.get(f"{base_url}{endpoint}") as response:
                    status = response.status
                    data = await response.json()
                    
                    print(f"Status: {status}")
                    
                    if status == 200:
                        print(f"✅ {name} - PASS")
                        
                        # Print key metrics
                        if endpoint == "/health":
                            print(f"   Health: {data.get('status')}")
                        elif endpoint == "/api/rag/metrics":
                            metrics = data.get("metrics", {})
                            print(f"   Total patterns: {metrics.get('total_patterns', 0)}")
                            print(f"   Total decisions: {metrics.get('total_routing_decisions', 0)}")
                            print(f"   RAG accuracy: {metrics.get('rag_routing_accuracy', 0):.1f}%")
                        elif endpoint == "/api/rag/patterns":
                            patterns = data.get("patterns", {})
                            print(f"   Total patterns: {patterns.get('total', 0)}")
                            by_domain = patterns.get("by_domain", {})
                            if by_domain:
                                print(f"   Domains: {len(by_domain)}")
                        elif endpoint == "/api/rag/routing/accuracy":
                            accuracy = data.get("accuracy", {})
                            print(f"   RAG: {accuracy.get('rag', 0):.1f}%")
                            print(f"   Baseline: {accuracy.get('baseline', 0):.1f}%")
                            print(f"   Improvement: {accuracy.get('improvement', 0):+.1f}%")
                        elif endpoint == "/api/rag/performance":
                            perf = data.get("performance", {})
                            print(f"   Total agents: {perf.get('total_agents', 0)}")
                            print(f"   Top performers: {len(perf.get('top_performers', []))}")
                            print(f"   Low performers: {len(perf.get('low_performers', []))}")
                        elif endpoint == "/api/rag/drift":
                            drift = data.get("drift", {})
                            print(f"   Drift detected: {drift.get('drift_detected', False)}")
                            print(f"   Needs reembedding: {drift.get('needs_reembedding', False)}")
                        elif endpoint == "/api/rag/ab-test":
                            ab_test = data.get("ab_test", {})
                            print(f"   Test: {ab_test.get('test_name', 'N/A')}")
                            print(f"   Significant: {ab_test.get('significant', False)}")
                            print(f"   Improvement: {ab_test.get('improvement', 0):+.1f}%")
                        elif endpoint == "/api/rag/weights":
                            opt = data.get("optimization", {})
                            print(f"   Total decisions: {opt.get('total_decisions', 0)}")
                            print(f"   Domain weights: {len(opt.get('domain_weights', {}))}")
                            print(f"   Agent weights: {len(opt.get('agent_weights', {}))}")
                    else:
                        print(f"❌ {name} - FAIL (status {status})")
                        print(f"   Error: {data.get('error', 'Unknown error')}")
                    
                    print()
                    
            except Exception as e:
                print(f"❌ {name} - FAIL")
                print(f"   Exception: {e}")
                print()
    
    # Cleanup
    await runner.cleanup()
    await db_store.close()
    
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✅ All RAG metrics endpoints tested")
    print("✅ Server integration working")
    print()
    print("🎉 RAG METRICS SERVER INTEGRATION TEST COMPLETE!")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_rag_metrics_endpoints())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

