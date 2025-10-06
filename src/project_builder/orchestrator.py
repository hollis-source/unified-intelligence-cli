"""Project orchestrator for managing project execution lifecycle.

Coordinates all components of the Agentic Project Builder following the
Meta-Operational Lifecycle: Plan → Verify → Decompose → Execute.
"""

import time
import asyncio
from typing import List

from src.interfaces import (
    IProjectOrchestrator,
    IGoalDecomposer,
    IHTNDSLTranslator,
    IStateManager,
    ProjectResult,
    ExecutionResult,
    TaskStatus
)
from src.dsl.entities.literal import Literal


class ProjectOrchestrator(IProjectOrchestrator):
    """Orchestrator for project execution lifecycle.

    Coordinates goal decomposition, HTN-DSL translation, state management,
    and task execution following Clean Architecture principles.

    Phase 1: Basic sequential execution with HTN and DSL
    Phase 2: Will add full execution coordinator and feedback loops

    Attributes:
        goal_decomposer: Converts goals to HTN graphs
        htn_dsl_translator: Converts HTN to DSL workflows
        state_manager: Manages project state
    """

    def __init__(
        self,
        goal_decomposer: IGoalDecomposer,
        htn_dsl_translator: IHTNDSLTranslator,
        state_manager: IStateManager
    ):
        """Initialize orchestrator with required components.

        Args:
            goal_decomposer: Goal decomposition component
            htn_dsl_translator: HTN to DSL translator
            state_manager: State management component
        """
        self.goal_decomposer = goal_decomposer
        self.htn_dsl_translator = htn_dsl_translator
        self.state_manager = state_manager

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

            # PHASE 2: VERIFY - Validate initial state
            print("[VERIFY] Validating initial state")
            if not self.state_manager.validate_current_state():
                raise ValueError("Initial state validation failed")

            # PHASE 3: DECOMPOSE - Translate HTN to DSL
            print("[DECOMPOSE] Translating HTN to DSL workflow")
            dsl_workflow = self.htn_dsl_translator.translate(htn_graph)
            print(f"[DECOMPOSE] Generated DSL: {dsl_workflow}")

            # PHASE 4: EXECUTE - Execute tasks sequentially
            print("[EXECUTE] Executing tasks")
            task_results = await self._execute_tasks(htn_graph, state)

            # Finalize artifacts
            artifacts = self.state_manager.finalize_artifacts()

            # Calculate total time and cost
            execution_time = time.time() - start_time

            # Phase 1: Placeholder cost calculation
            # Phase 2: Will track actual model usage costs
            estimated_cost = len(task_results) * 0.001  # $0.001 per task placeholder

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
        # Load existing state
        state = self.state_manager.load_state(project_id)

        # Continue execution from current state
        # Phase 1: Simple implementation
        # Phase 2: Will add sophisticated resumption logic

        task_results = await self._execute_tasks(state.htn_graph, state)

        artifacts = self.state_manager.finalize_artifacts()
        success = all(result.success for result in task_results)

        return ProjectResult(
            project_id=project_id,
            success=success,
            artifacts=artifacts,
            execution_time=0.0,  # Not tracked for resume
            cost=0.0,
            task_results=task_results,
            error="" if success else "Some tasks failed"
        )

    async def _execute_tasks(
        self,
        htn_graph,
        state
    ) -> List[ExecutionResult]:
        """Execute all tasks in HTN graph sequentially.

        Phase 1: Simple sequential execution with mock results
        Phase 2: Will integrate with execution coordinator and agent teams

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

            # Phase 1: Mock execution
            # Phase 2: Will call execution coordinator with agent teams
            await asyncio.sleep(0.1)  # Simulate work

            # Create execution result
            result = ExecutionResult(
                task_id=task.task_id,
                success=True,
                effects=task.effects,
                error="",
                metadata={"mock": True, "description": task.description}
            )

            # Apply effects to state
            if result.success:
                self.state_manager.apply_effects(result.effects)
                self.state_manager.mark_task_status(task.task_id, TaskStatus.COMPLETED)
            else:
                self.state_manager.mark_task_status(task.task_id, TaskStatus.FAILED)

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
