"""
Tests for DSPy Signatures.

Sprint 1, US-1.1: Test-driven development for DSPy signatures.
Following TDD: Tests written before implementation.
"""

import pytest
import dspy


def test_can_import_signatures():
    """Test that signature module can be imported."""
    from src.adapters.prompt import dspy_signatures
    assert dspy_signatures is not None


def test_implementation_signature_exists():
    """Test that ImplementationSignature class exists."""
    from src.adapters.prompt.dspy_signatures import ImplementationSignature
    assert ImplementationSignature is not None


def test_implementation_signature_has_required_input_fields():
    """Test that ImplementationSignature has task_description and previous_outputs input fields."""
    from src.adapters.prompt.dspy_signatures import ImplementationSignature

    # Check that signature has input fields
    # In DSPy 3.x, signatures define fields in __annotations__
    assert 'task_description' in ImplementationSignature.__annotations__
    assert 'previous_outputs' in ImplementationSignature.__annotations__


def test_implementation_signature_has_code_output_field():
    """Test that ImplementationSignature has code output field."""
    from src.adapters.prompt.dspy_signatures import ImplementationSignature

    assert 'code' in ImplementationSignature.__annotations__


def test_implementation_signature_is_dspy_signature():
    """Test that ImplementationSignature inherits from dspy.Signature."""
    from src.adapters.prompt.dspy_signatures import ImplementationSignature

    # Check that it's a proper DSPy signature
    assert issubclass(ImplementationSignature, dspy.Signature)


def test_implementation_signature_output_has_description():
    """Test that code output field has descriptive text to guide LLM."""
    from src.adapters.prompt.dspy_signatures import ImplementationSignature

    # DSPy 3.x uses __annotations__ and field metadata
    # Check that there's a docstring or description
    assert ImplementationSignature.__doc__ is not None
    assert 'implementation' in ImplementationSignature.__doc__.lower() or 'code' in ImplementationSignature.__doc__.lower()


def test_implementation_signature_works_with_predict_module():
    """Test that ImplementationSignature can be used with dspy.Predict."""
    from src.adapters.prompt.dspy_signatures import ImplementationSignature

    # Should be able to create a Predict module
    # Note: This doesn't require LLM, just module construction
    predictor = dspy.Predict(ImplementationSignature)
    assert predictor is not None


def test_design_signature_exists():
    """Test that DesignSignature exists for design tasks."""
    from src.adapters.prompt.dspy_signatures import DesignSignature
    assert DesignSignature is not None
    assert issubclass(DesignSignature, dspy.Signature)


def test_testing_signature_exists():
    """Test that TestingSignature exists for test generation tasks."""
    from src.adapters.prompt.dspy_signatures import TestingSignature
    assert TestingSignature is not None
    assert issubclass(TestingSignature, dspy.Signature)


def test_documentation_signature_exists():
    """Test that DocumentationSignature exists for documentation tasks."""
    from src.adapters.prompt.dspy_signatures import DocumentationSignature
    assert DocumentationSignature is not None
    assert issubclass(DocumentationSignature, dspy.Signature)


def test_testing_signature_has_code_to_test_field():
    """Test that TestingSignature has field for code to be tested."""
    from src.adapters.prompt.dspy_signatures import TestingSignature

    assert 'code_to_test' in TestingSignature.__annotations__


def test_documentation_signature_has_code_or_api_field():
    """Test that DocumentationSignature has field for code/API to document."""
    from src.adapters.prompt.dspy_signatures import DocumentationSignature

    assert 'code_or_api' in DocumentationSignature.__annotations__
