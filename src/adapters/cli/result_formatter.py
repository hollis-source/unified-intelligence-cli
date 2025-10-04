"""
Result Formatter - CLI adapter for displaying execution results.

Clean Architecture: Adapter layer handles presentation concerns.
SRP: Single responsibility - formatting results for CLI output.

Enhanced with Rich library for structured error display (Week 2).
"""

import click
from typing import List, Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
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
        self.console = Console()  # Rich console for enhanced formatting

    def format_results(self, results: List[ExecutionResult]) -> None:
        """
        Display execution results to CLI.

        Clean Code: Orchestrates formatting sub-methods.
        Enhanced: Now displays error_details with Rich formatting (Week 2).

        Args:
            results: List of execution results to display
        """
        for i, result in enumerate(results):
            self._display_result_header(i + 1)
            self._display_status(result.status)
            self._display_output(result.output)

            # Week 2: Display structured error details if present
            if result.error_details:
                self._display_error_details(result.error_details)
            elif result.errors:
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

        # Truncate output unless verbose mode (increased from 200 to 1000 for ULTRATHINK)
        max_length = None if self.verbose else 1000
        display_output = output

        if max_length and len(output) > max_length:
            display_output = output[:500] + f"\n... ({len(output)-1000} chars truncated) ...\n" + output[-500:]

        click.echo(f"Output: {display_output}")

    def _display_errors(self, errors: List[str]) -> None:
        """
        Display errors in red (fallback for simple errors).

        Clean Code: Extract method for error display.
        """
        if errors:
            error_text = ", ".join(errors)
            click.echo(click.style(f"Errors: {error_text}", fg="red"))

    def _display_error_details(self, error_details: Dict[str, Any]) -> None:
        """
        Display structured error details with Rich formatting (Week 2).

        Shows error_type, component, user_message, suggestion, and context.
        Clean Code: < 20 lines, single responsibility.

        Args:
            error_details: Structured error information
        """
        # Create Rich table for error details
        table = Table(
            title=f"❌ {error_details.get('error_type', 'Error')}",
            box=box.ROUNDED,
            title_style="bold red"
        )

        table.add_column("Field", style="cyan", no_wrap=True)
        table.add_column("Details", style="white")

        # Add key fields
        if "component" in error_details:
            table.add_row("Component", error_details["component"])
        if "user_message" in error_details:
            table.add_row("Message", error_details["user_message"])
        if "suggestion" in error_details:
            table.add_row("💡 Suggestion", error_details["suggestion"])
        if "root_cause" in error_details and self.verbose:
            table.add_row("Root Cause", error_details["root_cause"])
        if "context" in error_details and self.verbose:
            context_str = str(error_details["context"])[:100]
            table.add_row("Context", context_str)

        self.console.print(table)

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