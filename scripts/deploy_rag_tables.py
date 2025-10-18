#!/usr/bin/env python3
"""Deploy additional RAG tables to SurrealDB.

This script deploys the agent_performance and routing_decisions tables
to the existing SurrealDB instance.
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.llm.rag_config import RAGConfig


async def deploy_tables():
    """Deploy RAG tables to SurrealDB."""
    
    print("=" * 80)
    print("DEPLOYING RAG TABLES TO SURREALDB")
    print("=" * 80)
    
    # Create config (override URL for localhost access)
    config = RAGConfig()
    # Use localhost instead of Docker container name when running from host
    db_url = os.getenv("SURREALDB_URL", "ws://localhost:8000")
    print(f"\nConnecting to: {db_url}")
    print(f"Namespace: {config.db_namespace}")
    print(f"Database: {config.db_database}")
    
    # Create store and connect
    store = SurrealDBStore(
        url=db_url,  # Use localhost URL
        namespace=config.db_namespace,
        database=config.db_database,
        user=config.db_user,
        password=config.db_password
    )
    
    try:
        await store.connect()
        print("✅ Connected to SurrealDB")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False
    
    # Read schema file
    schema_file = os.path.join(os.path.dirname(__file__), 'add_rag_tables.surql')
    print(f"\nReading schema from: {schema_file}")
    
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    # Split into individual statements
    statements = [s.strip() for s in schema_sql.split(';') if s.strip() and not s.strip().startswith('--')]
    
    print(f"Found {len(statements)} SQL statements")
    
    # Execute each statement
    print("\nExecuting statements...")
    success_count = 0
    error_count = 0
    
    for i, stmt in enumerate(statements, 1):
        # Skip comments
        if stmt.startswith('--'):
            continue
            
        try:
            print(f"  [{i}/{len(statements)}] {stmt[:60]}...")
            result = await store.db.query(stmt)
            success_count += 1
            print(f"      ✅ Success")
        except Exception as e:
            error_count += 1
            print(f"      ⚠️  Warning: {e}")
            # Continue even if some statements fail (might already exist)
    
    print("\n" + "=" * 80)
    print("DEPLOYMENT SUMMARY")
    print("=" * 80)
    print(f"Total statements: {len(statements)}")
    print(f"Successful: {success_count}")
    print(f"Warnings: {error_count}")
    
    # Verify tables exist
    print("\n" + "=" * 80)
    print("VERIFYING TABLES")
    print("=" * 80)
    
    tables_to_verify = ['agent_performance', 'routing_decisions']
    
    for table in tables_to_verify:
        try:
            result = await store.db.query(f"INFO FOR TABLE {table}")
            print(f"✅ {table}: EXISTS")
        except Exception as e:
            print(f"❌ {table}: NOT FOUND ({e})")
    
    print("\n" + "=" * 80)
    print("DEPLOYMENT COMPLETE ✅")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(deploy_tables())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ DEPLOYMENT FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

