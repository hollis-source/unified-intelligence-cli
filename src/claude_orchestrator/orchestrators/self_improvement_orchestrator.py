"""SelfImprovementOrchestrator - Autonomous improvement loop.

Implements the full Analyze → Generate → Execute → Measure cycle.
Generates its own improvement tasks from context analysis.

Clean Architecture: Orchestrator layer
SOLID: SRP - Single responsibility for self-improvement orchestration
"""
from __future__ import annotations

import logging
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from src.claude_orchestrator.interfaces.worker_pool import IWorkerPool
from src.claude_orchestrator.entities.generated_task import GeneratedTask

logger = logging.getLogger(__name__)


class SelfImprovementOrchestrator:
    """
    Autonomous self-improvement orchestrator.
    
    Full cycle:
    1. Analyze context (git, coverage, metrics, health)
    2. Generate improvement tasks (LLM-driven)
    3. Prioritize and validate tasks
    4. Execute top tasks
    5. Measure results and update health score
    6. Repeat
    
    Usage:
        orchestrator = SelfImprovementOrchestrator(
            worker_pool=pool,
            llm_provider=qwen,
            project_path=".",
        )
        orchestrator.run_cycle()
    """
    
    def __init__(
        self,
        worker_pool: IWorkerPool,
        llm_provider: Optional[Any] = None,
        project_path: str = ".",
        coverage_file: str = "coverage.xml",
        db_store: Optional[Any] = None,
    ):
        """
        Initialize self-improvement orchestrator.
        
        Args:
            worker_pool: Worker pool for task execution
            llm_provider: LLM provider for task generation
            project_path: Path to project root
            coverage_file: Path to coverage report
            db_store: Database store for metrics
        """
        self.pool = worker_pool
        self.llm_provider = llm_provider
        self.project_path = project_path
        self.coverage_file = coverage_file
        self.db_store = db_store
        
        # Statistics
        self.cycle_count = 0
        self.tasks_generated = 0
        self.tasks_executed = 0
        self.tasks_succeeded = 0
        self.tasks_failed = 0
        self.health_history: List[float] = []
    
    async def run_cycle(
        self,
        max_tasks: int = 5,
        analysis_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Run one self-improvement cycle.
        
        Args:
            max_tasks: Maximum tasks to execute per cycle
            analysis_days: Days of history to analyze
            
        Returns:
            Cycle results dictionary
        """
        self.cycle_count += 1
        
        logger.info(f"\n{'='*70}")
        logger.info(f"SELF-IMPROVEMENT CYCLE #{self.cycle_count}")
        logger.info(f"{'='*70}\n")
        
        # Step 1: Analyze context
        logger.info("[Cycle] Step 1/5: Analyzing context...")
        system_context = await self._analyze_context(analysis_days)
        
        if system_context:
            logger.info(f"[Cycle] Health Score: {system_context.health_score.overall_score:.1f}/100 (Grade: {system_context.health_score.grade})")
            self.health_history.append(system_context.health_score.overall_score)
        
        # Step 2: Generate tasks
        logger.info("\n[Cycle] Step 2/5: Generating improvement tasks...")
        tasks = await self._generate_tasks(system_context, max_tasks * 2)  # Generate 2x, filter to top-K
        
        logger.info(f"[Cycle] Generated {len(tasks)} tasks")
        self.tasks_generated += len(tasks)
        
        # Step 3: Prioritize and validate
        logger.info("\n[Cycle] Step 3/5: Prioritizing and validating tasks...")
        validated_tasks = self._validate_tasks(tasks)
        ranked_tasks = self._prioritize_tasks(validated_tasks, system_context)
        
        top_tasks = ranked_tasks[:max_tasks]
        logger.info(f"[Cycle] Selected top {len(top_tasks)} tasks for execution")
        
        # Step 4: Execute tasks
        logger.info("\n[Cycle] Step 4/5: Executing tasks...")
        results = await self._execute_tasks(top_tasks)
        
        # Step 5: Measure and feedback
        logger.info("\n[Cycle] Step 5/5: Measuring results...")
        metrics = await self._measure_results(results, system_context)
        
        # Build cycle summary
        summary = {
            "cycle": self.cycle_count,
            "timestamp": datetime.utcnow().isoformat(),
            "health_score": system_context.health_score.overall_score if system_context else 0.0,
            "tasks_generated": len(tasks),
            "tasks_executed": len(results),
            "tasks_succeeded": sum(1 for r in results if r.get("success")),
            "tasks_failed": sum(1 for r in results if not r.get("success")),
            "metrics": metrics,
        }
        
        logger.info(f"\n[Cycle] Cycle #{self.cycle_count} complete")
        logger.info(f"[Cycle] Success rate: {summary['tasks_succeeded']}/{summary['tasks_executed']}")
        
        return summary
    
    async def _analyze_context(self, days: int) -> Optional[Any]:
        """Analyze context using ContextAggregator."""
        try:
            from src.analysis.context_aggregator import ContextAggregator
            
            aggregator = ContextAggregator(
                repo_path=self.project_path,
                coverage_file=self.coverage_file,
                db_store=self.db_store,
            )
            
            system_context = await aggregator.aggregate(analysis_days=days, test_pass_rate=1.0)
            return system_context
            
        except Exception as e:
            logger.error(f"Context analysis failed: {e}")
            return None
    
    async def _generate_tasks(
        self,
        system_context: Optional[Any],
        count: int,
    ) -> List[GeneratedTask]:
        """Generate tasks using LLM or heuristic fallback."""
        try:
            from src.claude_orchestrator.entities.task_context import TaskContext

            # Build minimal TaskContext
            # Derive modified_files from high-churn files to diversify tasks
            modified_files = []
            try:
                if system_context and system_context.git_analysis and system_context.git_analysis.high_churn_files:
                    modified_files = [f.file_path for f in system_context.git_analysis.high_churn_files[:10]]
            except Exception:
                modified_files = []

            context = TaskContext.create(
                snapshot_time=datetime.now(),
                recent_commits=[],
                modified_files=modified_files,
                current_branch="main",
                test_pass_rate=1.0,
                coverage_percentage=system_context.coverage_analysis.overall_coverage * 100 if system_context and system_context.coverage_analysis else 0.0,
            )

            # Try LLM generation first
            if self.llm_provider:
                try:
                    from src.claude_orchestrator.adapters.llm_task_generator import generate_batch_tasks

                    tasks = generate_batch_tasks(
                        llm_provider=self.llm_provider,
                        context=context,
                        system_context=system_context,
                        count=count,
                    )

                    if tasks:
                        return tasks
                except Exception as e:
                    logger.warning(f"LLM task generation failed, falling back to heuristic: {e}")

            # Fallback to heuristic generation
            from src.claude_orchestrator.adapters.heuristic_task_generator import HeuristicTaskGenerator

            generator = HeuristicTaskGenerator()
            tasks = []

            for i in range(count):
                try:
                    task = generator.generate_task(context, goal=None)
                    tasks.append(task)
                except Exception as e:
                    logger.error(f"Heuristic task generation failed: {e}")

            return tasks

        except Exception as e:
            logger.error(f"Task generation failed: {e}")
            return []
    
    def _validate_tasks(self, tasks: List[GeneratedTask]) -> List[GeneratedTask]:
        """Validate and filter tasks."""
        try:
            from src.claude_orchestrator.use_cases.task_validator import TaskValidator
            
            validator = TaskValidator()
            validated = validator.filter_and_deduplicate(tasks)
            
            return validated
            
        except Exception as e:
            logger.error(f"Task validation failed: {e}")
            return tasks
    
    def _prioritize_tasks(
        self,
        tasks: List[GeneratedTask],
        system_context: Optional[Any],
    ) -> List[GeneratedTask]:
        """Prioritize tasks by score."""
        try:
            from src.claude_orchestrator.use_cases.task_prioritizer import TaskPrioritizer
            
            prioritizer = TaskPrioritizer()
            scored = prioritizer.rank_tasks(tasks, system_context=system_context)
            
            # Return tasks in priority order
            return [s.task for s in scored]
            
        except Exception as e:
            logger.error(f"Task prioritization failed: {e}")
            return tasks
    
    async def _execute_tasks(self, tasks: List[GeneratedTask]) -> List[Dict[str, Any]]:
        """Execute tasks using worker pool."""
        results = []

        for task in tasks:
            logger.info(f"[Execute] Starting task: {task.id}")

            try:
                # Assign to worker pool
                worker = self.pool.assign_task(task)

                # Wait for completion
                output = self.pool.wait_for_completion(
                    worker.id,
                    timeout_minutes=task.estimated_minutes,
                )

                success = output.status.value == "completed"

                results.append({
                    "task_id": task.id,
                    "success": success,
                    "output": output.output,
                    "error": output.error,
                })

                if success:
                    self.tasks_succeeded += 1
                    logger.info(f"[Execute] Task {task.id} succeeded")
                else:
                    self.tasks_failed += 1
                    logger.error(f"[Execute] Task {task.id} failed: {output.error}")

                self.tasks_executed += 1

            except Exception as e:
                logger.error(f"[Execute] Task {task.id} execution error: {e}")
                results.append({
                    "task_id": task.id,
                    "success": False,
                    "error": str(e),
                })
                self.tasks_failed += 1
                self.tasks_executed += 1

        return results
    
    async def _measure_results(
        self,
        results: List[Dict[str, Any]],
        system_context: Optional[Any],
    ) -> Dict[str, Any]:
        """Measure impact of executed tasks."""
        # Re-analyze to get updated health score
        try:
            updated_context = await self._analyze_context(days=7)
            
            if updated_context and system_context:
                old_score = system_context.health_score.overall_score
                new_score = updated_context.health_score.overall_score
                delta = new_score - old_score
                
                return {
                    "old_health_score": old_score,
                    "new_health_score": new_score,
                    "health_delta": delta,
                    "improvement": delta > 0,
                }
            
        except Exception as e:
            logger.error(f"Results measurement failed: {e}")
        
        return {}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        success_rate = self.tasks_succeeded / max(1, self.tasks_executed)
        
        health_trend = "stable"
        if len(self.health_history) >= 2:
            if self.health_history[-1] > self.health_history[-2]:
                health_trend = "improving"
            elif self.health_history[-1] < self.health_history[-2]:
                health_trend = "degrading"
        
        return {
            "cycles_completed": self.cycle_count,
            "tasks_generated": self.tasks_generated,
            "tasks_executed": self.tasks_executed,
            "tasks_succeeded": self.tasks_succeeded,
            "tasks_failed": self.tasks_failed,
            "success_rate": success_rate,
            "health_history": self.health_history,
            "health_trend": health_trend,
            "current_health": self.health_history[-1] if self.health_history else 0.0,
        }

