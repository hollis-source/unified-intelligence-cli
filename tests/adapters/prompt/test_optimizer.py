"""Tests for DSPy Prompt Optimizer.

Sprint 2, US-2.2: MIPROv2 optimizer integration.
Following TDD: Tests written before implementation.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import dspy


def test_can_import_optimizer():
    """Test that optimizer module can be imported."""
    from src.adapters.prompt import optimizer
    assert optimizer is not None


def test_prompt_optimizer_exists():
    """Test that PromptOptimizer class exists."""
    from src.adapters.prompt.optimizer import PromptOptimizer
    assert PromptOptimizer is not None


def test_optimizer_accepts_training_examples():
    """Test that optimizer can be initialized with training examples."""
    from src.adapters.prompt.optimizer import PromptOptimizer

    training_examples = [
        {"task_description": "Write multiply function", "expected_output": "def multiply(a, b):\n    return a * b"},
        {"task_description": "Write add function", "expected_output": "def add(a, b):\n    return a + b"}
    ]

    optimizer = PromptOptimizer(training_examples=training_examples)
    assert optimizer is not None
    assert len(optimizer.training_examples) == 2


def test_optimizer_accepts_metric_function():
    """Test that optimizer accepts metric function."""
    from src.adapters.prompt.optimizer import PromptOptimizer

    metric_fn = lambda example, prediction: 1.0

    optimizer = PromptOptimizer(
        training_examples=[],
        metric=metric_fn
    )

    assert optimizer.metric == metric_fn


def test_optimizer_has_default_num_trials():
    """Test that optimizer has default num_trials parameter."""
    from src.adapters.prompt.optimizer import PromptOptimizer

    optimizer = PromptOptimizer(training_examples=[])

    assert hasattr(optimizer, 'num_trials')
    assert optimizer.num_trials == 20  # Default


def test_optimizer_accepts_custom_num_trials():
    """Test that optimizer accepts custom num_trials."""
    from src.adapters.prompt.optimizer import PromptOptimizer

    optimizer = PromptOptimizer(
        training_examples=[],
        num_trials=10
    )

    assert optimizer.num_trials == 10


def test_optimizer_converts_dict_examples_to_dspy_format():
    """Test that optimizer converts dict training examples to DSPy format."""
    from src.adapters.prompt.optimizer import PromptOptimizer

    training_examples = [
        {"task_description": "Write test", "expected_output": "code"}
    ]

    optimizer = PromptOptimizer(training_examples=training_examples)

    # Should convert to dspy.Example
    assert len(optimizer.dspy_examples) == 1
    assert isinstance(optimizer.dspy_examples[0], dspy.Example)


@patch('src.adapters.prompt.optimizer.dspy.MIPROv2')
def test_optimizer_creates_miprov2_instance(mock_miprov2):
    """Test that optimizer creates MIPROv2 instance on optimize()."""
    from src.adapters.prompt.optimizer import PromptOptimizer
    from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter

    # Mock MIPROv2
    mock_optimizer_instance = Mock()
    mock_optimizer_instance.compile.return_value = Mock()  # Optimized module
    mock_miprov2.return_value = mock_optimizer_instance

    # Mock DSPy adapter
    mock_adapter = Mock(spec=DSPyPromptAdapter)
    mock_adapter.implementation_module = Mock()
    mock_adapter.design_module = Mock()
    mock_adapter.testing_module = Mock()
    mock_adapter.documentation_module = Mock()

    optimizer = PromptOptimizer(
        training_examples=[{"task_description": "test", "expected_output": "output"}],
        metric=lambda e, p: 1.0,
        num_trials=5
    )

    # Run optimization
    optimizer.optimize(mock_adapter, task_type="implementation")

    # Verify MIPROv2 was created
    mock_miprov2.assert_called_once()


def test_optimizer_saves_optimized_prompts():
    """Test that optimizer saves optimized prompts to disk."""
    from src.adapters.prompt.optimizer import PromptOptimizer
    from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter
    import tempfile
    import json

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "optimized.json"

        # Mock adapter
        mock_adapter = Mock(spec=DSPyPromptAdapter)
        mock_adapter.implementation_module = Mock()
        mock_adapter.design_module = Mock()
        mock_adapter.testing_module = Mock()
        mock_adapter.documentation_module = Mock()

        # Mock MIPROv2 to skip actual optimization
        with patch('src.adapters.prompt.optimizer.dspy.MIPROv2'):
            optimizer = PromptOptimizer(
                training_examples=[{"task_description": "test", "expected_output": "output"}],
                metric=lambda e, p: 1.0
            )

            optimizer.optimize(
                mock_adapter,
                task_type="implementation",
                output_path=str(output_path)
            )

            # Verify file was created
            assert output_path.exists()

            # Verify file contains expected fields
            with open(output_path) as f:
                data = json.load(f)
                assert "task_type" in data
                assert "optimized_at" in data
                assert data["task_type"] == "implementation"


def test_optimizer_loads_previously_optimized_prompts():
    """Test that optimizer can load previously saved optimized prompts."""
    from src.adapters.prompt.optimizer import PromptOptimizer
    import tempfile
    import json
    from datetime import datetime

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock optimized prompts file
        optimized_data = {
            "task_type": "implementation",
            "optimized_at": datetime.now().isoformat(),
            "num_trials": 20,
            "baseline_score": 0.689,
            "optimized_score": 1.0
        }

        file_path = Path(tmpdir) / "optimized.json"
        with open(file_path, 'w') as f:
            json.dump(optimized_data, f)

        # Load optimized prompts
        optimizer = PromptOptimizer(training_examples=[])
        loaded_data = optimizer.load_optimized_prompts(str(file_path))

        assert loaded_data is not None
        assert loaded_data["task_type"] == "implementation"
        assert loaded_data["optimized_score"] == 1.0


def test_optimizer_supports_task_type_routing():
    """Test that optimizer routes to correct module based on task_type."""
    from src.adapters.prompt.optimizer import PromptOptimizer
    from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter

    mock_adapter = Mock(spec=DSPyPromptAdapter)
    mock_adapter.implementation_module = Mock()
    mock_adapter.design_module = Mock()
    mock_adapter.testing_module = Mock()
    mock_adapter.documentation_module = Mock()

    with patch('src.adapters.prompt.optimizer.dspy.MIPROv2'):
        optimizer = PromptOptimizer(
            training_examples=[{"task_description": "test", "expected_output": "output"}],
            metric=lambda e, p: 1.0
        )

        # Test implementation routing
        optimizer.optimize(mock_adapter, task_type="implementation")
        # Should access implementation_module

        # Test design routing
        optimizer.optimize(mock_adapter, task_type="design")
        # Should access design_module


def test_optimizer_calculates_improvement_metrics():
    """Test that optimizer calculates baseline vs optimized metrics."""
    from src.adapters.prompt.optimizer import PromptOptimizer
    from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter

    mock_adapter = Mock(spec=DSPyPromptAdapter)
    mock_adapter.implementation_module = Mock()
    mock_adapter.design_module = Mock()
    mock_adapter.testing_module = Mock()
    mock_adapter.documentation_module = Mock()

    # Mock metric that returns different scores
    call_count = [0]
    def mock_metric(example, prediction):
        call_count[0] += 1
        # First calls (baseline): return 0.6
        # Later calls (optimized): return 1.0
        return 0.6 if call_count[0] <= 2 else 1.0

    with patch('src.adapters.prompt.optimizer.dspy.MIPROv2'):
        optimizer = PromptOptimizer(
            training_examples=[{"task_description": "test", "expected_output": "output"}],
            metric=mock_metric
        )

        result = optimizer.optimize(mock_adapter, task_type="implementation")

        # Should calculate improvement
        assert "baseline_score" in result
        assert "optimized_score" in result
        assert "improvement" in result


def test_optimizer_handles_empty_training_examples():
    """Test that optimizer handles empty training examples gracefully."""
    from src.adapters.prompt.optimizer import PromptOptimizer

    optimizer = PromptOptimizer(training_examples=[])
    assert optimizer.dspy_examples == []
