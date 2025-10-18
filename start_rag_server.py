#!/usr/bin/env python3
"""Start RAG Metrics Server on 157.90.66.183"""

import os
import sys

# Ensure we're using the right path
sys.path.insert(0, '/home/ui-cli_jake/unified-intelligence-cli')

from aiohttp import web
from src.adapters.web.api_server import create_app
from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.llm.rag_config import RAGConfig


async def dummy_task_runner(tasks):
    """Dummy task runner for metrics-only server."""
    return {'tasks_processed': len(tasks)}


def main():
    """Main entry point."""
    import asyncio
    
    async def init_and_run():
        config = RAGConfig()
        db_store = SurrealDBStore(
            url='ws://localhost:8000',
            namespace=config.db_namespace,
            database=config.db_database,
            user=config.db_user,
            password=config.db_password
        )
        
        try:
            await db_store.connect()
            print('✅ Connected to SurrealDB')
        except Exception as e:
            print(f'❌ Failed to connect: {e}')
            sys.exit(1)
        
        app = create_app(dummy_task_runner, db_store=db_store, enable_rag_metrics=True)
        
        print('=' * 80)
        print('RAG METRICS SERVER')
        print('=' * 80)
        print(f'Server: http://0.0.0.0:8888')
        print(f'External: http://157.90.66.183:8888')
        print()
        print('Endpoints:')
        print('  • GET  /health')
        print('  • GET  /api/rag/metrics')
        print('  • GET  /api/rag/patterns')
        print('  • GET  /api/rag/routing/accuracy')
        print('  • GET  /api/rag/performance')
        print('  • GET  /api/rag/drift')
        print('  • GET  /api/rag/ab-test')
        print('  • GET  /api/rag/weights')
        print('=' * 80)
        print()
        
        web.run_app(app, host='0.0.0.0', port=8888)
    
    asyncio.run(init_and_run())


if __name__ == '__main__':
    main()

