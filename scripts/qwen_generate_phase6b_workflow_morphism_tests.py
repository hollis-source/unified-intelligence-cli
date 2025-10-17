#!/usr/bin/env python3
"""
Generate Phase 6b tests: Workflow_morphism entity comprehensive tests.

Uses Qwen3-Next-80B-A3B-Instruct (direct instruction mode).

Phase 6b Focus:
- flatten_htn() transformation
- remove_htn_identity() transformation
- simplify_htn() transformation
- graph_remove_isolated_nodes() transformation
- graph_deduplicate() transformation
- optimize_workflow() composite morphism
- Deprecated methods (htn_flatten, htn_remove_identity, htn_simplify, workflow_optimize)
- create_transformation_pipeline() helper function

Expected: 30-35 tests covering all workflow transformations.
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
    print("Phase 6b: Workflow_morphism Entity Test Generation")
    print("=" * 80)

    # Read Workflow_morphism source code
    workflow_path = project_root / "src/entity/category_theory/workflow_morphism.py"
    with open(workflow_path, 'r') as f:
        workflow_source = f.read()

    print("\n📖 Source Code Analysis:")
    print(f"   Workflow_morphism: {len(workflow_source)} chars, {len(workflow_source.splitlines())} lines")

    print("\n🔧 Components to test:")
    print("   - flatten_htn(): Flatten nested compositions")
    print("   - remove_htn_identity(): Remove identity nodes")
    print("   - simplify_htn(): Unwrap single-subtask nodes")
    print("   - graph_remove_isolated_nodes(): Remove isolated nodes")
    print("   - graph_deduplicate(): Remove duplicate edges")
    print("   - optimize_workflow(): Composite transformation")
    print("   - Deprecated: htn_flatten(), htn_remove_identity(), htn_simplify(), workflow_optimize()")
    print("   - create_transformation_pipeline(): Pipeline from names")

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
    prompt = f"""You are a Python testing expert. Generate comprehensive pytest tests for the Workflow_morphism entity.

**Source Code to Test:**

```python
{workflow_source}
```

**Requirements:**

1. **Comprehensive Coverage** (30-35 tests):

   **flatten_htn() (4-5 tests)**:
   - Flatten nested composition ((c ∘ b) ∘ a → c ∘ b ∘ a)
   - Primitive node returns unchanged
   - Non-composition compound returns unchanged
   - Deeply nested composition
   - Metadata "flattened": True added

   **remove_htn_identity() (4-5 tests)**:
   - Remove id_* nodes from composition
   - Remove nodes with description="identity"
   - Node with no identity subtasks unchanged
   - All subtasks are identities (returns identity node)
   - Recursive removal in nested structure

   **simplify_htn() (4-5 tests)**:
   - Unwrap single-subtask compound node
   - Multiple subtasks unchanged
   - Primitive node unchanged
   - Recursive simplification in nested structure
   - Empty subtasks unchanged

   **graph_remove_isolated_nodes() (3-4 tests)**:
   - Remove nodes with no edges
   - Graph with no isolated nodes unchanged
   - All nodes isolated (returns empty graph)
   - Preserve connected components

   **graph_deduplicate() (2-3 tests)**:
   - Graph with unique edges unchanged
   - Copy all nodes and edges correctly
   - Works with empty graph

   **optimize_workflow() (3-4 tests)**:
   - Composite transformation applies all steps
   - Returns composed morphism (verify type)
   - Test on complex HTN (flatten + remove_id + simplify)
   - Verify composition order

   **Deprecated Methods (4 tests)**:
   - htn_flatten(): deprecation warning, returns morphism
   - htn_remove_identity(): deprecation warning
   - htn_simplify(): deprecation warning
   - workflow_optimize(): deprecation warning

   **create_transformation_pipeline() (5-6 tests)**:
   - Single transformation name
   - Multiple transformations (composition)
   - Unknown transformation name raises ValueError
   - Empty list raises ValueError
   - Verify compose_chain is used
   - Test various transformation combinations

2. **Key Test Patterns**:
   - Create HTN fixtures (nested, with identities, single-subtask)
   - Create Graph fixtures (isolated nodes, connected)
   - Test morphism application: morphism(input) == expected_output
   - Verify morphism properties (name, source, target)
   - Test deprecated methods with pytest.warns
   - Test error cases with pytest.raises

3. **Code Style**:
   - Import from src.entity.category_theory.workflow_morphism
   - Import HTNNode from src.entity.htn.htn_node
   - Import Graph from src.entity.graph.graph
   - Use fixtures for common test structures
   - Add docstrings explaining transformation

4. **Output Format**:
   - Return ONLY valid Python code
   - Enclose code in markdown ```python``` blocks
   - NO explanatory text outside code blocks
   - File should start with: # tests/unit/entity/category_theory/test_workflow_morphism_comprehensive.py

**Important Notes**:
- All methods return Morphism objects (not direct transformations)
- Morphisms are callable: morphism(value) applies transformation
- optimize_workflow() uses compose_chain(flatten, remove_id, simplify)
- create_transformation_pipeline() maps names to factory methods
- Graph.edges uses lists (not sets), but duplicates handled by add_edge validation

NO LONG THINKING. Focus on generating high-quality, executable tests. Return code immediately.

Generate the complete test file now:"""

    # Generate tests
    print("\n⏱️  Generating tests with Qwen3 Instruct (no thinking mode)...")
    print("   Expected time: ~30-40 seconds...")

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
    if "workflow_morphism" not in code.lower():
        print("   ⚠️  WARNING: Workflow_morphism import may be missing")

    test_count = code.count("def test_")
    fixture_count = code.count("@pytest.fixture")
    param_count = code.count("@pytest.mark.parametrize")

    print(f"   Test functions: {test_count}")
    print(f"   Fixtures: {fixture_count}")
    print(f"   Parametrized tests: {param_count}")

    if test_count < 25:
        print(f"   ⚠️  WARNING: Only {test_count} tests generated (expected 30-35)")

    # Write to file
    output_path = project_root / "tests/unit/entity/category_theory/test_workflow_morphism_comprehensive.py"

    print(f"\n💾 Writing tests to: {output_path}")
    with open(output_path, 'w') as f:
        f.write(code)

    print("   ✅ File written successfully")

    # Instructions
    print("\n" + "=" * 80)
    print("✅ Phase 6b Test Generation Complete!")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Run tests: pytest tests/unit/entity/category_theory/test_workflow_morphism_comprehensive.py -v")
    print("2. Fix any errors found")
    print("3. Run coverage: pytest --cov=src/entity/category_theory/workflow_morphism tests/unit/entity/category_theory/test_workflow_morphism_comprehensive.py")
    print("\nExpected Result:")
    print("- 30-35 tests passing")
    print("- 90%+ coverage of Workflow_morphism entity")
    print("- All transformations validated")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
