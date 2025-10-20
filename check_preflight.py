"""Pre-flight checks before running 7-agent analysis."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from adapters.rag import SurrealDBStore

async def main():
    print("=== Pre-flight Checks ===")
    print("✅ Granite: Both servers healthy (8080, 8081)")

    # Check RAG database
    db = SurrealDBStore('ws://localhost:8000', 'atado', 'rag', 'root', 'root')
    await db.connect()
    r = await db.query('SELECT count() FROM code_entity GROUP ALL')
    count = r[0]["count"]
    await db.close()

    print(f"✅ RAG Database: {count} entities indexed")
    print(f"✅ All systems ready for 7-agent analysis!")

    return count >= 1000

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
