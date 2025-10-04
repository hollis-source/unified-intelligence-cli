"""CLI Integration for DSL - Run .ct programs from command line.

Clean Architecture: Adapter layer for CLI.
SOLID: SRP - only handles DSL file execution.
"""

import asyncio
from pathlib import Path
from typing import Any
import click

from src.dsl.adapters.parser import Parser
from src.dsl.use_cases.interpreter import Interpreter
from src.dsl.adapters.cli_task_executor import CLITaskExecutor


def read_dsl_file(file_path: str) -> str:
    """
    Read DSL program from .ct file.

    Args:
        file_path: Path to .ct file

    Returns:
        DSL program text

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file can't be read
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"DSL file not found: {file_path}")

    if not path.suffix == ".ct":
        click.echo(f"Warning: Expected .ct extension, got {path.suffix}", err=True)

    with open(path, 'r') as f:
        return f.read()


async def execute_dsl_program(dsl_text: str, verbose: bool = False) -> Any:
    """
    Execute DSL program.

    Args:
        dsl_text: DSL program text
        verbose: Enable verbose output

    Returns:
        Execution result
    """
    if verbose:
        click.echo(f"Parsing DSL program...")
        click.echo(f"Program:\n{dsl_text}\n")

    # Parse DSL → AST
    parser = Parser()
    try:
        ast = parser.parse(dsl_text)
        if verbose:
            click.echo(f"Parsed AST: {ast}\n")
    except Exception as e:
        click.echo(f"Parse error: {e}", err=True)
        raise

    # Extract main functor or last AST node
    # Parser returns list of nodes (type annotations + functors)
    if isinstance(ast, list):
        # Find last functor (main workflow) or use last node
        functors = [node for node in ast if hasattr(node, 'name')]
        if functors:
            main_node = functors[-1]  # Last functor is main workflow
            if verbose:
                click.echo(f"Executing functor: {main_node.name}\n")
        else:
            main_node = ast[-1] if ast else None
    else:
        main_node = ast

    if main_node is None:
        click.echo("Error: No executable node found in DSL program", err=True)
        raise ValueError("Empty DSL program")

    # Build symbol table from functors
    symbol_table = {}
    if isinstance(ast, list):
        for node in ast:
            if hasattr(node, 'name') and hasattr(node, 'expression'):
                # Store functor definition
                symbol_table[node.name] = node.expression

    # Create executor with symbol table support
    executor = CLITaskExecutor()
    interpreter = Interpreter(executor)

    # Add symbol table to interpreter (if it supports it)
    if hasattr(interpreter, 'set_symbol_table'):
        interpreter.set_symbol_table(symbol_table)

    if verbose:
        if symbol_table:
            click.echo(f"Defined functors: {list(symbol_table.keys())}\n")
        click.echo("Executing DSL program...")

    # Execute
    try:
        result = await interpreter.execute(main_node)
        return result
    except Exception as e:
        click.echo(f"Execution error: {e}", err=True)
        raise


def format_result(result: Any, verbose: bool = False) -> None:
    """
    Format and display execution result.

    Args:
        result: Execution result
        verbose: Enable verbose output
    """
    if verbose:
        click.echo("\n" + "=" * 70)
        click.echo("Execution Result:")
        click.echo("=" * 70)

    _print_result(result)

    if verbose:
        click.echo("=" * 70)


def _print_result(result: Any, indent: int = 0) -> None:
    """
    Recursively print result structure.

    Args:
        result: Result to print
        indent: Indentation level
    """
    prefix = " " * indent

    if isinstance(result, tuple):
        click.echo(f"{prefix}Parallel Results:")
        for i, item in enumerate(result):
            click.echo(f"{prefix}  [{i}]:")
            _print_result(item, indent + 4)
    elif isinstance(result, dict):
        for key, value in result.items():
            if isinstance(value, (dict, list, tuple)):
                click.echo(f"{prefix}{key}:")
                _print_result(value, indent + 2)
            else:
                click.echo(f"{prefix}{key}: {value}")
    elif isinstance(result, list):
        for i, item in enumerate(result):
            click.echo(f"{prefix}[{i}]: {item}")
    else:
        click.echo(f"{prefix}{result}")


@click.command(name='run-dsl')
@click.argument('file', type=click.Path(exists=True))
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def run_dsl_command(file: str, verbose: bool):
    """
    Run a Category Theory DSL program from a .ct file.

    Example:
        python -m src.main run-dsl examples/workflows/ci_pipeline.ct
        python -m src.main run-dsl examples/workflows/ci_pipeline.ct --verbose
    """
    try:
        # Read DSL file
        dsl_text = read_dsl_file(file)

        # Execute DSL program
        result = asyncio.run(execute_dsl_program(dsl_text, verbose=verbose))

        # Format and display result
        format_result(result, verbose=verbose)

        click.echo("\n✅ DSL program executed successfully")

    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Execution failed: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        raise click.Abort()


if __name__ == "__main__":
    run_dsl_command()
