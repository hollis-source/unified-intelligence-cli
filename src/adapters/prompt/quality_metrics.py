"""Quality Metric Evaluator for DSPy Optimization.

Sprint 2, US-2.1: Automated quality metrics for LLM outputs.

This module provides quality metrics for evaluating code generation:
- Syntax correctness (AST parsing)
- Completeness (no TODOs/placeholders)
- Conciseness (no thinking verbosity)

Clean Architecture:
- Pure functions for each metric
- DSPy-compatible metric interface
- Configurable weights for optimization goals
"""

import ast
import re
import logging
from typing import Callable, Optional
import dspy

logger = logging.getLogger(__name__)


class QualityMetricEvaluator:
    """
    Evaluator for code quality metrics.

    Provides both individual metrics and a weighted overall score
    for DSPy prompt optimization.

    Attributes:
        syntax_weight: Weight for syntax correctness (default: 0.4)
        completeness_weight: Weight for completeness (default: 0.4)
        conciseness_weight: Weight for conciseness (default: 0.2)
    """

    def __init__(
        self,
        syntax_weight: float = 0.4,
        completeness_weight: float = 0.4,
        conciseness_weight: float = 0.2
    ):
        """
        Initialize quality metric evaluator.

        Args:
            syntax_weight: Weight for syntax correctness metric
            completeness_weight: Weight for completeness metric
            conciseness_weight: Weight for conciseness metric
        """
        if abs(syntax_weight + completeness_weight + conciseness_weight - 1.0) > 0.01:
            raise ValueError("Metric weights must sum to 1.0")

        self.syntax_weight = syntax_weight
        self.completeness_weight = completeness_weight
        self.conciseness_weight = conciseness_weight

    def measure_syntax_correctness(self, code: str) -> float:
        """
        Measure syntax correctness of code.

        Attempts to parse code as Python AST. Returns 1.0 if valid,
        0.0 if syntax errors detected.

        Args:
            code: Code string to evaluate

        Returns:
            1.0 if syntax correct, 0.0 otherwise
        """
        if not code or not code.strip():
            return 0.0

        # Extract code from markdown fences if present
        code_clean = self._extract_code_from_fences(code)

        try:
            ast.parse(code_clean)
            return 1.0
        except SyntaxError:
            return 0.0
        except Exception:
            # Other parsing errors (e.g., encoding issues)
            return 0.0

    def measure_completeness(self, code: str) -> float:
        """
        Measure code completeness (no TODOs/placeholders).

        Returns 1.0 if code is complete, 0.0 if incomplete patterns found.

        Incomplete patterns:
        - "# TODO"
        - "# Similar to"
        - "NotImplementedError"
        - "pass  # implement"
        - "# ..."

        Args:
            code: Code string to evaluate

        Returns:
            1.0 if complete, 0.0 if incomplete
        """
        if not code or not code.strip():
            return 0.0

        incomplete_patterns = [
            r'#\s*TODO',
            r'#\s*Similar',
            r'NotImplementedError',
            r'pass\s*#.*implement',
            r'#\s*\.{3}',  # "# ..."
            r'#\s*rest of'
        ]

        code_lower = code.lower()

        for pattern in incomplete_patterns:
            if re.search(pattern, code_lower, re.IGNORECASE):
                return 0.0

        return 1.0

    def measure_conciseness(self, code: str) -> float:
        """
        Measure code conciseness (no thinking verbosity).

        Returns 1.0 if concise, 0.0 if thinking patterns found.

        Thinking patterns (at start of output):
        - "Okay,"
        - "Let me"
        - "I need to"
        - "First,"
        - "Wait,"

        Args:
            code: Code string to evaluate

        Returns:
            1.0 if concise, 0.0 if verbose
        """
        if not code or not code.strip():
            return 0.0

        thinking_patterns = [
            r'^Okay,',
            r'^Let me\s',
            r'^I need to\s',
            r'^First,',
            r'^Wait,',
            r'^Hmm,',
            r'^So,',
            r'^Now,',
            r'^The\s+task',
            r'^I should',
            r'^We should'
        ]

        # Check first 200 characters for thinking
        code_start = code[:200]

        for pattern in thinking_patterns:
            if re.search(pattern, code_start, re.MULTILINE | re.IGNORECASE):
                return 0.0

        return 1.0

    def calculate_quality_score(self, code: str) -> float:
        """
        Calculate overall quality score (weighted).

        Combines syntax, completeness, and conciseness metrics
        with configured weights.

        Args:
            code: Code string to evaluate

        Returns:
            Weighted quality score (0.0-1.0)
        """
        syntax = self.measure_syntax_correctness(code)
        completeness = self.measure_completeness(code)
        conciseness = self.measure_conciseness(code)

        score = (
            syntax * self.syntax_weight +
            completeness * self.completeness_weight +
            conciseness * self.conciseness_weight
        )

        return score

    def get_dspy_metric(self) -> Callable:
        """
        Get DSPy-compatible metric function.

        Returns a metric function with signature:
            (example: dspy.Example, prediction: dspy.Prediction) -> float

        This function can be passed to DSPy optimizers like MIPROv2.

        Returns:
            Metric function for DSPy optimization
        """
        def metric(example: dspy.Example, prediction: dspy.Prediction) -> float:
            """
            DSPy metric function.

            Evaluates prediction quality based on code output.

            Args:
                example: DSPy example (contains expected output)
                prediction: DSPy prediction (contains generated code)

            Returns:
                Quality score (0.0-1.0)
            """
            # Extract code from prediction
            # DSPy predictions can have different field names
            code = None
            if hasattr(prediction, 'code'):
                code = prediction.code
            elif hasattr(prediction, 'output'):
                code = prediction.output
            elif hasattr(prediction, 'answer'):
                code = prediction.answer
            else:
                logger.warning("Prediction has no code/output/answer field")
                return 0.0

            if not code:
                return 0.0

            # Calculate quality score
            return self.calculate_quality_score(code)

        return metric

    def _extract_code_from_fences(self, code: str) -> str:
        """
        Extract code from markdown fences if present.

        Args:
            code: Potentially fenced code

        Returns:
            Clean code without fences
        """
        # Check for ```python fences
        match = re.search(r'```python\s*\n(.*?)```', code, re.DOTALL)
        if match:
            return match.group(1)

        # Check for generic ``` fences
        match = re.search(r'```\s*\n(.*?)```', code, re.DOTALL)
        if match:
            return match.group(1)

        # No fences, return as-is
        return code
