"""Test SurrealDB insert and persistence."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from adapters.rag import SurrealDBStore


async def main():
    print("Testing SurrealDB insert and persistence...")

    db = SurrealDBStore('ws://localhost:8000', 'atado', 'rag', 'root', 'root')
    await db.connect()
    print("✅ Connected")

    # Check initial count
    result = await db.query('SELECT count() FROM code_entity GROUP ALL')
    print(f"Initial count: {result}")

    # Try manual insert
    print("\nInserting test entity...")
    result = await db.query('''
        CREATE code_entity SET
            file_path = 'test.py',
            name = 'test_func',
            qualified_name = 'test.py:test_func',
            entity_type = 'function',
            language = 'python',
            content = 'def test(): pass',
            content_hash = 'abc123',
            docstring = 'Test function',
            start_line = 1,
            end_line = 1,
            tags = [],
            embedding = [0.1, 0.2, 0.3],
            embedding_model = 'test'
    ''')
    print(f"Insert result: {result}")

    # Check count again
    result = await db.query('SELECT count() FROM code_entity GROUP ALL')
    print(f"After insert count: {result}")

    # Try to select
    result = await db.query('SELECT * FROM code_entity WHERE name = "test_func"')
    print(f"Select result: {result}")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
