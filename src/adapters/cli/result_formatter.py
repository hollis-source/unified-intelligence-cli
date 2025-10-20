"""
Result Formatter - CLI adapter for displaying execution results.

Clean Architecture: Adapter layer handles presentation concerns.
SRP: Single responsibility - formatting results for CLI output.

Enhanced with Rich library for structured error display (Week 2).
"""

import click
from typing import List, Optional, Dict, Any, Tuple
import json
import re
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from src.entity import ExecutionResult, ExecutionStatus
from src.adapters.cli.claude_settings import ClaudeOutputSettings


class ResultFormatter:
    """
    Formats execution results for CLI display.

    Clean Architecture: Adapter for CLI presentation.
    OCP: Extend with new formatters without modifying existing code.
    """

    def __init__(self, verbose: bool = False, settings: Optional[ClaudeOutputSettings] = None, correlation_id: Optional[str] = None):
        """
        Initialize formatter with verbosity setting and Claude output hooks.

        Args:
            verbose: legacy verbosity flag (used if settings.verbosity not provided)
            settings: ClaudeOutputSettings controlling output hooks
            correlation_id: Optional correlation ID to display if enabled
        """
        self.console = Console()  # Rich console for enhanced formatting
        self.settings = settings or ClaudeOutputSettings.defaults()
        # Backward compat: if caller passes verbose but settings say quiet/normal, we treat as a display hint only
        self.correlation_id = correlation_id

    def format_results(self, results: List[ExecutionResult]) -> None:
        """
        Display execution results to CLI.

        Clean Code: Orchestrates formatting sub-methods.
        Enhanced: Now displays error_details with Rich formatting (Week 2).

        Args:
            results: List of execution results to display
        """
        # Header with correlation id if configured
        if self.settings.include_correlation_id and self.correlation_id:
            click.echo(f"cid={self.correlation_id}")

        for i, result in enumerate(results):
            # Quiet mode: essentials only (status); no headers, no output, no traces/diagnostics
            if self.settings.verbosity == "quiet":
                self._display_status(result.status)
                continue

            # Normal/Verbose/Debug
            self._display_result_header(i + 1)
            self._display_status(result.status)

            # Render output with redaction, wrapping, inline code policy, and truncation
            processed_output = self._process_output_text(
                result.output or "",
                result.metadata or {}
            )
            if processed_output:
                click.echo(processed_output)

            # Errors (suppress diagnostics in quiet; already handled above)
            if result.error_details and self.settings.verbosity in ("verbose", "debug"):
                self._display_error_details(result.error_details)
            elif result.errors and self.settings.verbosity != "quiet":
                self._display_errors(result.errors)

            # Verbosity gates for metadata/routing
            if self.settings.verbosity in ("verbose", "debug"):
                self._display_routing_trace(result.metadata or {})
                self._display_metadata(result.metadata)

    def _process_output_text(self, text: str, metadata: Dict[str, Any]) -> str:
        if not text:
            return ""
        s = text
        # Thought redaction
        if self.settings.redact_thoughts:
            for tag in self.settings.thought_tag_names:
                pattern = re.compile(fr"<{tag}>.*?</{tag}>", re.DOTALL)
                prev = None
                while prev != s:
                    prev = s
                    s = pattern.sub("", s)
        # Code wrapping policy
        s = self._apply_code_wrapping(s)
        # Inline code policy
        if not self.settings.inline_code_allowed:
            s = re.sub(r"`([^`\n]+)`", r"\1", s)
        # Cache annotations
        if self.settings.show_cache_annotations and isinstance(metadata, dict):
            cache_hit = metadata.get("cache_hit")
            ttl = metadata.get("ttl")
            if cache_hit is not None:
                ann = f"(cache: {'hit' if cache_hit else 'miss'}"
                if isinstance(ttl, int):
                    ann += f"; ttl: {ttl}s"
                ann += ")"
                s = s + ("\n" if not s.endswith("\n") else "") + ann
        # Truncation with safe boundaries
        if self.settings.max_chars and self.settings.max_chars > 0:
            s = self._safe_truncate(s, self.settings.max_chars)
        return s

    def _apply_code_wrapping(self, s: str) -> str:
        mode = self.settings.wrap_code_blocks
        if mode == "none":
            return s
        # Detect fenced blocks ```lang\n...\n```
        fenced_re = re.compile(r"```(\w+)?\n([\s\S]*?)```", re.MULTILINE)
        def repl(m):
            lang = m.group(1) or ""
            body = m.group(2)
            if mode == "fenced":
                return f"```{lang}\n{body}```"
            # augment_code_snippet
            return f"<augment_code_snippet mode=\"EXCERPT\">\n````{lang}\n{body}````\n</augment_code_snippet>"
        return fenced_re.sub(repl, s)

    def _safe_truncate(self, s: str, max_chars: int) -> str:
        if len(s) <= max_chars:
            return s
        # Avoid truncating inside fenced or augment blocks. Find the last safe index <= max_chars
        block_ranges: List[Tuple[int,int]] = []
        for m in re.finditer(r"<augment_code_snippet[\s\S]*?</augment_code_snippet>", s):
            block_ranges.append((m.start(), m.end()))
        for m in re.finditer(r"```[\s\S]*?```", s):
            block_ranges.append((m.start(), m.end()))
        def inside(i):
            return any(a <= i < b for a,b in block_ranges)
        cut = max_chars
        while cut > 0 and inside(cut):
            # move to end of the block
            for a,b in block_ranges:
                if a <= cut < b:
                    cut = b
                    break
            if cut >= len(s):
                return s  # nothing to truncate safely
        return s[:cut] + "…"

    def _display_routing_trace(self, metadata: Dict[str, Any]) -> None:
        if not self.settings.include_routing_trace:
            return
        routing = metadata.get("routing_path") or metadata.get("routing")
        if not routing:
            return
        fmt = self.settings.routing_trace_format
        human = f"Route: {routing.get('domain','?')} → {routing.get('team','?')} → {routing.get('agent','?')}"
        if self.settings.show_top3_domain_scores and 'scores' in routing and self.settings.verbosity in ("verbose","debug"):
            human += f" | top3={routing['scores']}"
        if fmt in ("human","both"):
            click.echo(human)
        if fmt in ("json","both"):
            click.echo(json.dumps({"routing_path": routing}))

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