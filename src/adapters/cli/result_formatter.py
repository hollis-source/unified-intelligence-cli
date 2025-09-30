"""
Result Formatter - CLI adapter for displaying execution results.

Clean Architecture: Adapter layer handles presentation concerns.
SRP: Single responsibility - formatting results for CLI output.
"""

import click
from typing import List, Optional
from src.entities import ExecutionResult, ExecutionStatus


class ResultFormatter:
    """
    Formats execution results for CLI display.

    Clean Architecture: Adapter for CLI presentation.
    OCP: Extend with new formatters without modifying existing code.
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize formatter with verbosity setting.

        Args:
            verbose: Enable detailed output
        """
        self.verbose = verbose

    def format_results(self, results: List[ExecutionResult]) -> None:
        """
        Display execution results to CLI.

        Clean Code: Orchestrates formatting sub-methods.

        Args:
            results: List of execution results to display
        """
        for i, result in enumerate(results):
            self._display_result_header(i + 1)
            self._display_status(result.status)
            self._display_output(result.output)
            self._display_errors(result.errors)

            if self.verbose:
                self._display_metadata(result.metadata)

    def _display_result_header(self, number: int) -> None:
        """
        Display result section header.

        Clean Code: Extract method for clarity.
        """
        click.echo(f"\n{'=' * 40}")
        click.echo(f"Result #{number}")
        click.echo(f"{'=' * 40}")

    def _display_status(self, status: ExecutionStatus) -> None:
        """
        Display execution status with color coding.

        Clean Code: Single responsibility - status display.
        """
        color = "green" if status == ExecutionStatus.SUCCESS else "red"
        click.echo(click.style(f"Status: {status.value}", fg=color))

    def _display_output(self, output: Optional[str]) -> None:
        """
        Display execution output, truncated if not verbose.

        Clean Code: Extract method for output handling.
        """
        if not output:
            return

        # Truncate output unless verbose mode
        max_length = None if self.verbose else 200
        display_output = output

        if max_length and len(output) > max_length:
            display_output = output[:max_length] + "..."

        click.echo(f"Output: {display_output}")

    def _display_errors(self, errors: List[str]) -> None:
        """
        Display errors in red.

        Clean Code: Extract method for error display.
        """
        if errors:
            error_text = ", ".join(errors)
            click.echo(click.style(f"Errors: {error_text}", fg="red"))

    def _display_metadata(self, metadata: Optional[dict]) -> None:
        """
        Display metadata in verbose mode.

        Clean Code: Extract method for metadata display.
        """
        if metadata:
            click.echo(f"Metadata: {metadata}")

    def format_error(self, message: str, error_type: str = "Error") -> None:
        """
        Display error message.

        Args:
            message: Error message to display
            error_type: Type of error (default: "Error")
        """
        click.echo(click.style(f"{error_type}: {message}", fg="red"), err=True)

    def format_success(self, message: str) -> None:
        """
        Display success message.

        Args:
            message: Success message to display
        """
        click.echo(click.style(message, fg="green"))

    def format_info(self, message: str) -> None:
        """
        Display informational message.

        Args:
            message: Info message to display
        """
        click.echo(message)

    def format_warning(self, message: str) -> None:
        """
        Display warning message.

        Args:
            message: Warning message to display
        """
        click.echo(click.style(f"Warning: {message}", fg="yellow"))