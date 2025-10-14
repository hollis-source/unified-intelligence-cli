"""Lifecycle-aware DSL workflow executor.

Integrates DSL execution with Plan → Verify → Decompose → Execute lifecycle
from unified architecture baseline.

Clean Architecture: Use Case layer (orchestrates entities).
SOLID: SRP - handles DSL workflow execution with lifecycle phases.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from src.entity.lifecycle import Lifecycle, LifecycleState
from src.dsl.adapters.parser import Parser
from src.dsl.use_cases.interpreter import Interpreter, TaskExecutor
from src.dsl.adapters.cli_task_executor import CLITaskExecutor


@dataclass
class ValidationResult:
    """Result of workflow validation."""

    is_valid: bool
    issues: List[str]
    checks: List[str]


@dataclass
class WorkflowExecutionResult:
    """Complete workflow execution result with lifecycle information."""

    success: bool
    result: Any
    lifecycle: Lifecycle
    execution_time: float
    phases_completed: List[str]
    error: Optional[str] = None


class LifecycleWorkflowExecutor:
    """Executes DSL workflows through lifecycle phases.

    Coordinates DSL parsing, validation, decomposition, and execution
    through the Plan → Verify → Decompose → Execute lifecycle.

    Phases:
        1. PLAN: Parse DSL file into AST
        2. VERIFY: Validate workflow structure and dependencies
        3. DECOMPOSE: Break into executable tasks
        4. EXECUTE: Run tasks with monitoring

    Example:
        executor = LifecycleWorkflowExecutor(task_executor)
        result = await executor.execute_workflow("workflow.ct", verbose=True)
    """

    def __init__(
        self,
        task_executor: Optional[TaskExecutor] = None,
        parser: Optional[Parser] = None
    ):
        """Initialize lifecycle executor.

        Args:
            task_executor: Task executor implementation (defaults to CLITaskExecutor)
            parser: DSL parser (defaults to Parser())
        """
        self.task_executor = task_executor or CLITaskExecutor()
        self.parser = parser or Parser()

    async def execute_workflow(
        self,
        workflow_file: str,
        verbose: bool = False
    ) -> WorkflowExecutionResult:
        """Execute DSL workflow file through full lifecycle.

        Args:
            workflow_file: Path to .ct workflow file
            verbose: Enable verbose output

        Returns:
            WorkflowExecutionResult with execution details

        Raises:
            FileNotFoundError: If workflow file doesn't exist
            ValueError: If workflow validation fails
        """
        import time
        start_time = time.time()

        lifecycle = Lifecycle()
        phases_completed = []

        try:
            # PHASE 1: PLAN - Parse DSL file
            dsl_text = self._read_workflow_file(workflow_file)
            ast = self._parse_workflow(dsl_text)
            symbol_table = self._extract_symbol_table(ast)

            lifecycle.plan(plan_data={
                "file": workflow_file,
                "ast": ast,
                "symbol_table": symbol_table
            })
            phases_completed.append("PLAN")

            if verbose:
                self._print_phase("PLAN", f"Parsed workflow from {workflow_file}")
                if symbol_table:
                    self._print_detail(f"Defined functors: {list(symbol_table.keys())}")

            # PHASE 2: VERIFY - Validate workflow
            validation = self._validate_workflow(ast, symbol_table)

            if not validation.is_valid:
                # Transition to VERIFY with failure
                lifecycle.verify(
                    verification_result=False,
                    checks=validation.checks,
                    issues=validation.issues
                )
                phases_completed.append("VERIFY")

                lifecycle.fail(error="Validation failed", issues=validation.issues)
                execution_time = time.time() - start_time

                return WorkflowExecutionResult(
                    success=False,
                    result=None,
                    lifecycle=lifecycle,
                    execution_time=execution_time,
                    phases_completed=phases_completed,
                    error=f"Validation failed: {', '.join(validation.issues)}"
                )

            lifecycle.verify(
                verification_result=True,
                checks=validation.checks,
                issues=validation.issues
            )

            phases_completed.append("VERIFY")

            if verbose:
                self._print_phase("VERIFY", f"Passed {len(validation.checks)} validation checks")
                for check in validation.checks:
                    self._print_detail(f"✓ {check}")

            # PHASE 3: DECOMPOSE - Extract executable tasks
            main_node = self._get_main_node(ast)
            task_count = self._count_tasks(main_node)

            lifecycle.decompose(decomposed_units={
                "main_node": main_node,
                "task_count": task_count
            })
            phases_completed.append("DECOMPOSE")

            if verbose:
                self._print_phase("DECOMPOSE", f"{task_count} executable tasks identified")

            # PHASE 4: EXECUTE - Run workflow
            lifecycle.execute(execution_data={"status": "running"})

            interpreter = Interpreter(self.task_executor)
            interpreter.set_symbol_table(symbol_table)

            result = await interpreter.execute(main_node)

            lifecycle.complete(result=result)
            phases_completed.append("EXECUTE")
            phases_completed.append("COMPLETE")

            execution_time = time.time() - start_time

            if verbose:
                self._print_phase("EXECUTE", "Workflow completed successfully")
                self._print_detail(f"Total execution time: {execution_time:.2f}s")

            return WorkflowExecutionResult(
                success=True,
                result=result,
                lifecycle=lifecycle,
                execution_time=execution_time,
                phases_completed=phases_completed
            )

        except Exception as e:
            lifecycle.fail(error=str(e))
            execution_time = time.time() - start_time

            if verbose:
                self._print_phase("FAILED", str(e), success=False)

            return WorkflowExecutionResult(
                success=False,
                result=None,
                lifecycle=lifecycle,
                execution_time=execution_time,
                phases_completed=phases_completed,
                error=str(e)
            )

    def _read_workflow_file(self, file_path: str) -> str:
        """Read workflow file contents.

        Args:
            file_path: Path to .ct file

        Returns:
            File contents

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {file_path}")

        if path.suffix != ".ct":
            # Warning but continue
            import click
            click.echo(f"Warning: Expected .ct extension, got {path.suffix}", err=True)

        return path.read_text()

    def _parse_workflow(self, dsl_text: str):
        """Parse DSL text to AST.

        Args:
            dsl_text: DSL program text

        Returns:
            Parsed AST

        Raises:
            Exception: If parsing fails
        """
        return self.parser.parse(dsl_text)

    def _extract_symbol_table(self, ast) -> Dict[str, Any]:
        """Extract functor definitions from AST.

        Args:
            ast: Parsed AST

        Returns:
            Symbol table mapping functor names to expressions
        """
        symbol_table = {}

        if isinstance(ast, list):
            for node in ast:
                if hasattr(node, 'name') and hasattr(node, 'expression'):
                    symbol_table[node.name] = node.expression

        return symbol_table

    def _validate_workflow(self, ast, symbol_table: Dict) -> ValidationResult:
        """Validate workflow structure.

        Performs basic validation checks:
        - AST is not empty
        - At least one executable node exists
        - Symbol table references are resolvable

        Args:
            ast: Parsed AST
            symbol_table: Functor definitions

        Returns:
            ValidationResult with issues and checks
        """
        issues = []
        checks = []

        # Check 1: AST is not empty
        if ast is None:
            issues.append("Empty workflow (no AST)")
        elif isinstance(ast, list) and len(ast) == 0:
            issues.append("Empty workflow (no nodes)")
        else:
            checks.append("Non-empty workflow")

        # Check 2: At least one executable node
        main_node = self._get_main_node(ast)
        if main_node is None:
            issues.append("No executable node found")
        else:
            checks.append("Executable node found")

        # Check 3: All functor references are defined
        # (This would require AST traversal - simplified for now)
        if symbol_table:
            checks.append(f"{len(symbol_table)} functors defined")

        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            checks=checks
        )

    def _get_main_node(self, ast):
        """Extract main executable node from AST.

        Args:
            ast: Parsed AST

        Returns:
            Main node to execute, or None if not found
        """
        if isinstance(ast, list):
            # Find last functor or last node
            functors = [node for node in ast if hasattr(node, 'name')]
            if functors:
                return functors[-1]  # Last functor is main
            elif ast:
                return ast[-1]  # Last node
            else:
                return None
        else:
            return ast

    def _count_tasks(self, node) -> int:
        """Count tasks in AST node (simplified).

        Args:
            node: AST node

        Returns:
            Estimated task count
        """
        if node is None:
            return 0

        # Simplified counting - just count nodes
        # In reality, would traverse composition/product trees
        if hasattr(node, 'expression'):
            return self._count_tasks(node.expression)
        elif hasattr(node, 'left') and hasattr(node, 'right'):
            return self._count_tasks(node.left) + self._count_tasks(node.right)
        else:
            return 1  # Primitive task

    def _print_phase(self, phase: str, message: str, success: bool = True):
        """Print phase header.

        Args:
            phase: Phase name
            message: Phase message
            success: Whether phase succeeded
        """
        import click

        symbol = "✓" if success else "✗"
        color = "green" if success else "red"

        click.echo(click.style(f"{symbol} {phase}: {message}", fg=color, bold=True))

    def _print_detail(self, message: str):
        """Print detail message.

        Args:
            message: Detail message
        """
        import click
        click.echo(f"  {message}")
