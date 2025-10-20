"""LLMTaskGenerator - LLM-powered task generation.

Generates tasks using LLM prompting with SystemContext (health score, opportunities).
Supports structured output and priority ranking.

Clean Architecture: Adapter layer (implements ITaskGenerator)
SOLID: LSP - substitutable for ITaskGenerator
"""
from __future__ import annotations

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.claude_orchestrator.interfaces.task_generator import (
    ITaskGenerator,
    TaskGenerationError,
)
from src.claude_orchestrator.entities.task_context import TaskContext
from src.claude_orchestrator.entities.generated_task import GeneratedTask
from src.claude_orchestrator.entities.goal import Goal

logger = logging.getLogger(__name__)


class LLMTaskGenerator(ITaskGenerator):
    """
    LLM-powered task generator using SystemContext.
    
    Features:
    - Generates 10+ improvement tasks per week
    - Uses health score and ranked opportunities
    - Structured JSON output
    - Priority ranking by impact/effort
    
    Usage:
        generator = LLMTaskGenerator(llm_provider=qwen_provider)
        task = generator.generate_task(context, goal=None, system_context=sys_ctx)
    """
    
    def __init__(
        self,
        llm_provider: Optional[Any] = None,
        model_name: str = "qwen3",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ):
        """
        Initialize LLM task generator.
        
        Args:
            llm_provider: LLM provider adapter (e.g., QwenAgentAdapter)
            model_name: Model to use
            temperature: Sampling temperature
            max_tokens: Max response tokens
        """
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def generate_task(
        self,
        context: TaskContext,
        goal: Optional[Goal] = None,
        max_complexity: str = "medium",
        target_goal_id: Optional[str] = None,
        enable_heuristics: bool = True,
        system_context: Optional[Any] = None,  # SystemContext from context_aggregator
    ) -> GeneratedTask:
        """
        Generate next task using LLM.
        
        Args:
            context: Current codebase context (TaskContext)
            goal: Optional specific goal to target
            max_complexity: Maximum task complexity
            target_goal_id: Optional explicit goal ID
            enable_heuristics: Fallback to heuristics if LLM fails
            system_context: Optional SystemContext with health score and opportunities
            
        Returns:
            GeneratedTask with instruction and rationale
        """
        try:
            # Build prompt
            prompt = self._build_prompt(context, goal, max_complexity, system_context)
            
            # Call LLM
            if self.llm_provider is None:
                raise TaskGenerationError("LLM provider not configured; cannot generate task")
            
            response = self._call_llm(prompt)
            
            # Parse structured output
            task_data = self._parse_response(response)
            
            # Create GeneratedTask
            task = GeneratedTask.create(
                id=task_data.get("id", f"llm-task-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                instruction=task_data.get("instruction", ""),
                rationale=task_data.get("rationale", ""),
                goal_id=task_data.get("goal_id", goal.id if goal else "general"),
                estimated_minutes=task_data.get("estimated_minutes", 60),
                priority=task_data.get("priority", "P2"),
                complexity=task_data.get("complexity", max_complexity),
            )
            
            return task
            
        except Exception as e:
            logger.error(f"LLM task generation failed: {e}")
            raise TaskGenerationError(f"LLM task generation failed: {e}")
    
    def _build_prompt(
        self,
        context: TaskContext,
        goal: Optional[Goal],
        max_complexity: str,
        system_context: Optional[Any],
    ) -> str:
        """Build LLM prompt with context and opportunities."""
        lines = [
            "You are an autonomous software development assistant. Generate the next high-impact task.",
            "",
            "## Current Context",
            f"- Branch: {context.current_branch}",
            f"- Recent commits: {len(context.recent_commits)}",
            f"- Test pass rate: {context.test_pass_rate * 100:.1f}%",
            f"- Coverage: {context.coverage_percentage:.1f}%",
            f"- Active goals: {len(context.active_goals)}",
        ]
        
        if context.test_failures:
            lines.append(f"- **CRITICAL**: {len(context.test_failures)} failing tests")
        
        # Add SystemContext if available
        if system_context:
            lines.extend([
                "",
                "## System Health",
                f"- Health Score: {system_context.health_score.overall_score:.1f}/100 (Grade: {system_context.health_score.grade})",
                "",
                "### Top Improvement Opportunities:",
            ])
            for i, opp in enumerate(system_context.ranked_opportunities[:5], 1):
                lines.append(f"{i}. [{opp.category}] {opp.description}")
                lines.append(f"   Impact: {opp.impact}, Effort: {opp.effort}, Score gain: +{opp.estimated_score_gain:.1f}")
        
        # Add goal if specified
        if goal:
            lines.extend([
                "",
                "## Target Goal",
                f"- ID: {goal.id}",
                f"- Title: {goal.title}",
                f"- Description: {goal.description}",
                f"- Priority: {goal.priority}",
                f"- Progress: {goal.progress_percentage() or 0:.0f}%",
            ])
        
        lines.extend([
            "",
            "## Task Requirements",
            f"- Max complexity: {max_complexity}",
            "- Must have clear success criteria",
            "- Must be testable and verifiable",
            "- Prefer high-impact, low-effort tasks",
            "",
            "## Output Format (JSON)",
            "Generate a single task as JSON:",
            "{",
            '  "id": "task-<type>-<timestamp>",',
            '  "instruction": "Clear, actionable task description with steps",',
            '  "rationale": "Why this task is important and its expected impact",',
            '  "goal_id": "goal-id or general",',
            '  "estimated_minutes": 30-120,',
            '  "priority": "P0|P1|P2|P3",',
            '  "complexity": "low|medium|high"',
            "}",
            "",
            "Generate the task now:",
        ])
        
        return "\n".join(lines)
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM provider with prompt."""
        # Adapt to provider interface
        # Assuming provider has generate(messages, config) method
        messages = [{"role": "user", "content": prompt}]
        
        # Build config
        config = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        
        # Call provider (sync or async)
        try:
            result = self.llm_provider.generate(messages=messages, config=config)
            # Extract content from GenerationResult
            if hasattr(result, 'content'):
                return result.content
            return str(result)
        except Exception as e:
            raise TaskGenerationError(f"LLM call failed: {e}")
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response as JSON."""
        # Extract JSON from response (may have markdown fences)
        response = response.strip()
        
        # Remove markdown code fences if present
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        
        response = response.strip()
        
        try:
            data = json.loads(response)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response: {response[:500]}")
            raise TaskGenerationError(f"Invalid JSON response from LLM: {e}")


def generate_batch_tasks(
    llm_provider: Any,
    context: TaskContext,
    system_context: Optional[Any],
    count: int = 10,
    max_complexity: str = "medium",
) -> List[GeneratedTask]:
    """
    Generate multiple tasks in one LLM call for efficiency.
    
    Args:
        llm_provider: LLM provider
        context: TaskContext
        system_context: SystemContext with health score
        count: Number of tasks to generate
        max_complexity: Max complexity
        
    Returns:
        List of GeneratedTask objects
    """
    generator = LLMTaskGenerator(llm_provider=llm_provider)
    
    # Build batch prompt
    prompt_lines = [
        f"Generate {count} high-impact improvement tasks for the codebase.",
        "",
        "## Current Context",
        f"- Test pass rate: {context.test_pass_rate * 100:.1f}%",
        f"- Coverage: {context.coverage_percentage:.1f}%",
    ]
    
    if system_context:
        prompt_lines.extend([
            f"- Health Score: {system_context.health_score.overall_score:.1f}/100",
            "",
            "### Top Opportunities:",
        ])
        for i, opp in enumerate(system_context.ranked_opportunities[:10], 1):
            prompt_lines.append(f"{i}. [{opp.category}] {opp.description} (Impact: {opp.impact}, Effort: {opp.effort})")
    
    prompt_lines.extend([
        "",
        "## Task Requirements",
        "Each task MUST include:",
        "1. Clear numbered steps (1., 2., 3., etc.)",
        "2. Success criteria or verification steps",
        "3. Specific file paths or components to modify",
        "",
        f"Generate {count} tasks as JSON array:",
        "[",
        "  {",
        '    "id": "task-1",',
        '    "instruction": "Task description\\n\\nSteps:\\n1. First step\\n2. Second step\\n3. Verify success",',
        '    "rationale": "Why this task matters and expected impact",',
        '    "goal_id": "coverage|testing|refactor|general",',
        '    "estimated_minutes": 30-120,',
        '    "priority": "P0|P1|P2|P3",',
        '    "complexity": "low|medium|high"',
        "  },",
        "  ...",
        "]",
    ])
    
    prompt = "\n".join(prompt_lines)
    
    try:
        response = generator._call_llm(prompt)
        # Parse JSON array
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        tasks_data = json.loads(response)
        
        tasks = []
        for task_data in tasks_data[:count]:
            task = GeneratedTask.create(
                id=task_data.get("id", f"batch-{len(tasks)}"),
                instruction=task_data.get("instruction", ""),
                rationale=task_data.get("rationale", ""),
                goal_id=task_data.get("goal_id", "general"),
                estimated_minutes=task_data.get("estimated_minutes", 60),
                priority=task_data.get("priority", "P2"),
                complexity=task_data.get("complexity", max_complexity),
            )
            tasks.append(task)
        
        return tasks
        
    except Exception as e:
        logger.error(f"Batch task generation failed: {e}")
        return []

