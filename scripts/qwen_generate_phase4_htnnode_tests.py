#!/usr/bin/env python3
"""
Generate Phase 4 tests: HTNNode entity comprehensive tests.

Uses Qwen3-Next-80B-A3B-Instruct with thinking mode enabled.

Phase 4 Focus:
- HTNNode entity (hierarchical task network node)
- Recursive task decomposition
- Preconditions and effects management
- Graph-theoretic operations (get_depth, is_primitive, is_compound)
- Decompose method with custom strategies

Expected: 25-30 tests covering complex hierarchical structures.
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
    print("Phase 4: HTNNode Entity Test Generation")
    print("=" * 80)

    # Read HTNNode source code
    htnnode_path = project_root / "src/entity/htn/htn_node.py"
    with open(htnnode_path, 'r') as f:
        htnnode_source = f.read()

    print("\n📖 Source Code Analysis:")
    print(f"   HTNNode: {len(htnnode_source)} chars, {len(htnnode_source.splitlines())} lines")

    print("\n🔧 Methods to test:")
    print("   - is_primitive()")
    print("   - is_compound()")
    print("   - add_subtask()")
    print("   - check_preconditions()")
    print("   - apply_effects()")
    print("   - decompose() [most complex - recursive]")
    print("   - get_depth()")
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
    prompt = f"""You are a Python testing expert. Generate comprehensive pytest tests for the HTNNode entity.

**Source Code to Test:**

```python
{htnnode_source}
```

**Requirements:**

1. **Comprehensive Coverage** (25-30 tests):
   - HTNNode creation (task_id, description, subtasks, preconditions, effects, metadata)
   - is_primitive() method (no subtasks = True)
   - is_compound() method (has subtasks = True)
   - add_subtask() method (add child nodes)
   - check_preconditions() method (state validation)
   - apply_effects() method (immutable state updates)
   - decompose() method (recursive decomposition, precondition checking)
   - get_depth() method (recursive depth calculation)
   - __repr__() method

2. **Recursive Structure Tests**:
   - Test hierarchies: primitive tasks, 1-level hierarchies, multi-level hierarchies
   - Test decompose() with various depths
   - Test custom decomposition functions
   - Test precondition failures raising ValueError

3. **Parametrized Tests**:
   - Use @pytest.mark.parametrize for state/precondition scenarios
   - Test various precondition combinations
   - Test effect applications

4. **Edge Cases**:
   - Empty subtasks list
   - Missing state keys
   - Failed preconditions
   - Deep hierarchies (3+ levels)
   - Custom decomposition strategies

5. **Code Style**:
   - Import from src.entity.htn.htn_node (NOT src.entities)
   - Use descriptive test names
   - Add docstrings explaining what each test validates
   - Test immutability (apply_effects returns new state, doesn't mutate)

6. **Output Format**:
   - Return ONLY valid Python code
   - Enclose code in markdown ```python``` blocks
   - NO explanatory text outside code blocks
   - File should start with: # tests/unit/entity/test_htnnode_comprehensive.py

**Important Notes:**
- decompose() is recursive and complex - test multiple levels
- check_preconditions() requires exact match (key exists AND value equals)
- apply_effects() creates NEW state dict (immutable pattern)
- get_depth() recursively calculates max depth to leaf
- Test ValueError raised when preconditions not satisfied

NO LONG THINKING. Focus on generating high-quality, executable tests. Return code immediately.

Generate the complete test file now:"""

    # Generate tests
    print("\n⏱️  Generating tests with Qwen3 (thinking mode enabled)...")
    print("   This may take 30-60 seconds due to recursive decomposition logic...")

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
    if "src.entity.htn.htn_node" not in code and "HTNNode" not in code:
        print("   ⚠️  WARNING: Import path may be incorrect")

    test_count = code.count("def test_")
    fixture_count = code.count("@pytest.fixture")
    param_count = code.count("@pytest.mark.parametrize")

    print(f"   Test functions: {test_count}")
    print(f"   Fixtures: {fixture_count}")
    print(f"   Parametrized tests: {param_count}")

    if test_count < 20:
        print(f"   ⚠️  WARNING: Only {test_count} tests generated (expected 25-30)")

    # Write to file
    output_path = project_root / "tests/unit/entity/test_htnnode_comprehensive.py"

    print(f"\n💾 Writing tests to: {output_path}")
    with open(output_path, 'w') as f:
        f.write(code)

    print("   ✅ File written successfully")

    # Instructions
    print("\n" + "=" * 80)
    print("✅ Phase 4 HTNNode Test Generation Complete!")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Run tests: pytest tests/unit/entity/test_htnnode_comprehensive.py -v")
    print("2. Fix any errors found")
    print("3. Run coverage: pytest --cov=src.entity.htn.htn_node tests/unit/entity/test_htnnode_comprehensive.py")
    print("\nExpected Result:")
    print("- 25-30 tests passing")
    print("- High coverage of HTNNode entity")
    print("- All recursive decomposition behaviors validated")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
