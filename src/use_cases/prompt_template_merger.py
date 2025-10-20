"""
Prompt Template Merger - Merge templates with task-specific information.

Phase 3: Template Library Integration
Clean Architecture: Use Case layer
SOLID: SRP - Single responsibility for template merging
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from src.entity import Agent, Task
from src.entity.prompt_strategy import PromptStrategy
from src.adapters.prompt.template_loader import PromptTemplate

logger = logging.getLogger(__name__)


class PromptTemplateMerger:
    """
    Merge prompt templates with task-specific information.
    
    Features:
    - Replace template placeholders with actual values
    - Merge template persona with agent capabilities
    - Preserve template structure and quality
    - Fallback to dynamic generation if no template
    
    Usage:
        merger = PromptTemplateMerger()
        strategy = merger.merge(template, agent, task)
    """
    
    def merge(
        self,
        template: PromptTemplate,
        agent: Agent,
        task: Task,
        context_text: Optional[str] = None
    ) -> PromptStrategy:
        """
        Merge template with agent and task.
        
        Args:
            template: Prompt template from framework
            agent: Agent to execute task
            task: Task to execute
            context_text: Optional context text (tier, history, etc.)
            
        Returns:
            PromptStrategy with merged content
        """
        # Merge persona
        persona = self._merge_persona(template.persona, agent)
        
        # Merge goal
        goal = self._merge_goal(template.goal, task)
        
        # Merge task
        task_text = self._merge_task(template.task, task)
        
        # Merge context
        context = self._merge_context(template.context, agent, task, context_text)
        
        return PromptStrategy(
            persona=persona,
            goal=goal,
            task=task_text,
            context=context,
            agent_type=agent.role,
            domain=template.domain
        )
    
    def _merge_persona(self, template_persona: str, agent: Agent) -> str:
        """
        Merge template persona with agent capabilities.
        
        Replaces:
        - {role} → agent.role
        - {capabilities} → agent.capabilities
        - {tier} → agent.tier
        """
        persona = template_persona
        
        # Replace placeholders
        persona = persona.replace("{role}", agent.role)
        persona = persona.replace("{tier}", str(agent.tier) if hasattr(agent, 'tier') and agent.tier else "1")
        
        # Replace capabilities
        if "{capabilities}" in persona:
            caps = ", ".join(agent.capabilities) if agent.capabilities else "general"
            persona = persona.replace("{capabilities}", caps)
        
        # Append agent-specific info if not in template
        if agent.capabilities and "Capabilities:" not in persona:
            caps_str = ", ".join(agent.capabilities)
            persona += f"\nCapabilities: {caps_str}"
        
        if hasattr(agent, 'tier') and agent.tier and "Tier" not in persona:
            persona += f"\nTier: {agent.tier}"
        
        return persona.strip()
    
    def _merge_goal(self, template_goal: str, task: Task) -> str:
        """
        Merge template goal with task-specific goal.
        
        Replaces:
        - {task_description} → task.description
        - {priority} → task.priority
        """
        goal = template_goal
        
        # Replace placeholders
        if "{task_description}" in goal:
            goal = goal.replace("{task_description}", task.description)
        
        if hasattr(task, 'priority') and task.priority:
            goal = goal.replace("{priority}", str(task.priority))
        
        # If template goal is generic, extract from task
        if goal == "[Template section]" or len(goal) < 20:
            goal = self._extract_goal_from_task(task)
        
        return goal.strip()
    
    def _merge_task(self, template_task: str, task: Task) -> str:
        """
        Merge template task with actual task description.
        
        Replaces:
        - {task_description} → task.description
        - {steps} → task.steps (if available)
        """
        task_text = template_task
        
        # Replace placeholders
        if "{task_description}" in task_text:
            task_text = task_text.replace("{task_description}", task.description)
        
        # If template task is generic, use task description
        if task_text == "[Template section]" or len(task_text) < 20:
            task_text = task.description
        
        # Append task description if not already present
        if task.description not in task_text:
            task_text += f"\n\nTask: {task.description}"
        
        return task_text.strip()
    
    def _merge_context(
        self,
        template_context: str,
        agent: Agent,
        task: Task,
        context_text: Optional[str]
    ) -> str:
        """
        Merge template context with runtime context.
        
        Replaces:
        - {tier} → agent.tier
        - {priority} → task.priority
        - {constraints} → task.constraints (if available)
        """
        context = template_context
        
        # Replace placeholders
        if hasattr(agent, 'tier') and agent.tier:
            context = context.replace("{tier}", str(agent.tier))
        
        if hasattr(task, 'priority') and task.priority:
            context = context.replace("{priority}", str(task.priority))
        
        # Append runtime context if provided
        if context_text:
            if context == "[Template section]":
                context = context_text
            else:
                context += f"\n\n{context_text}"
        
        return context.strip()
    
    def _extract_goal_from_task(self, task: Task) -> str:
        """
        Extract goal from task description.
        
        Heuristics:
        - Look for goal keywords: reduce, improve, increase, achieve, optimize
        - Look for metrics: from X to Y, by X%, < X ms
        - Fallback: "Successfully complete: {task}"
        """
        desc = task.description.lower()
        
        # Goal keywords
        goal_keywords = ["reduce", "improve", "increase", "achieve", "optimize", "minimize", "maximize"]
        
        for keyword in goal_keywords:
            if keyword in desc:
                # Extract sentence containing keyword
                sentences = task.description.split(".")
                for sentence in sentences:
                    if keyword in sentence.lower():
                        return sentence.strip()
        
        # Fallback
        return f"Successfully complete: {task.description}"

