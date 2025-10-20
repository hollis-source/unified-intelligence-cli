#!/usr/bin/env python3
"""
Generate Phase 5b tests: Metrics entity comprehensive tests.

Uses Qwen3-Next-80B-A3B-Instruct (direct instruction mode).

Phase 5b Focus:
- RoutingMetric, ModelSelectionMetric, TeamUtilizationMetric dataclasses
- MetricsCollector initialization and storage setup
- record_routing(), record_model_selection(), record_team_utilization()
- save() method with JSON persistence
- _calculate_summary() with aggregation logic
- get_summary() thread-safe getter
- Thread safety with concurrent access
- Edge cases (empty metrics, division by zero)

Expected: 30-35 tests covering metrics collection and aggregation.
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
    print("Phase 5b: Metrics Entity Test Generation")
    print("=" * 80)

    # Read Metrics source code
    metrics_path = project_root / "src/entity/metrics.py"
    with open(metrics_path, 'r') as f:
        metrics_source = f.read()

    print("\n📖 Source Code Analysis:")
    print(f"   Metrics: {len(metrics_source)} chars, {len(metrics_source.splitlines())} lines")

    print("\n🔧 Components to test:")
    print("   - RoutingMetric dataclass")
    print("   - ModelSelectionMetric dataclass")
    print("   - TeamUtilizationMetric dataclass")
    print("   - MetricsCollector initialization")
    print("   - record_routing() with validation")
    print("   - record_model_selection()")
    print("   - record_team_utilization()")
    print("   - save() JSON persistence")
    print("   - _calculate_summary() aggregation")
    print("   - get_summary() thread-safe access")
    print("   - Thread safety with concurrent writes")

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
    prompt = f"""You are a Python testing expert. Generate comprehensive pytest tests for the Metrics entity.

**Source Code to Test:**

```python
{metrics_source}
```

**Requirements:**

1. **Comprehensive Coverage** (30-35 tests):

   **Dataclasses (9-12 tests)**:
   - RoutingMetric: creation, to_dict(), fields, validation
   - ModelSelectionMetric: creation, to_dict(), fields
   - TeamUtilizationMetric: creation, to_dict(), fields

   **MetricsCollector (18-23 tests)**:
   - __init__: storage path creation, session ID, initial state
   - record_routing(): basic recording, validation logic (is_correct)
   - record_model_selection(): recording with fallback tracking
   - record_team_utilization(): recording team stats
   - save(): JSON file creation, data structure
   - _calculate_summary(): routing accuracy, model counts, fallback rate, team counts
   - get_summary(): thread-safe access
   - Thread safety: concurrent record calls
   - Edge cases: empty metrics (division by zero), large datasets

2. **Key Test Scenarios**:
   - Routing accuracy: 100% (all correct), 50% (half correct), 0% (none correct)
   - Model selection: multiple models, fallback usage
   - Team utilization: multiple teams with different stats
   - Summary calculations: verify percentages, counts, rounding
   - Thread safety: use threading.Thread to test concurrent access
   - File I/O: verify JSON structure matches expected format

3. **Fixtures**:
   - sample_routing_metric: Basic RoutingMetric
   - sample_model_metric: Basic ModelSelectionMetric
   - sample_team_metric: Basic TeamUtilizationMetric
   - metrics_collector: MetricsCollector with temp directory
   - Use tmp_path fixture for file operations

4. **Code Style**:
   - Use pytest fixtures (tmp_path for storage)
   - Test thread safety with threading.Thread
   - Verify JSON output with json.load()
   - Use parametrize for different metric types
   - Import from src.entity.metrics
   - Add docstrings explaining validation

5. **Output Format**:
   - Return ONLY valid Python code
   - Enclose code in markdown ```python``` blocks
   - NO explanatory text outside code blocks
   - File should start with: # tests/unit/entity/test_metrics_comprehensive.py

**Important Notes**:
- record_routing() calculates is_correct when both expected_domain and expected_team are provided
- _calculate_summary() handles division by zero (returns 0.0 for empty lists)
- Thread safety uses threading.Lock (test with concurrent calls)
- JSON persistence includes session_id, timestamp, all metrics, summary
- Summary includes: routing_accuracy, model_selection_breakdown, fallback_usage_rate, team_utilization

NO LONG THINKING. Focus on generating high-quality, executable tests. Return code immediately.

Generate the complete test file now:"""

    # Generate tests
    print("\n⏱️  Generating tests with Qwen3 Instruct (no thinking mode)...")
    print("   Expected time: ~25-30 seconds...")

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
    if "metrics" not in code.lower():
        print("   ⚠️  WARNING: Metrics import may be missing")

    test_count = code.count("def test_")
    fixture_count = code.count("@pytest.fixture")
    param_count = code.count("@pytest.mark.parametrize")

    print(f"   Test functions: {test_count}")
    print(f"   Fixtures: {fixture_count}")
    print(f"   Parametrized tests: {param_count}")

    if test_count < 25:
        print(f"   ⚠️  WARNING: Only {test_count} tests generated (expected 30-35)")

    # Write to file
    output_path = project_root / "tests/unit/entity/test_metrics_comprehensive.py"

    print(f"\n💾 Writing tests to: {output_path}")
    with open(output_path, 'w') as f:
        f.write(code)

    print("   ✅ File written successfully")

    # Instructions
    print("\n" + "=" * 80)
    print("✅ Phase 5b Test Generation Complete!")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Run tests: pytest tests/unit/entity/test_metrics_comprehensive.py -v")
    print("2. Fix any errors found")
    print("3. Run coverage: pytest --cov=src/entity/metrics tests/unit/entity/test_metrics_comprehensive.py")
    print("\nExpected Result:")
    print("- 30-35 tests passing")
    print("- 90%+ coverage of Metrics entity")
    print("- All aggregation and thread safety validated")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
