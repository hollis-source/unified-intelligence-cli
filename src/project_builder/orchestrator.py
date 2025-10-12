"""Project orchestrator for managing project execution lifecycle.

Coordinates all components of the Agentic Project Builder following the
Meta-Operational Lifecycle: Plan → Verify → Decompose → Execute.
"""

import time
import asyncio
import re

from typing import List, Optional

from src.interfaces import (
    IProjectOrchestrator,
    IGoalDecomposer,
    IHTNDSLTranslator,
    IStateManager,
    IExecutionCoordinator,
    IFeedbackHandler,
    ProjectResult,
    ExecutionResult,
    TaskStatus
)
from src.core.entities.file_ref import FileRef
from src.dsl.entities.literal import Literal


class ProjectOrchestrator(IProjectOrchestrator):
    """Orchestrator for project execution lifecycle.

    Coordinates goal decomposition, HTN-DSL translation, state management,
    task execution, and feedback loops following Clean Architecture principles.

    Phase 1: Basic sequential execution with HTN and DSL
    Phase 2: Integrated execution coordinator and feedback loops
    Phase 3: Production-ready with full agent teams integration

    Attributes:
        goal_decomposer: Converts goals to HTN graphs
        htn_dsl_translator: Converts HTN to DSL workflows
        state_manager: Manages project state
        execution_coordinator: Routes tasks to agents (optional)
        feedback_handler: Handles failures and replanning (optional)
        max_retries: Maximum retry attempts on failure
    """

    def __init__(
        self,
        goal_decomposer: IGoalDecomposer,
        htn_dsl_translator: IHTNDSLTranslator,
        state_manager: IStateManager,
        execution_coordinator: Optional[IExecutionCoordinator] = None,
        feedback_handler: Optional[IFeedbackHandler] = None,
        max_retries: int = 3
    ):
        """Initialize orchestrator with required components.

        Args:
            goal_decomposer: Goal decomposition component
            htn_dsl_translator: HTN to DSL translator
            state_manager: State management component
            execution_coordinator: Execution coordinator (optional, uses mock if None)
            feedback_handler: Feedback loop handler (optional)
            max_retries: Maximum retry attempts on failure
        """
        self.goal_decomposer = goal_decomposer
        self.htn_dsl_translator = htn_dsl_translator
        self.state_manager = state_manager
        self.execution_coordinator = execution_coordinator
        self.feedback_handler = feedback_handler
        self.max_retries = max_retries

    async def execute_project(self, goal: str, project_id: str) -> ProjectResult:
        """Execute a project from natural language goal to completion.

        Implements Meta-Operational Lifecycle:
        1. Plan: Decompose goal into HTN
        2. Verify: Validate initial state
        3. Decompose: Translate HTN to DSL
        4. Execute: Execute tasks sequentially

        Args:
            goal: Natural language description of project goal
            project_id: Unique identifier for the project

        Returns:
            Final project result with artifacts

        Example:
            goal: "Create a REST API with user authentication"
            project_id: "rest-api-20251006"
            returns: ProjectResult with API artifacts
        """
        start_time = time.time()
        task_results: List[ExecutionResult] = []

        try:
            # PHASE 1: PLAN - Decompose goal into HTN
            print(f"[PLAN] Decomposing goal: {goal}")
            htn_graph = await self.goal_decomposer.decompose_goal(goal)
            print(f"[PLAN] Generated HTN with depth {htn_graph.get_depth()}")

            # Initialize state
            state = self.state_manager.initialize(project_id, htn_graph)

            # Seed world_state with file paths mentioned in the goal so HTN preconditions like
            # {'file_path': '/opt/...'} can be satisfied at start.
            paths = re.findall(r'(/[-\w/\.]+)', goal)
            if paths:
                # Primary path used by tasks expecting a single 'file_path'
                state.world_state['file_path'] = paths[0]
                # Preserve all discovered paths for downstream components
                state.world_state['file_paths'] = paths
                # Optional: also expose typed FileRef URIs for resource resolution
                try:
                    file_ref_uris = []
                    for p in paths:
                        uri = f"file://{p}"
                        ref = FileRef.parse(uri)
                        file_ref_uris.append(ref.to_uri())
                    if file_ref_uris:
                        state.world_state['file_refs'] = file_ref_uris
                except Exception:
                    # Best-effort; don't block initialization if parsing fails
                    pass


            # PHASE 2: VERIFY - Validate initial state
            print("[VERIFY] Validating initial state")
            if not self.state_manager.validate_current_state():
                raise ValueError("Initial state validation failed")

            # PHASE 3: DECOMPOSE - Translate HTN to DSL
            print("[DECOMPOSE] Translating HTN to DSL workflow")
            dsl_workflow = self.htn_dsl_translator.translate(htn_graph)
            print(f"[DECOMPOSE] Generated DSL: {dsl_workflow}")

            # PHASE 4: EXECUTE - Execute tasks with feedback loop
            print("[EXECUTE] Executing tasks")
            task_results = await self._execute_with_feedback(dsl_workflow, state)

            # Finalize artifacts
            artifacts = self.state_manager.finalize_artifacts()

            # Calculate total time and cost
            execution_time = time.time() - start_time

            # Calculate actual cost from task results
            estimated_cost = sum(
                result.metadata.get("cost", 0.001)
                for result in task_results
            )

            # Check if all tasks succeeded
            success = all(result.success for result in task_results)

            return ProjectResult(
                project_id=project_id,
                success=success,
                artifacts=artifacts,
                execution_time=execution_time,
                cost=estimated_cost,
                task_results=task_results,
                error="" if success else "Some tasks failed"
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ProjectResult(
                project_id=project_id,
                success=False,
                artifacts={},
                execution_time=execution_time,
                cost=0.0,
                task_results=task_results,
                error=str(e)
            )

    async def resume_project(self, project_id: str) -> ProjectResult:
        """Resume a previously started project.

        Args:
            project_id: ID of project to resume

        Returns:
            Final project result with artifacts
        """
        start_time = time.time()

        try:
            # Load existing state
            state = self.state_manager.load_state(project_id)

            print(f"[RESUME] Loaded project state (version {state.version})")

            # Re-translate HTN to DSL (in case of changes)
            dsl_workflow = self.htn_dsl_translator.translate(state.htn_graph)

            # Continue execution from current state
            task_results = await self._execute_with_feedback(dsl_workflow, state)

            # Finalize artifacts
            artifacts = self.state_manager.finalize_artifacts()

            # Calculate metrics
            execution_time = time.time() - start_time
            estimated_cost = sum(
                result.metadata.get("cost", 0.001)
                for result in task_results
            )
            success = all(result.success for result in task_results)

            return ProjectResult(
                project_id=project_id,
                success=success,
                artifacts=artifacts,
                execution_time=execution_time,
                cost=estimated_cost,
                task_results=task_results,
                error="" if success else "Some tasks failed"
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ProjectResult(
                project_id=project_id,
                success=False,
                artifacts={},
                execution_time=execution_time,
                cost=0.0,
                task_results=[],
                error=f"Resume failed: {e}"
            )

    async def _execute_with_feedback(
        self,
        dsl_workflow,
        state
    ) -> List[ExecutionResult]:
        """Execute DSL workflow with feedback loop for retry on failure.

        Phase 2: Integrated execution coordinator and feedback handler
        Phase 3: Production-ready with full agent teams

        Args:
            dsl_workflow: DSL workflow to execute
            state: Current project state

        Returns:
            List of execution results for all tasks
        """
        all_results: List[ExecutionResult] = []
        retry_count = 0

        while retry_count <= self.max_retries:
            # Execute workflow
            if self.execution_coordinator:
                # Phase 2+: Use ExecutionCoordinator
                results = await self.execution_coordinator.execute_workflows(
                    dsl_workflow,
                    state
                )
            else:
                # Phase 1: Fallback to mock execution
                results = await self._execute_tasks_mock(state.htn_graph, state)

            # Update state based on results
            for result in results:
                if result.success:
                    self.state_manager.apply_effects(result.effects)
                    self.state_manager.mark_task_status(result.task_id, TaskStatus.COMPLETED)
                else:
                    self.state_manager.mark_task_status(result.task_id, TaskStatus.FAILED)

            all_results.extend(results)

            # Check for failures
            failed_tasks = [r for r in results if not r.success]

            if not failed_tasks:
                # All tasks succeeded
                break

            if not self.feedback_handler or retry_count >= self.max_retries:
                # No feedback handler or max retries reached
                print(f"[FEEDBACK] Max retries ({self.max_retries}) reached, giving up")
                break

            # Replan using feedback handler
            print(f"[FEEDBACK] {len(failed_tasks)} tasks failed, replanning (attempt {retry_count + 1}/{self.max_retries})")

            try:
                new_state = self.feedback_handler.replan(
                    self.state_manager.get_current_state(),
                    failed_tasks
                )
                # Update state manager with new state
                self.state_manager.current_state = new_state
                print(f"[FEEDBACK] Replanning successful, retrying failed tasks")
                retry_count += 1
            except Exception as e:
                print(f"[FEEDBACK] Replanning failed: {e}")
                break

        return all_results

    async def _execute_tasks_mock(
        self,
        htn_graph,
        state
    ) -> List[ExecutionResult]:
        """Execute all tasks with mock implementation (Phase 1 fallback).

        Args:
            htn_graph: HTN task graph to execute
            state: Current project state

        Returns:
            List of execution results for each task
        """
        results: List[ExecutionResult] = []

        # Get primitive tasks (leaf nodes) in execution order
        primitive_tasks = self._get_primitive_tasks(htn_graph)

        for task in primitive_tasks:
            print(f"  Executing task: {task.task_id} - {task.description}")

            # Mark task as in progress
            self.state_manager.mark_task_status(task.task_id, TaskStatus.IN_PROGRESS)

            # Mock execution
            await asyncio.sleep(0.1)  # Simulate work

            # Create execution result
            result = ExecutionResult(
                task_id=task.task_id,
                success=True,
                effects=task.effects,
                error="",
                metadata={"mock": True, "description": task.description, "cost": 0.001}
            )

            results.append(result)

        return results

    def _get_primitive_tasks(self, node, results=None):
        """Recursively collect all primitive (leaf) tasks from HTN graph.

        Args:
            node: HTN node to start from
            results: Accumulated list of primitive tasks

        Returns:
            List of primitive HTNNode instances
        """
        if results is None:
            results = []

        if node.is_primitive():
            results.append(node)
        else:
            for subtask in node.subtasks:
                self._get_primitive_tasks(subtask, results)

        return results
