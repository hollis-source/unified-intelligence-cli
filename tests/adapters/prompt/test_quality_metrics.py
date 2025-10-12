"""Tests for Quality Metric Evaluator.

Sprint 2, US-2.1: Automated quality metrics for DSPy optimization.
Following TDD: Tests written before implementation.
"""

import pytest
import dspy


def test_can_import_quality_metrics():
    """Test that quality metrics module can be imported."""
    from src.adapters.prompt import quality_metrics
    assert quality_metrics is not None


def test_quality_metric_evaluator_exists():
    """Test that QualityMetricEvaluator class exists."""
    from src.adapters.prompt.quality_metrics import QualityMetricEvaluator
    assert QualityMetricEvaluator is not None


def test_evaluator_can_measure_syntax_correctness():
    """Test syntax correctness metric for valid Python code."""
    from src.adapters.prompt.quality_metrics import QualityMetricEvaluator

    evaluator = QualityMetricEvaluator()

    # Valid code
    valid_code = "def multiply(a, b):\n    return a * b"
    score = evaluator.measure_syntax_correctness(valid_code)
    assert score == 1.0

    # Invalid code
    invalid_code = "def multiply(a, b)\n    return a * b"  # Missing colon
    score = evaluator.measure_syntax_correctness(invalid_code)
    assert score == 0.0


def test_evaluator_handles_code_with_markdown_fences():
    """Test that evaluator can extract code from markdown fences."""
    from src.adapters.prompt.quality_metrics import QualityMetricEvaluator

    evaluator = QualityMetricEvaluator()

    code_with_fences = """```python
def multiply(a, b):
    return a * b
```"""

    score = evaluator.measure_syntax_correctness(code_with_fences)
    assert score == 1.0


def test_evaluator_can_measure_completeness():
    """Test completeness metric (no TODOs/placeholders)."""
    from src.adapters.prompt.quality_metrics import QualityMetricEvaluator

    evaluator = QualityMetricEvaluator()

    # Complete code
    complete_code = "def multiply(a, b):\n    return a * b"
    score = evaluator.measure_completeness(complete_code)
    assert score == 1.0

    # Incomplete code with TODO
    incomplete_code = "def multiply(a, b):\n    # TODO: implement\n    pass"
    score = evaluator.measure_completeness(incomplete_code)
    assert score == 0.0

    # Incomplete with placeholder
    placeholder_code = "def multiply(a, b):\n    # Similar to add function\n    pass"
    score = evaluator.measure_completeness(placeholder_code)
    assert score == 0.0


def test_evaluator_can_measure_conciseness():
    """Test conciseness metric (no thinking verbosity)."""
    from src.adapters.prompt.quality_metrics import QualityMetricEvaluator

    evaluator = QualityMetricEvaluator()

    # Concise code (no thinking)
    concise_code = "def multiply(a, b):\n    return a * b"
    score = evaluator.measure_conciseness(concise_code)
    assert score == 1.0

    # Verbose code with thinking
    verbose_code = "Okay, let me think about this.\n\ndef multiply(a, b):\n    return a * b"
    score = evaluator.measure_conciseness(verbose_code)
    assert score == 0.0


def test_evaluator_calculates_weighted_quality_score():
    """Test overall quality score calculation (weighted)."""
    from src.adapters.prompt.quality_metrics import QualityMetricEvaluator

    evaluator = QualityMetricEvaluator()

    # Perfect code: 100% quality
    perfect_code = "def multiply(a, b):\n    return a * b"
    score = evaluator.calculate_quality_score(perfect_code)
    assert score == 1.0

    # Code with syntax error: 0% syntax, 100% complete, 100% concise
    # Expected: 0.4*0 + 0.4*1 + 0.2*1 = 0.6
    syntax_error_code = "def multiply(a, b)\n    return a * b"  # Missing colon
    score = evaluator.calculate_quality_score(syntax_error_code)
    assert score == pytest.approx(0.6, abs=0.01)

    # Code with TODO: 100% syntax, 0% complete, 100% concise
    # Expected: 0.4*1 + 0.4*0 + 0.2*1 = 0.6
    incomplete_code = "def multiply(a, b):\n    # TODO: implement\n    pass"
    score = evaluator.calculate_quality_score(incomplete_code)
    assert score == pytest.approx(0.6, abs=0.01)

    # Code with thinking: 0% syntax (not valid Python), 100% complete, 0% concise
    # Expected: 0.4*0 + 0.4*1 + 0.2*0 = 0.4
    verbose_code = "Let me think.\n\ndef multiply(a, b):\n    return a * b"
    score = evaluator.calculate_quality_score(verbose_code)
    assert score == pytest.approx(0.4, abs=0.01)


def test_evaluator_returns_dspy_compatible_metric_function():
    """Test that evaluator can create DSPy-compatible metric function."""
    from src.adapters.prompt.quality_metrics import QualityMetricEvaluator

    evaluator = QualityMetricEvaluator()
    metric_fn = evaluator.get_dspy_metric()

    # DSPy metric signature: (example, prediction) -> float
    assert callable(metric_fn)

    # Create mock DSPy example and prediction
    example = dspy.Example(
        task_description="Write multiply function",
        expected_output="def multiply(a, b):\n    return a * b"
    ).with_inputs("task_description")

    # Perfect prediction
    prediction = dspy.Prediction(code="def multiply(a, b):\n    return a * b")
    score = metric_fn(example, prediction)
    assert score == 1.0

    # Imperfect prediction
    prediction = dspy.Prediction(code="def multiply(a, b):\n    # TODO\n    pass")
    score = metric_fn(example, prediction)
    assert score < 1.0


def test_evaluator_handles_empty_code():
    """Test that evaluator handles empty code gracefully."""
    from src.adapters.prompt.quality_metrics import QualityMetricEvaluator

    evaluator = QualityMetricEvaluator()

    score = evaluator.calculate_quality_score("")
    assert score == 0.0


def test_evaluator_handles_non_python_code():
    """Test that evaluator can handle non-Python code."""
    from src.adapters.prompt.quality_metrics import QualityMetricEvaluator

    evaluator = QualityMetricEvaluator()

    # JavaScript code (invalid Python syntax)
    js_code = "function multiply(a, b) { return a * b; }"
    score = evaluator.measure_syntax_correctness(js_code)
    assert score == 0.0


def test_evaluator_detects_multiple_incomplete_patterns():
    """Test that evaluator detects various incomplete patterns."""
    from src.adapters.prompt.quality_metrics import QualityMetricEvaluator

    evaluator = QualityMetricEvaluator()

    patterns = [
        "# TODO: implement",
        "# Similar to foo",
        "raise NotImplementedError",
        "pass  # implement this",
        "# ... rest of implementation"
    ]

    for pattern in patterns:
        code = f"def test():\n    {pattern}"
        score = evaluator.measure_completeness(code)
        assert score == 0.0, f"Failed to detect incomplete pattern: {pattern}"


def test_evaluator_detects_multiple_thinking_patterns():
    """Test that evaluator detects various thinking patterns."""
    from src.adapters.prompt.quality_metrics import QualityMetricEvaluator

    evaluator = QualityMetricEvaluator()

    patterns = [
        "Okay, let me think",
        "Let me approach this",
        "I need to implement",
        "First, we should",
        "Wait, I should"
    ]

    for pattern in patterns:
        code = f"{pattern}\n\ndef test():\n    pass"
        score = evaluator.measure_conciseness(code)
        assert score == 0.0, f"Failed to detect thinking pattern: {pattern}"


def test_evaluator_customizable_weights():
    """Test that evaluator accepts custom metric weights."""
    from src.adapters.prompt.quality_metrics import QualityMetricEvaluator

    # Custom weights: syntax=0.5, complete=0.3, concise=0.2
    evaluator = QualityMetricEvaluator(
        syntax_weight=0.5,
        completeness_weight=0.3,
        conciseness_weight=0.2
    )

    # Code with syntax error only
    code = "def test()\n    pass"
    score = evaluator.calculate_quality_score(code)
    # Expected: 0.5*0 + 0.3*1 + 0.2*1 = 0.5
    assert score == pytest.approx(0.5, abs=0.01)
