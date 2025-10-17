#!/usr/bin/env python3
"""
Generate Phase 6a tests: Graph entity comprehensive tests.

Uses Qwen3-Next-80B-A3B-Instruct (direct instruction mode).

Phase 6a Focus:
- GraphNode dataclass (creation, hash, equality, repr)
- Graph initialization
- Node operations (add_node, get_node, has_node)
- Edge operations (add_edge, has_edge, duplicate edge errors)
- Accessors (get_successors, get_predecessors)
- Counting (count_nodes, count_edges, deprecated methods)
- Traversals (traverse_dfs, traverse_bfs, with visit functions)
- Cycle detection (acyclic, cyclic, self-loop, disconnected)
- Topological sort (valid DAG, cyclic error)
- Roots/leaves finding
- Subgraph extraction
- Deprecated method warnings

Expected: 40-45 tests covering all graph operations.
"""

import os
import sys
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.factories.provider_factory import ProviderFactory


def extract_code_from_markdown(content: str) -> str:
    """Extract Python code from markdown code blocks."""
    pattern = r'```python\s*\n(.*?)\n```'
    matches = re.findall(pattern, content, re.DOTALL)
    if matches:
        return matches[0].strip()
    return content.strip()


def main():
    print("=" * 80)
    print("Phase 6a: Graph Entity Test Generation")
    print("=" * 80)

    # Read Graph source code
    graph_path = project_root / "src/entity/graph/graph.py"
    with open(graph_path, 'r') as f:
        graph_source = f.read()

    print("\n📖 Source Code Analysis:")
    print(f"   Graph: {len(graph_source)} chars, {len(graph_source.splitlines())} lines")

    print("\n🔧 Components to test:")
    print("   - GraphNode dataclass (creation, hash, equality, repr)")
    print("   - Graph initialization")
    print("   - add_node() with metadata")
    print("   - get_node(), has_node()")
    print("   - add_edge() with validation")
    print("   - has_edge(), get_successors(), get_predecessors()")
    print("   - count_nodes(), count_edges()")
    print("   - Deprecated: node_count(), edge_count()")
    print("   - traverse_dfs() with visit function")
    print("   - traverse_bfs() with visit function")
    print("   - Deprecated: dfs(), bfs()")
    print("   - has_cycle() - acyclic, cyclic, self-loop")
    print("   - sort_topologically() - DAG, cyclic error")
    print("   - Deprecated: topological_sort()")
    print("   - find_roots(), find_leaves()")
    print("   - extract_subgraph() with validation")
    print("   - Deprecated: subgraph()")
    print("   - __repr__()")

    # Initialize Qwen3 provider
    print("\n🚀 Initializing Qwen3-Next-80B-A3B-Instruct...")
    factory = ProviderFactory()
    config = {
        "model": "Qwen/Qwen3-Next-80B-A3B-Instruct",
        "thinking_mode": False
    }

    try:
        provider = factory.create_provider("qwen-agent", config)
        print("   ✅ Provider initialized successfully")
    except Exception as e:
        print(f"   ❌ Provider initialization failed: {e}")
        return 1

    # Construct prompt
    prompt = f"""You are a Python testing expert. Generate comprehensive pytest tests for the Graph entity.

**Source Code to Test:**

```python
{graph_source}
```

**Requirements:**

1. **Comprehensive Coverage** (40-45 tests):

   **GraphNode (5 tests)**:
   - Creation with data and metadata
   - __hash__() returns hash of node_id
   - __eq__() compares node_ids
   - __repr__() format
   - Use in set/dict (hash uniqueness)

   **Graph Initialization (1 test)**:
   - Empty graph state (nodes, edges, reverse_edges)

   **Node Operations (6 tests)**:
   - add_node(): with data, metadata, returns GraphNode
   - add_node(): duplicate node raises ValueError
   - get_node(): existing returns node, missing returns None
   - has_node(): existing returns True, missing returns False

   **Edge Operations (6 tests)**:
   - add_edge(): valid edge, updates edges and reverse_edges
   - add_edge(): missing source raises ValueError
   - add_edge(): missing target raises ValueError
   - add_edge(): duplicate edge raises ValueError
   - has_edge(): existing returns True, missing returns False
   - get_successors(), get_predecessors(): return copies of lists

   **Counting (4 tests)**:
   - count_nodes(), count_edges(): correct counts
   - node_count(): deprecated warning, returns count
   - edge_count(): deprecated warning, returns count

   **Traversals (8 tests)**:
   - traverse_dfs(): correct order, linear graph
   - traverse_dfs(): with visit function (track calls)
   - traverse_dfs(): missing start node raises ValueError
   - dfs(): deprecated warning, returns traversal
   - traverse_bfs(): correct order, tree structure
   - traverse_bfs(): with visit function
   - traverse_bfs(): missing start node raises ValueError
   - bfs(): deprecated warning

   **Cycle Detection (5 tests)**:
   - has_cycle(): acyclic graph returns False
   - has_cycle(): cyclic graph returns True
   - has_cycle(): self-loop returns True
   - has_cycle(): disconnected components (mixed)
   - has_cycle(): empty graph returns False

   **Topological Sort (4 tests)**:
   - sort_topologically(): valid DAG, correct ordering
   - sort_topologically(): cyclic graph raises ValueError
   - sort_topologically(): disconnected components
   - topological_sort(): deprecated warning

   **Roots/Leaves (4 tests)**:
   - find_roots(): tree with single root
   - find_roots(): multiple roots, no roots
   - find_leaves(): tree with multiple leaves
   - find_leaves(): no leaves, all leaves

   **Subgraph (3 tests)**:
   - extract_subgraph(): valid nodes, edges preserved
   - extract_subgraph(): missing node raises ValueError
   - subgraph(): deprecated warning

   **Other (1 test)**:
   - __repr__(): format with counts

2. **Key Test Patterns**:
   - Use simple graphs (3-5 nodes) for clarity
   - Test error cases with pytest.raises
   - Test deprecated methods with pytest.warns
   - Verify bidirectional edge tracking (edges + reverse_edges)
   - Test visit functions with list.append tracking
   - Verify topological sort ordering (all edges go forward)

3. **Code Style**:
   - Import from src.entity.graph.graph
   - Use descriptive graph structures (e.g., A→B→C for linear)
   - Add docstrings explaining graph structure
   - Use fixtures for common graphs (linear, tree, cyclic)

4. **Output Format**:
   - Return ONLY valid Python code
   - Enclose code in markdown ```python``` blocks
   - NO explanatory text outside code blocks
   - File should start with: # tests/unit/entity/graph/test_graph_comprehensive.py

**Important Notes**:
- GraphNode uses node_id for hash/equality (can have same data, different IDs)
- add_edge() requires both nodes to exist first
- Cycle detection uses 3-color DFS (WHITE=0, GRAY=1, BLACK=2)
- Topological sort is DFS-based (reverse postorder)
- Traversals handle disconnected components
- get_successors/get_predecessors return copies (not references)

NO LONG THINKING. Focus on generating high-quality, executable tests. Return code immediately.

Generate the complete test file now:"""

    # Generate tests
    print("\n⏱️  Generating tests with Qwen3 Instruct (no thinking mode)...")
    print("   Expected time: ~40-60 seconds (most complex entity)...")

    try:
        import time
        start_time = time.time()

        response = provider.generate(prompt)

        elapsed = time.time() - start_time
        print(f"   ✅ Generation completed in {elapsed:.1f} seconds")

        # Extract code
        content = response.content if hasattr(response, 'content') else str(response)
        code = extract_code_from_markdown(content)

        print(f"\n📊 Generation Statistics:")
        print(f"   Raw output: {len(content)} characters")
        print(f"   Extracted code: {len(code)} characters")
        print(f"   Lines: {len(code.splitlines())}")

    except Exception as e:
        print(f"   ❌ Generation failed: {e}")
        return 1

    # Validate code structure
    print("\n🔍 Validating code structure...")
    if "import pytest" not in code:
        print("   ⚠️  WARNING: No pytest import found")
    if "def test_" not in code:
        print("   ⚠️  WARNING: No test functions found")
    if "graph" not in code.lower():
        print("   ⚠️  WARNING: Graph import may be missing")

    test_count = code.count("def test_")
    fixture_count = code.count("@pytest.fixture")
    param_count = code.count("@pytest.mark.parametrize")

    print(f"   Test functions: {test_count}")
    print(f"   Fixtures: {fixture_count}")
    print(f"   Parametrized tests: {param_count}")

    if test_count < 35:
        print(f"   ⚠️  WARNING: Only {test_count} tests generated (expected 40-45)")

    # Create output directory if needed
    output_dir = project_root / "tests/unit/entity/graph"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write to file
    output_path = output_dir / "test_graph_comprehensive.py"

    print(f"\n💾 Writing tests to: {output_path}")
    with open(output_path, 'w') as f:
        f.write(code)

    print("   ✅ File written successfully")

    # Instructions
    print("\n" + "=" * 80)
    print("✅ Phase 6a Test Generation Complete!")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Run tests: pytest tests/unit/entity/graph/test_graph_comprehensive.py -v")
    print("2. Fix any errors found")
    print("3. Run coverage: pytest --cov=src/entity/graph/graph tests/unit/entity/graph/test_graph_comprehensive.py")
    print("\nExpected Result:")
    print("- 40-45 tests passing")
    print("- 90%+ coverage of Graph entity")
    print("- All graph algorithms validated")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
