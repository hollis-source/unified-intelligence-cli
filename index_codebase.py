"""Index codebase into SurrealDB for RAG.

Indexes all Python code entities from src/ directory.
"""

import asyncio
import ast
import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from adapters.rag import EmbeddingPipeline
from surrealdb.connections.async_ws import AsyncWsSurrealConnection


async def index_file(db, embedder, file_path: str, repo_root: str):
    """Index a single Python file."""
    rel_path = os.path.relpath(file_path, repo_root)
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        source = f.read()
    
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0
    
    indexed = 0
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            name = node.name
            doc = ast.get_docstring(node) or ""
            
            # Get source segment
            try:
                content = ast.get_source_segment(source, node) or ""
            except:
                content = f"class {name}" if isinstance(node, ast.ClassDef) else f"def {name}()"
            
            # Generate embedding
            text = f"{name}\n{doc}\n{content[:1000]}"  # Limit content length
            emb = await embedder.embed_text(text)

            # Content hash
            h = hashlib.sha256()
            h.update(content.encode('utf-8'))
            content_hash = h.hexdigest()

            # Calculate line numbers safely
            start_line = node.lineno
            end_line = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno is not None else node.lineno

            # Debug first entity
            if indexed == 0:
                print(f"\n      DEBUG: name={name}, start_line={start_line}, end_line={end_line}, type={type(end_line)}\n")

            # Store
            try:
                result = await db.query("""
                    CREATE code_entity SET
                        repo_path = $repo_path,
                        file_path = $file_path,
                        name = $name,
                        qualified_name = $qualified_name,
                        entity_type = $entity_type,
                        language = 'python',
                        content = $content,
                        content_hash = $content_hash,
                        docstring = $docstring,
                        start_line = $start_line,
                        end_line = $end_line,
                        tags = $tags,
                        embedding = $embedding,
                        embedding_model = $embedding_model
                """, {
                    "repo_path": repo_root,
                    "file_path": rel_path,
                    "name": name,
                    "qualified_name": f"{rel_path}:{name}",
                    "entity_type": "class" if isinstance(node, ast.ClassDef) else "function",
                    "content": content[:2000],  # Limit storage
                    "content_hash": content_hash,
                    "docstring": doc,
                    "start_line": start_line,
                    "end_line": end_line,
                    "tags": [],
                    "embedding": emb.tolist(),
                    "embedding_model": "sentence-transformers/all-mpnet-base-v2"
                })
                if indexed == 0:  # Print first result to debug
                    print(f"\n      First insert result: {result}\n")
                indexed += 1
            except Exception as e:
                print(f"    Error storing {name}: {e}")
                if indexed == 0:  # Stop on first error to see it
                    raise
    
    return indexed


async def main():
    print("=" * 80)
    print("CODEBASE INDEXING FOR RAG")
    print("=" * 80)
    
    # Setup
    print("\n[1/3] Initializing...")
    embedder = EmbeddingPipeline(
        model="sentence-transformers/all-mpnet-base-v2",
        provider="sentence-transformers"
    )
    
    db = AsyncWsSurrealConnection("ws://localhost:8000")
    await db.connect()
    await db.signin({"username": "root", "password": "root"})
    await db.use("atado", "rag")
    
    print("  ✅ RAG components ready")
    
    # Index files
    print("\n[2/3] Indexing src/ directory...")
    
    repo_root = os.path.abspath(".")
    src_dir = os.path.join(repo_root, "src")
    
    total_files = 0
    total_entities = 0
    
    for root, dirs, files in os.walk(src_dir):
        # Skip test directories
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.mypy_cache']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_root)
                
                print(f"  Indexing {rel_path}...", end='', flush=True)
                indexed = await index_file(db, embedder, file_path, repo_root)
                total_files += 1
                total_entities += indexed
                print(f" {indexed} entities")
    
    print(f"\n  ✅ Indexed {total_entities} entities from {total_files} files")
    
    # Verify
    print("\n[3/3] Verifying index...")
    result = await db.query("SELECT count() FROM code_entity GROUP ALL")
    count = result[0]['result'][0]['count'] if result and result[0].get('result') else 0
    
    print(f"  Total entities in database: {count}")
    
    # Test query
    test_query = "HTN task decomposition"
    print(f"\n  Test query: '{test_query}'")
    
    test_emb = await embedder.embed_text(test_query)
    result = await db.query(f"""
        SELECT file_path, name, qualified_name,
               vector::similarity::cosine(embedding, $e) AS similarity
        FROM code_entity
        WHERE embedding <|5|> $e
        ORDER BY similarity DESC
        LIMIT 5
    """, {"e": test_emb.tolist()})
    
    if result and result[0].get('result'):
        print(f"  Top 5 results:")
        for i, item in enumerate(result[0]['result'][:5], 1):
            print(f"    {i}. {item['name']} (sim={item['similarity']:.3f}) - {item['file_path']}")
    
    await db.close()
    
    print("\n" + "=" * 80)
    print("INDEXING COMPLETE")
    print("=" * 80)
    print(f"\n✅ Files indexed: {total_files}")
    print(f"✅ Entities indexed: {total_entities}")
    print(f"✅ Database total: {count}")


if __name__ == "__main__":
    asyncio.run(main())
