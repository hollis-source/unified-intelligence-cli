"""
User Simulation Agent - Simulates real user behavior for testing.

This agent mimics actual user workflows to:
1. Find bugs and failure modes
2. Collect performance data
3. Identify UX issues
4. Validate system behavior under realistic conditions

TDD at system level: Test first, then build fixes based on evidence.
"""

import asyncio
import time
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from src.entities import Task, Agent, ExecutionResult, ExecutionStatus
from src.composition import create_coordinator


@dataclass
class UserAction:
    """Represents a single user action."""
    action_type: str  # "submit_task", "check_status", "read_result", "cancel_task"
    task_description: str
    expected_outcome: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SimulationResult:
    """Results from user simulation."""
    scenario_name: str
    actions_performed: int
    successes: int
    failures: int
    errors: List[Dict[str, Any]]
    warnings: List[str]
    performance_data: Dict[str, Any]
    duration_seconds: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


class UserSimulationAgent:
    """
    Simulates real user behavior for system testing.

    Follows TDD principle at system level:
    - Run realistic user workflows
    - Collect data on failures
    - Document actual bugs
    - Inform next development priorities
    """

    def __init__(self, provider: str = "mock", verbose: bool = True):
        """
        Initialize user simulation agent.

        Args:
            provider: LLM provider to use (mock for testing, grok for real)
            verbose: Print detailed output during simulation
        """
        self.provider = provider
        self.verbose = verbose
        self.results: List[SimulationResult] = []

    def log(self, message: str, level: str = "INFO"):
        """Log simulation activity."""
        if self.verbose:
            timestamp = datetime.utcnow().isoformat()
            print(f"[{timestamp}] [{level}] {message}")

    async def simulate_scenario(
        self,
        scenario_name: str,
        actions: List[UserAction]
    ) -> SimulationResult:
        """
        Simulate a user scenario.

        Args:
            scenario_name: Name of the scenario being tested
            actions: List of user actions to perform

        Returns:
            SimulationResult with data collected
        """
        self.log(f"Starting scenario: {scenario_name}", "SCENARIO")
        start_time = time.time()

        successes = 0
        failures = 0
        errors = []
        warnings = []
        performance_data = {}

        try:
            # Get coordinator via composition
            coordinator = create_coordinator(provider_type=self.provider, verbose=self.verbose)

            # Perform each user action
            for i, action in enumerate(actions, 1):
                self.log(f"Action {i}/{len(actions)}: {action.action_type}", "ACTION")

                try:
                    if action.action_type == "submit_task":
                        result = await self._submit_task(
                            coordinator,
                            action.task_description,
                            action.expected_outcome
                        )

                        if result["success"]:
                            successes += 1
                        else:
                            failures += 1
                            errors.append({
                                "action": action.action_type,
                                "task": action.task_description,
                                "error": result.get("error", "Unknown error")
                            })

                    elif action.action_type == "multi_task_workflow":
                        result = await self._multi_task_workflow(
                            coordinator,
                            action.task_description
                        )

                        if result["success"]:
                            successes += 1
                            performance_data["multi_task_duration"] = result["duration"]
                        else:
                            failures += 1
                            errors.append({
                                "action": action.action_type,
                                "error": result.get("error", "Unknown error")
                            })

                    elif action.action_type == "stress_test":
                        result = await self._stress_test(coordinator)
                        performance_data["stress_test"] = result

                        if result["success"]:
                            successes += 1
                        else:
                            failures += 1
                            warnings.append(f"Stress test revealed issues: {result.get('issues', [])}")

                except Exception as e:
                    self.log(f"ERROR in action {i}: {e}", "ERROR")
                    failures += 1
                    errors.append({
                        "action": action.action_type,
                        "exception": str(e),
                        "type": type(e).__name__
                    })

        except Exception as e:
            self.log(f"FATAL ERROR in scenario: {e}", "FATAL")
            errors.append({
                "fatal": True,
                "exception": str(e),
                "type": type(e).__name__
            })

        duration = time.time() - start_time

        result = SimulationResult(
            scenario_name=scenario_name,
            actions_performed=len(actions),
            successes=successes,
            failures=failures,
            errors=errors,
            warnings=warnings,
            performance_data=performance_data,
            duration_seconds=duration
        )

        self.results.append(result)
        self.log(f"Scenario complete: {successes} successes, {failures} failures", "RESULT")

        return result

    async def _submit_task(
        self,
        coordinator,
        task_description: str,
        expected_outcome: str
    ) -> Dict[str, Any]:
        """Simulate submitting a single task."""
        try:
            start = time.time()

            task = Task(
                description=task_description,
                task_id=f"user_task_{int(time.time())}",
                priority=5
            )

            result = await coordinator.coordinate_task(task)
            duration = time.time() - start

            success = result.status == ExecutionStatus.SUCCESS

            # Extract error message properly (Week 1: Error Infrastructure fix)
            error_message = None
            if not success:
                if result.error_details:
                    error_message = result.error_details.get("user_message", "Unknown error")
                elif result.errors:
                    error_message = result.errors[0]
                else:
                    error_message = "Unknown error"

            self.log(
                f"Task {'succeeded' if success else 'failed'} in {duration:.2f}s",
                "SUCCESS" if success else "FAILURE"
            )

            if not success and error_message:
                self.log(f"Error: {error_message}", "ERROR")

            return {
                "success": success,
                "duration": duration,
                "result": result,
                "error": error_message if not success else None,
                "error_details": result.error_details if not success else None,
                "met_expectation": (
                    expected_outcome.lower() in str(result.output).lower()
                    if success and result.output
                    else False
                )
            }

        except Exception as e:
            self.log(f"Task submission failed: {e}", "ERROR")
            return {
                "success": False,
                "error": str(e),
                "exception_type": type(e).__name__
            }

    async def _multi_task_workflow(
        self,
        coordinator,
        workflow_description: str
    ) -> Dict[str, Any]:
        """Simulate multi-task coordination workflow."""
        try:
            start = time.time()

            # Create 3-task workflow
            tasks = [
                Task(description=f"{workflow_description} - part 1", task_id=f"task_1", priority=1),
                Task(description=f"{workflow_description} - part 2", task_id=f"task_2", priority=2),
                Task(description=f"{workflow_description} - part 3", task_id=f"task_3", priority=3)
            ]

            results = []
            for task in tasks:
                result = await coordinator.coordinate_task(task)
                results.append(result)

            duration = time.time() - start
            success_count = sum(1 for r in results if r.status == ExecutionStatus.SUCCESS)

            return {
                "success": success_count == len(tasks),
                "duration": duration,
                "tasks_completed": success_count,
                "total_tasks": len(tasks)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _stress_test(self, coordinator, task_count: int = 10) -> Dict[str, Any]:
        """Run stress test with multiple concurrent tasks."""
        try:
            start = time.time()

            tasks = [
                Task(
                    description=f"Stress test task {i}",
                    task_id=f"stress_{i}",
                    priority=i % 5
                )
                for i in range(task_count)
            ]

            # Execute in parallel
            results = await asyncio.gather(
                *[coordinator.coordinate_task(task) for task in tasks],
                return_exceptions=True
            )

            duration = time.time() - start

            success_count = sum(
                1 for r in results
                if isinstance(r, ExecutionResult) and r.status == ExecutionStatus.SUCCESS
            )
            error_count = sum(1 for r in results if isinstance(r, Exception))

            return {
                "success": error_count == 0,
                "duration": duration,
                "tasks_completed": success_count,
                "tasks_failed": len(tasks) - success_count,
                "exceptions": error_count,
                "throughput": len(tasks) / duration if duration > 0 else 0,
                "issues": [str(r) for r in results if isinstance(r, Exception)]
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def generate_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive test report.

        Args:
            output_file: Optional path to save JSON report

        Returns:
            Report dictionary with all findings
        """
        total_actions = sum(r.actions_performed for r in self.results)
        total_successes = sum(r.successes for r in self.results)
        total_failures = sum(r.failures for r in self.results)
        total_errors = sum(len(r.errors) for r in self.results)

        report = {
            "summary": {
                "scenarios_run": len(self.results),
                "total_actions": total_actions,
                "total_successes": total_successes,
                "total_failures": total_failures,
                "success_rate": total_successes / total_actions if total_actions > 0 else 0,
                "total_errors": total_errors
            },
            "scenarios": [
                {
                    "name": r.scenario_name,
                    "actions": r.actions_performed,
                    "successes": r.successes,
                    "failures": r.failures,
                    "duration": r.duration_seconds,
                    "errors": r.errors,
                    "warnings": r.warnings,
                    "performance": r.performance_data
                }
                for r in self.results
            ],
            "critical_issues": [
                error for r in self.results for error in r.errors
            ],
            "performance_summary": {
                "avg_duration": sum(r.duration_seconds for r in self.results) / len(self.results) if self.results else 0,
                "stress_test_data": [
                    r.performance_data.get("stress_test")
                    for r in self.results
                    if "stress_test" in r.performance_data
                ]
            }
        }

        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            self.log(f"Report saved to: {output_file}", "REPORT")

        return report