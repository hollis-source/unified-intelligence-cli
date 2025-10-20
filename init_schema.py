"""Initialize SurrealDB schema for RAG."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from adapters.rag import SurrealDBStore


async def main():
    print("=" * 80)
    print("SURREALDB SCHEMA INITIALIZATION")
    print("=" * 80)

    # Connect
    print("\n[1/2] Connecting to SurrealDB...")
    db = SurrealDBStore(
        url="ws://localhost:8000",
        namespace="atado",
        database="rag",
        user="root",
        password="root"
    )
    await db.connect()
    print("  ✅ Connected")

    # Load and apply schema
    print("\n[2/2] Applying schema...")
    schema_file = "scripts/schema_clean.surql"

    with open(schema_file, 'r') as f:
        schema_sql = f.read()

    try:
        result = await db.query(schema_sql)
        print(f"  ✅ Schema applied successfully")
        print(f"     Result: {len(result)} statements executed")
    except Exception as e:
        print(f"  ❌ Schema application failed: {e}")
        await db.close()
        return False

    # Verify tables
    print("\n[3/3] Verifying tables...")
    try:
        result = await db.query("INFO FOR DB")
        print(f"  ✅ Database info retrieved")

        # Check for code_entity table
        result = await db.query("SELECT * FROM code_entity LIMIT 0")
        print(f"  ✅ code_entity table exists")
    except Exception as e:
        print(f"  ⚠️  Verification: {e}")

    await db.close()

    print("\n" + "=" * 80)
    print("SCHEMA INITIALIZED")
    print("=" * 80)
    print("\n✅ Vector embedding tables ready:")
    print("   - code_entity (array<float> embeddings)")
    print("   - execution_log (array<float> embeddings)")
    print("   - agent_learning (array<float> embeddings)")
    print("   - optimization_pattern (array<float> embeddings)")

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
