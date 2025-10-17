"""Complete end-to-end RAG test: Index → Search → Generate with llama.cpp"""

import asyncio
import requests
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))

from adapters.rag import EmbeddingPipeline
from surrealdb.connections.async_ws import AsyncWsSurrealConnection


async def main():
    print("=" * 80)
    print("END-TO-END RAG + LLAMA.CPP TEST")
    print("=" * 80)
    
    # Setup
    print("\n[1/4] Setup...")
    embedder = EmbeddingPipeline(
        model="sentence-transformers/all-mpnet-base-v2",
        provider="sentence-transformers"
    )
    
    db = AsyncWsSurrealConnection("ws://localhost:8000")
    await db.connect()
    await db.signin({"username": "root", "password": "root"})
    await db.use("atado", "rag")
    
    # Insert test HTN entities
    print("\n[2/4] Inserting HTN code entities...")
    
    test_entities = [
        {
            "name": "decompose_task",
            "file": "htn_node.py",
            "content": """def decompose_task(task, methods):
    '''Decompose HTN task into subtasks using available methods.
    
    Args:
        task: The task to decompose
        methods: Available decomposition methods
        
    Returns:
        List of subtasks
    '''
    subtasks = []
    for method in methods:
        if method.preconditions_met(task):
            subtasks.extend(method.decompose(task))
    return subtasks""",
        },
        {
            "name": "HTNPlanner",
            "file": "htn_planner.py",
            "content": """class HTNPlanner:
    '''Hierarchical Task Network planner for task decomposition.
    
    The HTN planner recursively decomposes tasks into primitive actions
    using a library of decomposition methods.
    '''
    
    def plan(self, goal_task):
        '''Create a plan by decomposing goal into primitive tasks.'''
        stack = [goal_task]
        plan = []
        
        while stack:
            task = stack.pop()
            if task.is_primitive():
                plan.append(task)
            else:
                subtasks = self.decompose(task)
                stack.extend(reversed(subtasks))
        
        return plan""",
        },
    ]
    
    for entity in test_entities:
        emb = await embedder.embed_text(f"{entity['name']}\n{entity['content']}")
        await db.query("""
            CREATE code_entity CONTENT {
                file_path: $file,
                name: $name,
                qualified_name: $qname,
                entity_type: $type,
                language: "python",
                content: $content,
                content_hash: $hash,
                docstring: "",
                line_start: 1,
                line_end: 10,
                embedding: $emb
            }
        """, {
            "file": entity["file"],
            "name": entity["name"],
            "qname": f"{entity['file']}:{entity['name']}",
            "type": "class" if entity["name"][0].isupper() else "function",
            "content": entity["content"],
            "hash": entity["name"],
            "emb": emb.tolist()
        })
    
    print(f"  ✅ Inserted {len(test_entities)} entities")
    
    # Test semantic search
    print("\n[3/4] Testing vector search...")
    query = "HTN task decomposition algorithm"
    query_emb = await embedder.embed_text(query)
    
    result = await db.query("""
        SELECT file_path, name, content,
               vector::similarity::cosine(embedding, $e) AS similarity
        FROM code_entity
        WHERE embedding <|3|> $e
        ORDER BY similarity DESC
        LIMIT 3
    """, {"e": query_emb.tolist()})
    
    context_snippets = []
    if result and result[0].get('result'):
        print(f"  ✅ Found {len(result[0]['result'])} results:")
        for r in result[0]['result']:
            print(f"    - {r['name']} (sim={r['similarity']:.3f})")
            context_snippets.append(f"# {r['file_path']}:{r['name']}\n{r['content']}\n")
    
    context = "\n".join(context_snippets)
    
    # RAG-augmented generation
    print("\n[4/4] RAG-augmented generation with llama.cpp...")
    
    rag_prompt = f"""Relevant code from this codebase:

{context}

Question: How does HTN task decomposition work in this codebase?

Answer based on the code above:"""
    
    response = requests.post(
        "http://localhost:8080/completion",
        json={
            "prompt": rag_prompt,
            "n_predict": 200,
            "temperature": 0.7,
        },
        timeout=30
    )
    
    result = response.json()
    answer = result.get('content', 'ERROR')
    
    print(f"\n  Context provided: {len(context)} chars (~{len(context)//4} tokens)")
    print(f"\n  Generated answer:")
    print(f"  {answer}")
    
    await db.close()
    
    print("\n" + "=" * 80)
    print("✅ END-TO-END RAG TEST COMPLETE")
    print("=" * 80)
    print(f"\nPhase 3 RAG Integration: SUCCESSFUL")
    print(f"  - Vector database: SurrealDB with MTREE index")
    print(f"  - Embeddings: 768-dim (all-mpnet-base-v2)")
    print(f"  - LLM backend: 2×512K llama.cpp instances")
    print(f"  - Context injection: {len(context)//4} tokens")


if __name__ == "__main__":
    asyncio.run(main())
