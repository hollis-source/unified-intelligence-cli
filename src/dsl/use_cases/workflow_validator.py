"""Workflow Validator Use Case

Orchestrates end-to-end validation of DSL workflows by:
1. Parsing .ct files into AST
2. Running type inference visitor
3. Collecting and reporting errors

Clean Architecture: Use Case layer (coordinates parsing + type checking)
SOLID: SRP - only responsible for workflow validation orchestration

Story: Sprint 2, Phase 2 - Workflow Validation
"""

from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from src.dsl.adapters.parser import Parser
from src.dsl.types.type_inference_visitor import TypeInferenceVisitor
from src.dsl.types.type_checker import TypeEnvironment


@dataclass
class ValidationReport:
    """
    Report from workflow validation.

    Attributes:
        workflow_path: Path to the validated workflow file
        success: True if no errors (warnings allowed)
        errors: List of error messages
        warnings: List of warning messages
        type_environment: Built type environment (if successful)
    """
    workflow_path: Path
    success: bool
    errors: List[str]
    warnings: List[str]
    type_environment: Optional[TypeEnvironment] = None

    def has_errors(self) -> bool:
        """Check if validation found errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if validation found warnings."""
        return len(self.warnings) > 0

    def summary(self) -> str:
        """Get formatted validation summary."""
        lines = [f"Validation Report: {self.workflow_path.name}"]
        lines.append("=" * 60)
        lines.append("")

        if self.success:
            lines.append("✓ Validation PASSED")
        else:
            lines.append("✗ Validation FAILED")

        lines.append("")
        lines.append(f"Errors:   {len(self.errors)}")
        lines.append(f"Warnings: {len(self.warnings)}")
        lines.append("")

        if self.errors:
            lines.append("Errors:")
            for i, error in enumerate(self.errors, 1):
                lines.append(f"  {i}. {error}")
            lines.append("")

        if self.warnings:
            lines.append("Warnings:")
            for i, warning in enumerate(self.warnings, 1):
                lines.append(f"  {i}. {warning}")
            lines.append("")

        if self.type_environment and not self.has_errors():
            lines.append("Type Environment:")
            for name, type_sig in self.type_environment.bindings.items():
                lines.append(f"  {name} :: {type_sig}")

        return "\n".join(lines)


class WorkflowValidator:
    """
    Validates DSL workflow files for type safety.

    Coordinates parsing and type inference to catch errors
    before workflow execution. Provides rich error reports.

    Clean Architecture:
    - Use Case layer (orchestrates parsing + type checking)
    - Depends on Parser (adapter) and TypeInferenceVisitor (types)
    - No framework dependencies (pure Python)

    Example:
        validator = WorkflowValidator()
        report = validator.validate_file("examples/workflows/build.ct")
        if report.has_errors():
            print(report.summary())
    """

    def __init__(self):
        """Initialize validator with parser."""
        self.parser = Parser()

    def validate_file(self, workflow_path: str | Path) -> ValidationReport:
        """
        Validate a DSL workflow file.

        Args:
            workflow_path: Path to .ct workflow file

        Returns:
            ValidationReport with errors, warnings, and type environment

        Example:
            validator = WorkflowValidator()
            report = validator.validate_file("build.ct")

            if report.success:
                print("✓ Workflow is type-safe!")
            else:
                print(report.summary())
        """
        workflow_path = Path(workflow_path)

        # Read workflow file
        try:
            with open(workflow_path, 'r') as f:
                dsl_text = f.read()
        except FileNotFoundError:
            return ValidationReport(
                workflow_path=workflow_path,
                success=False,
                errors=[f"Workflow file not found: {workflow_path}"],
                warnings=[]
            )
        except Exception as e:
            return ValidationReport(
                workflow_path=workflow_path,
                success=False,
                errors=[f"Error reading file: {e}"],
                warnings=[]
            )

        # Parse DSL
        try:
            ast = self.parser.parse(dsl_text)
        except Exception as e:
            return ValidationReport(
                workflow_path=workflow_path,
                success=False,
                errors=[f"Parse error: {e}"],
                warnings=[]
            )

        # Run type inference
        visitor = TypeInferenceVisitor()

        # Handle both single statement and list of statements
        if isinstance(ast, list):
            # Multiple statements - visit each
            for statement in ast:
                statement.accept(visitor)
        elif ast is not None:
            # Single statement
            ast.accept(visitor)
        # else: empty program, nothing to validate

        # Build report
        success = not visitor.has_errors()

        return ValidationReport(
            workflow_path=workflow_path,
            success=success,
            errors=visitor.errors.errors.copy(),
            warnings=visitor.errors.warnings.copy(),
            type_environment=visitor.type_env if success else None
        )

    def validate_text(self, dsl_text: str, name: str = "<string>") -> ValidationReport:
        """
        Validate DSL text directly (useful for testing).

        Args:
            dsl_text: DSL program text
            name: Name for the validation report

        Returns:
            ValidationReport with errors and warnings

        Example:
            validator = WorkflowValidator()
            report = validator.validate_text('''
                fetch :: () -> Data
                process :: Data -> Result
                pipeline = process ∘ fetch
            ''')
        """
        # Parse DSL
        try:
            ast = self.parser.parse(dsl_text)
        except Exception as e:
            return ValidationReport(
                workflow_path=Path(name),
                success=False,
                errors=[f"Parse error: {e}"],
                warnings=[]
            )

        # Run type inference
        visitor = TypeInferenceVisitor()

        # Handle both single statement and list of statements
        if isinstance(ast, list):
            for statement in ast:
                statement.accept(visitor)
        elif ast is not None:
            ast.accept(visitor)

        # Build report
        success = not visitor.has_errors()

        return ValidationReport(
            workflow_path=Path(name),
            success=success,
            errors=visitor.errors.errors.copy(),
            warnings=visitor.errors.warnings.copy(),
            type_environment=visitor.type_env if success else None
        )
