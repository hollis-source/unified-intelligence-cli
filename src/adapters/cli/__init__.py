"""
CLI Adapters - Presentation layer for command-line interface.

Clean Architecture: Adapters depend on interfaces, not use cases.
Handles CLI-specific concerns like formatting, color output, etc.
"""

from src.adapters.cli.result_formatter import ResultFormatter

__all__ = ["ResultFormatter"]