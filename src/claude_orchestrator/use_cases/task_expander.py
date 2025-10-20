"""TaskExpander - Template-based task expansion.

Expands high-level goals into concrete task sequences using templates.

Clean Architecture: Use Case layer
SOLID: SRP - Single responsibility for task expansion
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import yaml

from src.claude_orchestrator.entities.generated_task import GeneratedTask
from src.claude_orchestrator.entities.goal import Goal

logger = logging.getLogger(__name__)


class TaskExpander:
    """
    Expands high-level goals into concrete task sequences.
    
    Uses templates from tasks/ directory to generate step-by-step tasks.
    
    Usage:
        expander = TaskExpander(templates_dir="tasks")
        tasks = expander.expand_goal(goal, context)
    """
    
    def __init__(self, templates_dir: str = "tasks"):
        """
        Initialize task expander.
        
        Args:
            templates_dir: Path to task templates directory
        """
        self.templates_dir = Path(templates_dir)
        self.templates_cache: Dict[str, Dict[str, Any]] = {}
    
    def load_templates(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Load task templates from YAML files.
        
        Args:
            domain: Optional domain filter
            
        Returns:
            List of template dictionaries
        """
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return []
        
        templates = []
        
        for yaml_file in self.templates_dir.rglob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    template = yaml.safe_load(f)
                    
                    # Filter by domain if specified
                    if domain and template.get('domain') != domain:
                        continue
                    
                    templates.append(template)
                    
            except Exception as e:
                logger.error(f"Failed to load template {yaml_file}: {e}")
        
        return templates
    
    def expand_goal(
        self,
        goal: Goal,
        context: Optional[Any] = None,
        max_tasks: int = 5,
    ) -> List[GeneratedTask]:
        """
        Expand a goal into concrete tasks using templates.
        
        Args:
            goal: Goal to expand
            context: Optional TaskContext for context-aware expansion
            max_tasks: Maximum number of tasks to generate
            
        Returns:
            List of GeneratedTask objects
        """
        # Load templates matching goal domain/type
        templates = self.load_templates(domain=None)  # Load all for now
        
        # Find relevant templates
        relevant = self._find_relevant_templates(goal, templates)
        
        if not relevant:
            logger.info(f"No templates found for goal {goal.id}, generating generic task")
            return [self._generate_generic_task(goal)]
        
        # Expand using templates
        tasks = []
        for template in relevant[:max_tasks]:
            task = self._expand_template(template, goal, context)
            if task:
                tasks.append(task)
        
        return tasks
    
    def _find_relevant_templates(
        self,
        goal: Goal,
        templates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Find templates relevant to goal."""
        relevant = []
        
        goal_keywords = set(goal.title.lower().split() + goal.description.lower().split())
        
        for template in templates:
            # Match by domain
            if template.get('domain') and goal.title:
                if template['domain'].lower() in goal.title.lower():
                    relevant.append(template)
                    continue
            
            # Match by keywords
            template_name = template.get('name', '').lower()
            template_desc = template.get('description', '').lower()
            
            # Simple keyword overlap
            template_keywords = set(template_name.split() + template_desc.split())
            overlap = len(goal_keywords & template_keywords)
            
            if overlap >= 2:
                relevant.append(template)
        
        return relevant
    
    def _expand_template(
        self,
        template: Dict[str, Any],
        goal: Goal,
        context: Optional[Any],
    ) -> Optional[GeneratedTask]:
        """Expand a single template into a task."""
        try:
            # Extract template fields
            name = template.get('name', 'Unnamed task')
            description = template.get('description', '')
            domain = template.get('domain', 'general')
            
            # Build instruction from template
            instruction_parts = [f"Task: {name}", ""]
            
            if description:
                instruction_parts.append(f"Description: {description}")
                instruction_parts.append("")
            
            # Add inputs if present
            if 'inputs' in template:
                instruction_parts.append("Inputs:")
                for key, value in template['inputs'].items():
                    instruction_parts.append(f"- {key}: {value}")
                instruction_parts.append("")
            
            # Add acceptance criteria if present
            if 'acceptance_criteria' in template:
                instruction_parts.append("Acceptance Criteria:")
                for criterion in template['acceptance_criteria']:
                    instruction_parts.append(f"- {criterion}")
                instruction_parts.append("")
            
            # Add notes if present
            if 'notes' in template:
                instruction_parts.append("Notes:")
                for note in template['notes']:
                    instruction_parts.append(f"- {note}")
            
            instruction = "\n".join(instruction_parts)
            
            # Build rationale
            rationale = f"Expanding goal '{goal.title}' using template '{name}' from domain '{domain}'"
            
            # Estimate time (default 60 min)
            estimated_minutes = 60
            
            # Create task
            task = GeneratedTask.create(
                id=f"expanded-{goal.id}-{domain}",
                instruction=instruction,
                rationale=rationale,
                goal_id=goal.id,
                estimated_minutes=estimated_minutes,
                priority=goal.priority,
                complexity="medium",
            )
            
            return task
            
        except Exception as e:
            logger.error(f"Failed to expand template: {e}")
            return None
    
    def _generate_generic_task(self, goal: Goal) -> GeneratedTask:
        """Generate a generic task when no templates match."""
        instruction = f"""Work on goal: {goal.title}

Goal: {goal.description}
Type: {goal.goal_type.value}
Priority: {goal.priority}

Steps:
1. Review the goal requirements
2. Identify the next incremental step
3. Implement that step
4. Test your changes
5. Document progress"""
        
        rationale = f"Generic task for goal '{goal.title}' (no matching templates found)"
        
        return GeneratedTask.create(
            id=f"generic-{goal.id}",
            instruction=instruction,
            rationale=rationale,
            goal_id=goal.id,
            estimated_minutes=60,
            priority=goal.priority,
            complexity="medium",
        )

