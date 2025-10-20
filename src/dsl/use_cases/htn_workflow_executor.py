"""HTN Workflow Executor - Lifecycle executor with HTN decomposition.

Extends LifecycleWorkflowExecutor to add Hierarchical Task Network
decomposition in the DECOMPOSE phase, enabling recursive task breakdown
while preserving all lifecycle functionality.

Clean Architecture: Use Case layer (orchestrates HTN compilation).
SOLID: OCP - extends base executor without modification, LSP - fully substitutable.

Sprint 5 P1-2: Refactored to use IWorkflowEnvironment for HTN compiler dependency.
"""

import asyncio
import time
from typing import Optional
from pathlib import Path

from src.dsl.use_cases.lifecycle_executor import (
    LifecycleWorkflowExecutor,
    WorkflowExecutionResult
)
from src.dsl.use_cases.interpreter import Interpreter
from src.dsl.use_cases.graph_workflow_executor import GraphWorkflowExecutor
from src.dsl.interface.workflow_environment import IWorkflowEnvironment
from src.entity.lifecycle import Lifecycle


class HTNWorkflowExecutor(LifecycleWorkflowExecutor):
    """Lifecycle executor with HTN decomposition capabilities.

    Extends the base LifecycleWorkflowExecutor by compiling the DSL AST
    to a Hierarchical Task Network in the DECOMPOSE phase, enabling
    recursive task breakdown with preconditions and effects.

    All other phases (PLAN, VERIFY, EXECUTE) remain unchanged, ensuring
    backward compatibility with Sprint 1.

    Example:
        executor = HTNWorkflowExecutor()
        result = await executor.execute_workflow("workflow.ct", verbose=True)
        # Output shows HTN decomposition info in DECOMPOSE phase
    """

    def __init__(
        self,
        environment: Optional[IWorkflowEnvironment] = None,
        task_executor=None,
        parser=None
    ):
        """Initialize HTN workflow executor.

        Args:
            environment: Workflow environment providing dependencies (recommended)
            task_executor: DEPRECATED - Task executor implementation (for backward compatibility)
            parser: DEPRECATED - DSL parser (for backward compatibility)

        Recommended Usage:
            env = ConfiguredWorkflowEnvironment(...)
            executor = HTNWorkflowExecutor(environment=env)

        Backward Compatible Usage:
            executor = HTNWorkflowExecutor(task_executor=executor, parser=parser)
        """
        # Sprint 5 P1-2: Pass environment to parent, use it for HTN compiler
        super().__init__(environment=environment, task_executor=task_executor, parser=parser)
        self.htn_compiler = self.environment.get_htn_compiler()
        self.graph_executor = GraphWorkflowExecutor(self.task_executor)

    async def execute_workflow(
        self,
        workflow_file: str,
        verbose: bool = False
    ) -> WorkflowExecutionResult:
        """Execute workflow with HTN-enhanced DECOMPOSE phase.

        Follows same lifecycle as parent but enhances DECOMPOSE to:
        1. Compile AST to HTNNode tree via HTNCompiler
        2. Use HTN.decompose() for recursive breakdown
        3. Track HTN depth and structure

        Args:
            workflow_file: Path to .ct workflow file
            verbose: Enable verbose output with HTN details

        Returns:
            WorkflowExecutionResult with HTN decomposition info

        Backward Compatible: Returns same result structure as parent
        """
        start_time = time.time()
        lifecycle = Lifecycle()
        phases_completed = []

        try:
            # PHASE 1: PLAN - Parse DSL file (unchanged from parent)
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

            # PHASE 2: VERIFY - Validate workflow (unchanged from parent)
            validation = self._validate_workflow(ast, symbol_table)

            if not validation.is_valid:
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

            # PHASE 3: DECOMPOSE - HTN + Graph ENHANCED ✨
            main_node = self._get_main_node(ast)

            # Compile AST to HTNNode tree
            htn_root = self.htn_compiler.compile(main_node)

            # Convert HTN to dependency graph for validation (Sprint 3)
            graph = self.graph_executor.htn_to_graph(htn_root)

            # Validate graph is a DAG (no cycles)
            graph_issues = self.graph_executor.validate_dag(graph)
            if graph_issues:
                lifecycle.fail(error="Graph validation failed", issues=graph_issues)
                phases_completed.append("DECOMPOSE")
                execution_time = time.time() - start_time

                return WorkflowExecutionResult(
                    success=False,
                    result=None,
                    lifecycle=lifecycle,
                    execution_time=execution_time,
                    phases_completed=phases_completed,
                    error=f"Graph validation failed: {', '.join(graph_issues)}"
                )

            # Use HTN decomposition (recursive breakdown)
            htn_decomposed = htn_root.decompose(state={})
            task_count = len(htn_decomposed)

            # Calculate HTN depth for reporting
            htn_depth = self._calculate_htn_depth(htn_root)

            lifecycle.decompose(decomposed_units={
                "main_node": main_node,
                "htn_root": htn_root,
                "htn_decomposed": htn_decomposed,
                "graph": graph,  # NEW: Include graph for execution planning
                "task_count": task_count,
                "htn_depth": htn_depth
            })
            phases_completed.append("DECOMPOSE")

            if verbose:
                self._print_phase("DECOMPOSE",
                    f"HTN: {task_count} tasks, depth={htn_depth}, nodes={self._count_htn_nodes(htn_root)}")
                self._print_detail(f"HTN root: {htn_root.task_id}")
                if htn_root.is_compound():
                    self._print_detail(f"Subtasks: {[t.task_id for t in htn_root.subtasks]}")
                self._print_detail(f"Graph: {len(graph.nodes)} nodes, {graph.edge_count()} edges, DAG validated")

            # PHASE 4: EXECUTE - Run workflow (unchanged from parent)
            lifecycle.execute(execution_data={"status": "running", "htn": True})

            interpreter = Interpreter(self.task_executor)
            interpreter.set_symbol_table(symbol_table)

            result = await interpreter.execute(main_node)

            lifecycle.complete(result=result)
            phases_completed.append("EXECUTE")
            phases_completed.append("COMPLETE")

            execution_time = time.time() - start_time

            if verbose:
                self._print_phase("EXECUTE", "HTN workflow completed successfully")
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

    def _calculate_htn_depth(self, htn_node) -> int:
        """Calculate maximum depth of HTN tree.

        Args:
            htn_node: Root HTNNode

        Returns:
            Maximum depth (1 for leaf nodes)
        """
        if htn_node.is_primitive():
            return 1

        if not htn_node.subtasks:
            return 1

        return 1 + max(self._calculate_htn_depth(subtask) for subtask in htn_node.subtasks)

    def _count_htn_nodes(self, htn_node) -> int:
        """Count total nodes in HTN tree.

        Args:
            htn_node: Root HTNNode

        Returns:
            Total node count
        """
        if htn_node.is_primitive():
            return 1

        return 1 + sum(self._count_htn_nodes(subtask) for subtask in htn_node.subtasks)
