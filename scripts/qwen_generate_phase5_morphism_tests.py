#!/usr/bin/env python3
"""
Generate Phase 5 tests: Morphism entity comprehensive tests.

Uses Qwen3-Next-80B-A3B-Instruct (direct instruction mode).

Phase 5a Focus:
- Morphism creation and application
- Composition with type checking
- Identity morphisms (create_identity and deprecated identity)
- Category theory laws: associativity, left/right identity
- Chain composition (compose_chain function)
- Edge cases (empty chains, incompatible compositions)

Expected: 25-30 tests covering category theory properties.
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
    print("Phase 5a: Morphism Entity Test Generation")
    print("=" * 80)

    # Read Morphism source code
    morphism_path = project_root / "src/entity/category_theory/morphism.py"
    with open(morphism_path, 'r') as f:
        morphism_source = f.read()

    print("\n📖 Source Code Analysis:")
    print(f"   Morphism: {len(morphism_source)} chars, {len(morphism_source.splitlines())} lines")

    print("\n🔧 Features to test:")
    print("   - Morphism creation and __call__")
    print("   - compose() with type validation")
    print("   - create_identity() static method")
    print("   - identity() deprecated method (with warning)")
    print("   - verify_associativity()")
    print("   - verify_left_identity()")
    print("   - verify_right_identity()")
    print("   - compose_chain() function")
    print("   - Error handling (incompatible types)")

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
    prompt = f"""You are a Python testing expert. Generate comprehensive pytest tests for the Morphism entity.

**Source Code to Test:**

```python
{morphism_source}
```

**Requirements:**

1. **Comprehensive Coverage** (25-30 tests):
   - Morphism creation (name, source, target, transform)
   - __call__() applying transformation
   - __repr__() string representation
   - compose() with valid and invalid types
   - create_identity() static method
   - identity() deprecated method (check warning)
   - verify_associativity() with composable chain
   - verify_left_identity() law
   - verify_right_identity() law
   - compose_chain() function (2, 3, 4+ morphisms)

2. **Category Theory Laws**:
   - Identity: id_B ∘ f = f and f ∘ id_A = f
   - Associativity: (h ∘ g) ∘ f = h ∘ (g ∘ f)
   - Composition: g ∘ f only valid when f.target == g.source

3. **Parametrized Tests**:
   - Use @pytest.mark.parametrize for different transform functions
   - Test various type combinations (str→int, int→float, etc.)
   - Test edge cases (identity with itself, long chains)

4. **Code Style**:
   - Use simple lambda functions for transforms
   - Test both successful and failing compositions
   - Use pytest.raises for error cases
   - Use pytest.warns for deprecation warnings
   - Add docstrings explaining what each test validates

5. **Output Format**:
   - Return ONLY valid Python code
   - Enclose code in markdown ```python``` blocks
   - NO explanatory text outside code blocks
   - File should start with: # tests/unit/entity/category_theory/test_morphism_comprehensive.py

**Example Test Pattern:**

```python
def test_morphism_compose_valid():
    \"\"\"Test composing two morphisms with compatible types.\"\"\"
    f = Morphism("double", "int", "int", lambda x: x * 2)
    g = Morphism("to_str", "int", "str", lambda x: str(x))

    # g ∘ f: int -> int -> str
    composed = g.compose(f)

    assert composed.source == "int"
    assert composed.target == "str"
    assert composed(5) == "10"  # double then convert
```

**Important Notes:**
- Generic types (A, B, C) are for type hints, use concrete types in tests
- compose() checks self.source == other.target (NOT self.target == other.source)
- Composition order: g.compose(f) means f is applied first, then g
- compose_chain(f, g, h) = h ∘ g ∘ f (left to right application)
- create_identity() is current, identity() is deprecated

NO LONG THINKING. Focus on generating high-quality, executable tests. Return code immediately.

Generate the complete test file now:"""

    # Generate tests
    print("\n⏱️  Generating tests with Qwen3 Instruct (no thinking mode)...")
    print("   This should be faster (~20-40 seconds) than Thinking mode...")

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
    if "morphism" not in code.lower():
        print("   ⚠️  WARNING: Morphism import may be missing")

    test_count = code.count("def test_")
    param_count = code.count("@pytest.mark.parametrize")
    raises_count = code.count("pytest.raises")

    print(f"   Test functions: {test_count}")
    print(f"   Parametrized tests: {param_count}")
    print(f"   Error tests (pytest.raises): {raises_count}")

    if test_count < 20:
        print(f"   ⚠️  WARNING: Only {test_count} tests generated (expected 25-30)")

    # Create output directory if needed
    output_dir = project_root / "tests/unit/entity/category_theory"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write to file
    output_path = output_dir / "test_morphism_comprehensive.py"

    print(f"\n💾 Writing tests to: {output_path}")
    with open(output_path, 'w') as f:
        f.write(code)

    print("   ✅ File written successfully")

    # Instructions
    print("\n" + "=" * 80)
    print("✅ Phase 5a Test Generation Complete!")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Run tests: pytest tests/unit/entity/category_theory/test_morphism_comprehensive.py -v")
    print("2. Fix any errors found")
    print("3. Run coverage: pytest --cov=src/entity/category_theory/morphism tests/unit/entity/category_theory/test_morphism_comprehensive.py")
    print("\nExpected Result:")
    print("- 25-30 tests passing")
    print("- High coverage of Morphism entity")
    print("- All category theory laws validated")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
