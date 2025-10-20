"""
Unit tests for PromptTemplateMerger.

Tests Phase 3: Template merging with task-specific information.
Clean Architecture: Use Case layer tests.
"""

import pytest
from src.entity import Agent, Task
from src.use_cases.prompt_template_merger import PromptTemplateMerger
from src.adapters.prompt.template_loader import PromptTemplate
from pathlib import Path


class TestPromptTemplateMerger:
    """Test suite for PromptTemplateMerger."""
    
    def test_merge_persona_with_placeholders(self):
        """Test merging persona with placeholders."""
        merger = PromptTemplateMerger()
        
        template_persona = "You are a {role} with {capabilities}. Tier: {tier}"
        agent = Agent(role="backend-developer", capabilities=["python", "fastapi"], tier=2)
        
        persona = merger._merge_persona(template_persona, agent)
        
        assert "backend-developer" in persona
        assert "python, fastapi" in persona
        assert "2" in persona
    
    def test_merge_persona_without_placeholders(self):
        """Test merging persona without placeholders."""
        merger = PromptTemplateMerger()
        
        template_persona = "Senior Backend Developer"
        agent = Agent(role="backend-developer", capabilities=["python", "fastapi"], tier=1)
        
        persona = merger._merge_persona(template_persona, agent)
        
        assert "Senior Backend Developer" in persona
        assert "python, fastapi" in persona  # Appended
        assert "Tier: 1" in persona  # Appended
    
    def test_merge_goal_with_placeholder(self):
        """Test merging goal with placeholder."""
        merger = PromptTemplateMerger()
        
        template_goal = "Successfully complete: {task_description}"
        task = Task(description="Implement caching layer")
        
        goal = merger._merge_goal(template_goal, task)
        
        assert "Implement caching layer" in goal
    
    def test_merge_goal_generic_template(self):
        """Test merging goal with generic template."""
        merger = PromptTemplateMerger()
        
        template_goal = "[Template section]"
        task = Task(description="Reduce API latency from 500ms to 100ms")
        
        goal = merger._merge_goal(template_goal, task)
        
        assert "Reduce API latency" in goal or "Successfully complete" in goal
    
    def test_merge_task_with_placeholder(self):
        """Test merging task with placeholder."""
        merger = PromptTemplateMerger()
        
        template_task = "Task: {task_description}\n\nSteps:\n1. Analyze\n2. Implement\n3. Test"
        task = Task(description="Add logging to authentication module")
        
        task_text = merger._merge_task(template_task, task)
        
        assert "Add logging to authentication module" in task_text
        assert "Steps:" in task_text
    
    def test_merge_task_generic_template(self):
        """Test merging task with generic template."""
        merger = PromptTemplateMerger()
        
        template_task = "[Template section]"
        task = Task(description="Implement feature X")
        
        task_text = merger._merge_task(template_task, task)
        
        assert "Implement feature X" in task_text
    
    def test_merge_context_with_placeholders(self):
        """Test merging context with placeholders."""
        merger = PromptTemplateMerger()
        
        template_context = "Agent Tier: {tier}\nPriority: {priority}"
        agent = Agent(role="developer", capabilities=["python"], tier=2)
        task = Task(description="Test task")
        task.priority = 1
        
        context = merger._merge_context(template_context, agent, task, None)
        
        assert "Tier: 2" in context
        assert "Priority: 1" in context
    
    def test_merge_context_with_runtime_context(self):
        """Test merging context with runtime context."""
        merger = PromptTemplateMerger()
        
        template_context = "Template context"
        agent = Agent(role="developer", capabilities=["python"])
        task = Task(description="Test task")
        runtime_context = "Previous interactions: 5\nULTRATHINK enabled"
        
        context = merger._merge_context(template_context, agent, task, runtime_context)
        
        assert "Template context" in context
        assert "Previous interactions: 5" in context
        assert "ULTRATHINK enabled" in context
    
    def test_extract_goal_with_keyword(self):
        """Test extracting goal from task with keyword."""
        merger = PromptTemplateMerger()
        
        task = Task(description="Reduce API latency from 500ms to 100ms")
        
        goal = merger._extract_goal_from_task(task)
        
        assert "Reduce API latency" in goal
    
    def test_extract_goal_without_keyword(self):
        """Test extracting goal from task without keyword."""
        merger = PromptTemplateMerger()
        
        task = Task(description="Add logging to module")
        
        goal = merger._extract_goal_from_task(task)
        
        assert "Successfully complete" in goal
        assert "Add logging" in goal
    
    def test_merge_full_template(self):
        """Test merging full template with agent and task."""
        merger = PromptTemplateMerger()
        
        template = PromptTemplate(
            domain="backend",
            framework="4-sentence",
            persona="Senior {role} with {capabilities}",
            goal="Build scalable services",
            task="{task_description}",
            context="Tier: {tier}",
            file_path="test.md",
            raw_content=""
        )
        
        agent = Agent(role="backend-developer", capabilities=["python", "fastapi"], tier=2)
        task = Task(description="Implement caching layer")
        
        strategy = merger.merge(template, agent, task, "ULTRATHINK enabled")
        
        assert "backend-developer" in strategy.persona
        assert "python, fastapi" in strategy.persona
        assert "Build scalable services" in strategy.goal
        assert "Implement caching layer" in strategy.task
        assert "Tier: 2" in strategy.context
        assert "ULTRATHINK enabled" in strategy.context
        assert strategy.agent_type == "backend-developer"
        assert strategy.domain == "backend"
    
    def test_merge_role_template(self):
        """Test merging ROLE Model template."""
        merger = PromptTemplateMerger()

        template = PromptTemplate(
            domain="testing",
            framework="role",
            persona="QA Engineer",
            goal="Ensure quality for {task_description}",  # Add placeholder
            task="Write tests for {task_description}",
            context="Coverage target: 80%",
            file_path="test.md",
            raw_content=""
        )

        agent = Agent(role="test-engineer", capabilities=["pytest", "selenium"])
        task = Task(description="authentication module")

        strategy = merger.merge(template, agent, task, None)

        assert "QA Engineer" in strategy.persona
        assert "pytest, selenium" in strategy.persona
        assert "Ensure quality" in strategy.goal or "authentication module" in strategy.goal
        assert "authentication module" in strategy.task
        assert "Coverage target: 80%" in strategy.context
        assert strategy.domain == "testing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

