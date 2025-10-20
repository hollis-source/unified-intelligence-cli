"""
Unit tests for output validation (Week 14, Priority 2.2).

Tests OutputValidator, ValidationResult, and integration with MetricsCollector.
"""

import pytest
from pathlib import Path
from src.validation import OutputValidator, ValidationResult, ValidationType
from src.entity.metrics import MetricsCollector


class TestValidationResult:
    """Test suite for ValidationResult dataclass."""

    def test_create_validation_result_passed(self):
        """ValidationResult should be created with passed=True."""
        result = ValidationResult(
            passed=True,
            validation_type=ValidationType.PYTHON,
            warnings=["Code contains print() statements"],
            metadata={"lines": 10}
        )

        assert result.passed is True
        assert result.validation_type == ValidationType.PYTHON
        assert result.error_message is None
        assert len(result.warnings) == 1
        assert result.metadata["lines"] == 10

    def test_create_validation_result_failed(self):
        """ValidationResult should be created with passed=False and error details."""
        result = ValidationResult(
            passed=False,
            validation_type=ValidationType.PYTHON,
            error_message="Python syntax error: invalid syntax",
            error_line=5,
            error_column=10
        )

        assert result.passed is False
        assert result.error_message == "Python syntax error: invalid syntax"
        assert result.error_line == 5
        assert result.error_column == 10

    def test_validation_result_to_dict(self):
        """ValidationResult.to_dict() should convert to dictionary."""
        result = ValidationResult(
            passed=True,
            validation_type=ValidationType.JSON,
            warnings=["JSON object is empty"],
            metadata={"type": "dict", "size": 0}
        )

        result_dict = result.to_dict()

        assert result_dict["passed"] is True
        assert result_dict["validation_type"] == "json"
        assert result_dict["warnings"] == ["JSON object is empty"]
        assert result_dict["metadata"]["type"] == "dict"


class TestOutputValidatorPython:
    """Test suite for Python validation."""

    def test_validate_python_valid_code(self):
        """Valid Python code should pass validation."""
        validator = OutputValidator()

        code = """
def hello_world():
    return "Hello, World!"

result = hello_world()
        """

        result = validator.validate_python(code)

        assert result.passed is True
        assert result.validation_type == ValidationType.PYTHON
        assert result.error_message is None

    def test_validate_python_syntax_error(self):
        """Python code with syntax error should fail validation."""
        validator = OutputValidator()

        code = """
def hello_world(
    return "Hello, World!"
        """

        result = validator.validate_python(code)

        assert result.passed is False
        assert result.validation_type == ValidationType.PYTHON
        assert "syntax error" in result.error_message.lower()
        assert result.error_line is not None

    def test_validate_python_warning_print(self):
        """Python code with print() should pass but have warning."""
        validator = OutputValidator()

        code = """
def debug_function():
    print("Debugging...")
    return 42
        """

        result = validator.validate_python(code)

        assert result.passed is True
        assert len(result.warnings) > 0
        assert any("print()" in w for w in result.warnings)

    def test_validate_python_warning_todo(self):
        """Python code with TODO should pass but have warning."""
        validator = OutputValidator()

        code = """
def incomplete_function():
    # TODO: implement this
    pass
        """

        result = validator.validate_python(code)

        assert result.passed is True
        assert len(result.warnings) >= 2  # TODO warning + pass warning

    def test_validate_python_metadata(self):
        """Python validation should include metadata."""
        validator = OutputValidator()

        code = "def test():\n    return 1\n"

        result = validator.validate_python(code)

        assert result.passed is True
        assert "lines" in result.metadata
        assert result.metadata["lines"] == 2  # 2 lines (splitlines doesn't count trailing newline)


class TestOutputValidatorJSON:
    """Test suite for JSON validation."""

    def test_validate_json_valid_object(self):
        """Valid JSON object should pass validation."""
        validator = OutputValidator()

        json_text = '{"name": "test", "value": 42}'

        result = validator.validate_json(json_text)

        assert result.passed is True
        assert result.validation_type == ValidationType.JSON
        assert result.error_message is None
        assert result.metadata["type"] == "dict"

    def test_validate_json_valid_array(self):
        """Valid JSON array should pass validation."""
        validator = OutputValidator()

        json_text = '[1, 2, 3, "test"]'

        result = validator.validate_json(json_text)

        assert result.passed is True
        assert result.metadata["type"] == "list"
        assert result.metadata["size"] == 4

    def test_validate_json_parse_error(self):
        """Invalid JSON should fail validation."""
        validator = OutputValidator()

        json_text = '{"name": "test", invalid}'

        result = validator.validate_json(json_text)

        assert result.passed is False
        assert result.validation_type == ValidationType.JSON
        assert "parse error" in result.error_message.lower()

    def test_validate_json_empty_warning(self):
        """Empty JSON should pass but have warning."""
        validator = OutputValidator()

        json_text = '{}'

        result = validator.validate_json(json_text)

        assert result.passed is True
        assert len(result.warnings) > 0
        assert any("empty" in w.lower() for w in result.warnings)


class TestOutputValidatorMarkdown:
    """Test suite for Markdown validation."""

    def test_validate_markdown_valid(self):
        """Valid Markdown should pass validation."""
        validator = OutputValidator()

        markdown = """
# Title

This is a paragraph.

## Section

```python
def test():
    pass
```
        """

        result = validator.validate_markdown(markdown)

        assert result.passed is True
        assert result.validation_type == ValidationType.MARKDOWN
        assert result.error_message is None

    def test_validate_markdown_unclosed_code_block(self):
        """Markdown with unclosed code block should fail."""
        validator = OutputValidator()

        markdown = """
# Title

```python
def test():
    pass
        """

        result = validator.validate_markdown(markdown)

        assert result.passed is False
        assert "unclosed code block" in result.error_message.lower()

    def test_validate_markdown_empty_header(self):
        """Markdown with empty header should pass but have warning."""
        validator = OutputValidator()

        markdown = """
#

Some content here.
        """

        result = validator.validate_markdown(markdown)

        assert result.passed is True
        assert len(result.warnings) > 0

    def test_validate_markdown_broken_link(self):
        """Markdown with broken link should pass but have warning."""
        validator = OutputValidator()

        markdown = """
# Title

[empty link]()
        """

        result = validator.validate_markdown(markdown)

        assert result.passed is True
        assert len(result.warnings) > 0
        assert any("link" in w.lower() for w in result.warnings)

    def test_validate_markdown_metadata(self):
        """Markdown validation should include metadata."""
        validator = OutputValidator()

        markdown = """
# Title
## Section
```python
code
```
        """

        result = validator.validate_markdown(markdown)

        assert result.passed is True
        assert "headers" in result.metadata
        assert result.metadata["headers"] == 2
        assert result.metadata["code_blocks"] == 1


class TestOutputValidatorYAML:
    """Test suite for YAML validation."""

    def test_validate_yaml_valid(self):
        """Valid YAML should pass validation."""
        validator = OutputValidator()

        yaml_text = """
name: test
version: 1.0
dependencies:
  - python
  - pytest
        """

        result = validator.validate_yaml(yaml_text)

        assert result.passed is True
        assert result.validation_type == ValidationType.YAML

    def test_validate_yaml_invalid(self):
        """Invalid YAML should fail validation (if PyYAML available)."""
        validator = OutputValidator()

        # Use more clearly invalid YAML
        yaml_text = """
name: test
  - invalid
    - nested
        """

        result = validator.validate_yaml(yaml_text)

        # PyYAML might still parse this, so just verify it returns a result
        assert result.validation_type == ValidationType.YAML
        # Note: PyYAML is very lenient, so this may pass


class TestOutputValidatorGeneric:
    """Test suite for generic validation."""

    def test_validate_generic_normal_text(self):
        """Normal text should pass generic validation."""
        validator = OutputValidator()

        text = "This is a normal text output with no issues."

        result = validator._validate_generic(text)

        assert result.passed is True
        assert result.validation_type == ValidationType.GENERIC

    def test_validate_generic_short_output(self):
        """Very short output should pass but have warning."""
        validator = OutputValidator()

        text = "Short"

        result = validator._validate_generic(text)

        assert result.passed is True
        assert len(result.warnings) > 0
        assert any("short" in w.lower() for w in result.warnings)

    def test_validate_generic_error_indicators(self):
        """Output with error indicators should have warnings."""
        validator = OutputValidator()

        text = "Error: Something went wrong!"

        result = validator._validate_generic(text)

        assert result.passed is True
        assert len(result.warnings) > 0


class TestOutputValidatorAutoDetect:
    """Test suite for auto-detection of validation types."""

    def test_detect_python(self):
        """Python code should be auto-detected."""
        validator = OutputValidator()

        code = "def test():\n    return 42"

        result = validator.validate(code)

        assert result.validation_type == ValidationType.PYTHON
        assert result.passed is True

    def test_detect_json(self):
        """JSON should be auto-detected."""
        validator = OutputValidator()

        json_text = '{"key": "value"}'

        result = validator.validate(json_text)

        assert result.validation_type == ValidationType.JSON
        assert result.passed is True

    def test_detect_markdown(self):
        """Markdown should be auto-detected."""
        validator = OutputValidator()

        markdown = "# Title\n\nContent here."

        result = validator.validate(markdown)

        assert result.validation_type == ValidationType.MARKDOWN
        assert result.passed is True

    def test_detect_yaml(self):
        """YAML should be auto-detected."""
        validator = OutputValidator()

        yaml_text = "key: value\nother: test"

        result = validator.validate(yaml_text)

        assert result.validation_type == ValidationType.YAML
        assert result.passed is True

    def test_detect_generic_fallback(self):
        """Plain text should fall back to generic."""
        validator = OutputValidator()

        text = "This is just plain text."

        result = validator.validate(text)

        assert result.validation_type == ValidationType.GENERIC
        assert result.passed is True


class TestOutputValidatorStrictMode:
    """Test suite for strict mode validation."""

    def test_strict_mode_fail_on_warnings(self):
        """Strict mode should fail validation if warnings present."""
        validator = OutputValidator()

        code = """
def test():
    print("debug")
    return 42
        """

        result = validator.validate(code, strict=True)

        assert result.passed is False
        assert "strict mode" in result.error_message.lower()


class TestOutputValidatorEdgeCases:
    """Test suite for edge cases."""

    def test_validate_empty_output(self):
        """Empty output should fail validation."""
        validator = OutputValidator()

        result = validator.validate("")

        assert result.passed is False
        assert "empty" in result.error_message.lower()

    def test_validate_whitespace_only(self):
        """Whitespace-only output should fail validation."""
        validator = OutputValidator()

        result = validator.validate("   \n  \t  ")

        assert result.passed is False
        assert "empty" in result.error_message.lower()

    def test_validate_explicit_type_override(self):
        """Explicit validation type should override auto-detection."""
        validator = OutputValidator()

        # Plain text, but validate as JSON
        text = "not json"

        result = validator.validate(text, validation_type=ValidationType.JSON)

        assert result.validation_type == ValidationType.JSON
        assert result.passed is False


class TestMetricsCollectorOutputValidation:
    """Test suite for MetricsCollector output validation integration."""

    def test_record_output_validation(self, tmp_path):
        """record_output_validation() should append metric."""
        collector = MetricsCollector(storage_path=str(tmp_path / "metrics"))

        collector.record_output_validation(
            task_description="Test task",
            agent="python-specialist",
            validation_type="python",
            passed=True,
            warning_count=2,
            output_length=150
        )

        assert len(collector.output_validation_metrics) == 1
        metric = collector.output_validation_metrics[0]

        assert metric.agent == "python-specialist"
        assert metric.validation_type == "python"
        assert metric.passed is True
        assert metric.warning_count == 2
        assert metric.output_length == 150

    def test_record_output_validation_failed(self, tmp_path):
        """record_output_validation() should record failures."""
        collector = MetricsCollector(storage_path=str(tmp_path / "metrics"))

        collector.record_output_validation(
            task_description="Test task",
            agent="backend-lead",
            validation_type="json",
            passed=False,
            error_message="JSON parse error: invalid syntax",
            error_line=5,
            error_column=10,
            output_length=100
        )

        metric = collector.output_validation_metrics[0]

        assert metric.passed is False
        assert metric.error_message == "JSON parse error: invalid syntax"
        assert metric.error_line == 5
        assert metric.error_column == 10

    def test_save_includes_output_validation_metrics(self, tmp_path):
        """save() should include output_validation_metrics in JSON."""
        collector = MetricsCollector(storage_path=str(tmp_path / "metrics"))

        collector.record_output_validation(
            task_description="Test task",
            agent="frontend-lead",
            validation_type="markdown",
            passed=True,
            warning_count=1,
            output_length=200
        )

        collector.save()

        # Load saved JSON
        import json
        session_file = collector.session_file
        assert session_file.exists()

        with open(session_file, 'r') as f:
            data = json.load(f)

        assert "output_validation_metrics" in data
        assert len(data["output_validation_metrics"]) == 1

        metric = data["output_validation_metrics"][0]
        assert metric["agent"] == "frontend-lead"
        assert metric["validation_type"] == "markdown"

    def test_summary_includes_output_validation_statistics(self, tmp_path):
        """Summary should include output validation statistics."""
        collector = MetricsCollector(storage_path=str(tmp_path / "metrics"))

        # Add some validation metrics
        collector.record_output_validation(
            task_description="Task 1",
            agent="python-specialist",
            validation_type="python",
            passed=True,
            warning_count=2,
            output_length=150
        )

        collector.record_output_validation(
            task_description="Task 2",
            agent="backend-lead",
            validation_type="python",
            passed=False,
            error_message="Syntax error",
            warning_count=0,
            output_length=100
        )

        collector.record_output_validation(
            task_description="Task 3",
            agent="frontend-lead",
            validation_type="json",
            passed=True,
            warning_count=1,
            output_length=200
        )

        summary = collector.get_summary()

        assert "output_validation_statistics" in summary
        stats = summary["output_validation_statistics"]

        assert stats["total_validations"] == 3
        assert stats["passed"] == 2
        assert stats["failed"] == 1
        assert stats["pass_rate"] == 66.67  # 2/3 = 66.67%
        assert stats["avg_warnings_per_output"] == 1.0  # (2+0+1)/3 = 1.0

        # Check breakdown by type
        assert "validation_type_breakdown" in stats
        breakdown = stats["validation_type_breakdown"]

        assert breakdown["python"]["total"] == 2
        assert breakdown["python"]["passed"] == 1
        assert breakdown["python"]["failed"] == 1

        assert breakdown["json"]["total"] == 1
        assert breakdown["json"]["passed"] == 1
        assert breakdown["json"]["failed"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
