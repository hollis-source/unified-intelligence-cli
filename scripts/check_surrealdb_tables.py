#!/usr/bin/env python3
"""Check what tables exist in SurrealDB."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.llm.rag_config import RAGConfig


async def check_tables():
    """Check what tables exist in SurrealDB."""
    
    print("=" * 80)
    print("SURREALDB TABLES CHECK")
    print("=" * 80)
    
    config = RAGConfig()
    db_url = os.getenv("SURREALDB_URL", "ws://localhost:8000")
    
    print(f"Connecting to: {db_url}")
    print(f"Namespace: {config.db_namespace}")
    print(f"Database: {config.db_database}")
    print()
    
    store = SurrealDBStore(
        url=db_url,
        namespace=config.db_namespace,
        database=config.db_database,
        user=config.db_user,
        password=config.db_password
    )
    
    try:
        await store.connect()
        print("✅ Connected to SurrealDB")
        print()
        
        # List all tables
        print("Listing tables...")
        result = await store.query("INFO FOR DB;")
        print(f"Result: {result}")
        print()
        
        # Try to query execution_log
        print("Querying execution_log table...")
        result = await store.query("SELECT * FROM execution_log LIMIT 5;")
        print(f"Result: {result}")
        
        if result and result[0].get("result"):
            records = result[0]["result"]
            print(f"Found {len(records)} records in execution_log")
            for i, record in enumerate(records, 1):
                print(f"  {i}. {record.get('task_description', 'N/A')[:50]}")
        else:
            print("No records found or table doesn't exist")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_tables())

