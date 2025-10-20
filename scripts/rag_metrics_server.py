#!/usr/bin/env python3
"""RAG Metrics Server - Standalone server for RAG metrics API.

This server provides HTTP endpoints for monitoring RAG system metrics.
Can be deployed to syd2.jacobhollis.com or run locally.

Usage:
    python scripts/rag_metrics_server.py
    
Environment Variables:
    SURREALDB_URL - SurrealDB connection URL (default: ws://localhost:8000)
    HOST - Server host (default: 0.0.0.0)
    PORT - Server port (default: 8080)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiohttp import web
from src.adapters.web.api_server import create_app
from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.llm.rag_config import RAGConfig


async def dummy_task_runner(tasks):
    """Dummy task runner for standalone metrics server.
    
    In production, replace this with your actual task runner.
    """
    return {
        "tasks_processed": len(tasks),
        "message": "This is a metrics-only server. Task execution not implemented."
    }


async def init_database():
    """Initialize database connection."""
    config = RAGConfig()
    db_url = os.getenv("SURREALDB_URL", "ws://localhost:8000")
    
    print(f"Connecting to SurrealDB at {db_url}...")
    
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
        return db_store
    except Exception as e:
        print(f"❌ Failed to connect to SurrealDB: {e}")
        print("   Make sure SurrealDB is running and accessible")
        raise


async def main():
    """Main entry point."""
    print("=" * 80)
    print("RAG METRICS SERVER")
    print("=" * 80)
    print()
    
    # Initialize database
    try:
        db_store = await init_database()
    except Exception:
        print("\n❌ Server startup failed - database connection error")
        sys.exit(1)
    
    print()
    
    # Create app with RAG metrics
    app = create_app(
        task_runner=dummy_task_runner,
        db_store=db_store,
        enable_rag_metrics=True
    )
    
    # Get configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    
    print("Server Configuration:")
    print(f"  • Host: {host}")
    print(f"  • Port: {port}")
    print()
    
    print("Available Endpoints:")
    print("  • GET  /health                      - Health check")
    print("  • POST /api/v1/tasks                - Submit tasks (dummy)")
    print("  • GET  /api/rag/metrics             - Metrics overview")
    print("  • GET  /api/rag/patterns            - Pattern metrics")
    print("  • GET  /api/rag/routing/accuracy    - Routing accuracy")
    print("  • GET  /api/rag/performance         - Performance metrics")
    print("  • GET  /api/rag/drift               - Drift detection")
    print("  • GET  /api/rag/ab-test             - A/B test results")
    print("  • GET  /api/rag/weights             - Weight optimization")
    print()
    
    print("=" * 80)
    print(f"🚀 Starting server on http://{host}:{port}")
    print("=" * 80)
    print()
    print("Press Ctrl+C to stop")
    print()
    
    # Run server
    try:
        web.run_app(app, host=host, port=port, print=lambda x: None)
    except KeyboardInterrupt:
        print("\n\n⏹️  Server stopped by user")
    except Exception as e:
        print(f"\n\n❌ Server error: {e}")
        sys.exit(1)
    finally:
        await db_store.close()
        print("✅ Database connection closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

