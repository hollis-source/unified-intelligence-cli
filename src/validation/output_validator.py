"""
Output Validator - Post-execution validation of agent outputs.

Week 14: Priority 2.2 - Add output validation to catch errors in generated code.

Clean Architecture: Domain service for output quality assurance.
"""

import ast
import json
import logging
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


logger = logging.getLogger(__name__)


class ValidationType(Enum):
    """Types of validation supported."""
    PYTHON = "python"
    JSON = "json"
    MARKDOWN = "markdown"
    YAML = "yaml"
    GENERIC = "generic"


@dataclass
class ValidationResult:
    """
    Result of output validation.

    Week 14: Priority 2.2 - Track validation outcomes for metrics.
    """
    passed: bool
    validation_type: ValidationType
    error_message: Optional[str] = None
    error_line: Optional[int] = None
    error_column: Optional[int] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "passed": self.passed,
            "validation_type": self.validation_type.value,
            "error_message": self.error_message,
            "error_line": self.error_line,
            "error_column": self.error_column,
            "warnings": self.warnings,
            "metadata": self.metadata
        }


class OutputValidator:
    """
    Validates agent output for correctness and quality.

    Week 14: Priority 2.2 - Post-execution validation.

    Validation Types:
        - Python: Syntax check via ast.parse()
        - JSON: Valid JSON structure
        - Markdown: Basic structure validation
        - YAML: Valid YAML structure

    Benefits:
        - Catch syntax errors in generated code
        - Validate structured outputs (JSON, YAML)
        - Improve prompt quality via feedback loop
        - Track validation pass/fail rates

    Clean Code: Single Responsibility - output validation only.
    """

    def __init__(self):
        """Initialize output validator."""
        logger.info("OutputValidator initialized")

    def validate(
        self,
        output: str,
        validation_type: Optional[ValidationType] = None,
        strict: bool = False
    ) -> ValidationResult:
        """
        Validate output based on type.

        Args:
            output: Output text to validate
            validation_type: Type of validation (auto-detect if None)
            strict: If True, warnings cause validation to fail

        Returns:
            ValidationResult with pass/fail and error details

        Strategy:
            1. Auto-detect type if not specified
            2. Dispatch to specific validator
            3. Aggregate warnings and errors
            4. Return structured result
        """
        if not output or not output.strip():
            return ValidationResult(
                passed=False,
                validation_type=ValidationType.GENERIC,
                error_message="Output is empty"
            )

        # Auto-detect validation type
        if validation_type is None:
            validation_type = self._detect_type(output)

        logger.debug(f"Validating output as {validation_type.value}")

        # Dispatch to specific validator
        if validation_type == ValidationType.PYTHON:
            result = self.validate_python(output)
        elif validation_type == ValidationType.JSON:
            result = self.validate_json(output)
        elif validation_type == ValidationType.MARKDOWN:
            result = self.validate_markdown(output)
        elif validation_type == ValidationType.YAML:
            result = self.validate_yaml(output)
        else:
            result = self._validate_generic(output)

        # Strict mode: warnings cause failure
        if strict and result.warnings:
            result.passed = False
            result.error_message = f"Validation warnings in strict mode: {len(result.warnings)} issues"

        return result

    def validate_python(self, code: str) -> ValidationResult:
        """
        Validate Python code syntax using ast.parse().

        Args:
            code: Python code to validate

        Returns:
            ValidationResult with syntax check results

        Strategy:
            1. Attempt to parse code with ast.parse()
            2. Extract syntax error details (line, column)
            3. Check for common issues (indentation, unclosed brackets)
            4. Return detailed error information
        """
        try:
            # Parse Python code
            ast.parse(code)

            # Basic quality checks (warnings)
            warnings = []

            # Check for TODO comments
            if re.search(r'#\s*TODO|#\s*FIXME', code, re.IGNORECASE):
                warnings.append("Code contains TODO/FIXME comments")

            # Check for print statements (potential debugging)
            if 'print(' in code:
                warnings.append("Code contains print() statements (potential debugging code)")

            # Check for pass statements
            if re.search(r'^\s*pass\s*$', code, re.MULTILINE):
                warnings.append("Code contains pass statements (incomplete implementation)")

            return ValidationResult(
                passed=True,
                validation_type=ValidationType.PYTHON,
                warnings=warnings,
                metadata={"lines": len(code.splitlines())}
            )

        except SyntaxError as e:
            return ValidationResult(
                passed=False,
                validation_type=ValidationType.PYTHON,
                error_message=f"Python syntax error: {e.msg}",
                error_line=e.lineno,
                error_column=e.offset,
                metadata={"error_text": e.text.strip() if e.text else None}
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                validation_type=ValidationType.PYTHON,
                error_message=f"Python validation error: {str(e)}"
            )

    def validate_json(self, text: str) -> ValidationResult:
        """
        Validate JSON structure.

        Args:
            text: JSON text to validate

        Returns:
            ValidationResult with JSON parsing results
        """
        try:
            # Parse JSON
            data = json.loads(text)

            # Check structure
            warnings = []
            if isinstance(data, dict) and not data:
                warnings.append("JSON object is empty")
            elif isinstance(data, list) and not data:
                warnings.append("JSON array is empty")

            return ValidationResult(
                passed=True,
                validation_type=ValidationType.JSON,
                warnings=warnings,
                metadata={
                    "type": type(data).__name__,
                    "size": len(data) if isinstance(data, (dict, list)) else 1
                }
            )

        except json.JSONDecodeError as e:
            return ValidationResult(
                passed=False,
                validation_type=ValidationType.JSON,
                error_message=f"JSON parse error: {e.msg}",
                error_line=e.lineno,
                error_column=e.colno
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                validation_type=ValidationType.JSON,
                error_message=f"JSON validation error: {str(e)}"
            )

    def validate_markdown(self, text: str) -> ValidationResult:
        """
        Validate markdown structure (basic checks).

        Args:
            text: Markdown text to validate

        Returns:
            ValidationResult with markdown quality checks
        """
        warnings = []

        # Check for unclosed code blocks
        code_block_count = text.count("```")
        if code_block_count % 2 != 0:
            return ValidationResult(
                passed=False,
                validation_type=ValidationType.MARKDOWN,
                error_message="Unclosed code block (unmatched ```)"
            )

        # Check for empty sections
        if re.search(r'^#+\s*$', text, re.MULTILINE):
            warnings.append("Markdown contains empty headers")

        # Check for broken links
        broken_links = re.findall(r'\[([^\]]+)\]\(\s*\)', text)
        if broken_links:
            warnings.append(f"Found {len(broken_links)} empty links")

        return ValidationResult(
            passed=True,
            validation_type=ValidationType.MARKDOWN,
            warnings=warnings,
            metadata={
                "lines": len(text.splitlines()),
                "headers": len(re.findall(r'^#+', text, re.MULTILINE)),
                "code_blocks": code_block_count // 2
            }
        )

    def validate_yaml(self, text: str) -> ValidationResult:
        """
        Validate YAML structure.

        Args:
            text: YAML text to validate

        Returns:
            ValidationResult with YAML parsing results

        Note:
            Requires pyyaml package. Falls back to basic validation if not available.
        """
        try:
            import yaml

            # Parse YAML
            data = yaml.safe_load(text)

            warnings = []
            if data is None:
                warnings.append("YAML document is empty")

            return ValidationResult(
                passed=True,
                validation_type=ValidationType.YAML,
                warnings=warnings,
                metadata={"type": type(data).__name__ if data else "NoneType"}
            )

        except ImportError:
            # PyYAML not installed, do basic checks
            warnings = []
            if not text.strip():
                warnings.append("YAML document appears empty")

            return ValidationResult(
                passed=True,
                validation_type=ValidationType.YAML,
                warnings=warnings,
                metadata={"note": "PyYAML not available, basic validation only"}
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                validation_type=ValidationType.YAML,
                error_message=f"YAML validation error: {str(e)}"
            )

    def _validate_generic(self, text: str) -> ValidationResult:
        """
        Generic validation (basic quality checks).

        Args:
            text: Text to validate

        Returns:
            ValidationResult with basic quality checks
        """
        warnings = []

        # Check for suspiciously short output
        if len(text.strip()) < 10:
            warnings.append("Output is very short (< 10 chars)")

        # Check for error indicators
        error_patterns = [
            r'error:',
            r'exception:',
            r'failed:',
            r'traceback',
            r'fatal:'
        ]

        for pattern in error_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                warnings.append(f"Output contains error indicator: {pattern}")

        return ValidationResult(
            passed=True,
            validation_type=ValidationType.GENERIC,
            warnings=warnings,
            metadata={"length": len(text)}
        )

    def _detect_type(self, output: str) -> ValidationType:
        """
        Auto-detect validation type from output content.

        Args:
            output: Output text to analyze

        Returns:
            Detected ValidationType

        Strategy:
            1. Check for Python indicators (def, class, import)
            2. Check for JSON indicators ({ or [)
            3. Check for Markdown indicators (# headers, ``` blocks)
            4. Check for YAML indicators (key: value)
            5. Default to GENERIC
        """
        output_stripped = output.strip()

        # Python: def, class, import statements
        python_indicators = [
            r'^\s*def\s+\w+\s*\(',
            r'^\s*class\s+\w+',
            r'^\s*import\s+\w+',
            r'^\s*from\s+\w+\s+import'
        ]

        for pattern in python_indicators:
            if re.search(pattern, output, re.MULTILINE):
                return ValidationType.PYTHON

        # JSON: starts with { or [
        if output_stripped.startswith('{') or output_stripped.startswith('['):
            try:
                json.loads(output)
                return ValidationType.JSON
            except json.JSONDecodeError:
                pass

        # Markdown: has headers or code blocks
        if re.search(r'^#+\s', output, re.MULTILINE) or '```' in output:
            return ValidationType.MARKDOWN

        # YAML: has key: value patterns
        if re.search(r'^\w+:\s', output, re.MULTILINE):
            return ValidationType.YAML

        return ValidationType.GENERIC
