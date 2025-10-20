"""Tests for goal decomposer use case.

Tests LLM-driven goal → HTN decomposition with retry logic and validation.
"""

import pytest
import anyio
from unittest.mock import Mock, AsyncMock
from src.use_cases.goal_decomposer import GoalDecomposerUseCase
from src.entity.htn import HTNNode


@pytest.mark.anyio
async def test_goal_decomposition_success():
    """Test successful goal decomposition."""
    # Mock LLM provider
    llm_provider = Mock()
    llm_provider.generate = AsyncMock(return_value="""
    {
      "task_id": "build_api",
      "description": "Build REST API",
      "subtasks": [
        {
          "task_id": "design",
          "description": "Design API schema",
          "preconditions": {},
          "effects": {"design_complete": true},
          "subtasks": []
        },
        {
          "task_id": "implement",
          "description": "Implement API endpoints",
          "preconditions": {"design_complete": true},
          "effects": {"api_complete": true},
          "subtasks": []
        }
      ],
      "preconditions": {},
      "effects": {}
    }
    """)
    
    decomposer = GoalDecomposerUseCase(llm_provider=llm_provider)
    htn = await decomposer.decompose_goal("Build a REST API")
    
    assert htn.task_id == "build_api"
    assert htn.description == "Build REST API"
    assert len(htn.subtasks) == 2
    assert htn.subtasks[0].task_id == "design"
    assert htn.subtasks[1].task_id == "implement"
    assert htn.subtasks[1].preconditions == {"design_complete": True}
    assert htn.preconditions == {}  # Root preconditions removed for safety


@pytest.mark.asyncio
async def test_goal_decomposition_with_context():
    """Test goal decomposition with context."""
    llm_provider = Mock()
    llm_provider.generate = AsyncMock(return_value="""
    {
      "task_id": "build_python_api",
      "description": "Build Python REST API with FastAPI",
      "subtasks": [
        {
          "task_id": "setup",
          "description": "Setup FastAPI project",
          "preconditions": {},
          "effects": {"project_setup": true},
          "subtasks": []
        }
      ],
      "preconditions": {},
      "effects": {}
    }
    """)
    
    decomposer = GoalDecomposerUseCase(llm_provider=llm_provider)
    context = {
        "project_info": {"language": "Python", "framework": "FastAPI"},
        "constraints": {"max_complexity": "medium"}
    }
    
    htn = await decomposer.decompose_goal("Build REST API", context=context)
    
    assert htn.task_id == "build_python_api"
    assert "FastAPI" in htn.description
    
    # Verify context was passed to LLM
    call_args = llm_provider.generate.call_args
    prompt = call_args[1]["messages"][0]["content"]
    assert "Context:" in prompt
    assert "Python" in prompt


@pytest.mark.asyncio
async def test_goal_decomposition_retry_on_invalid_json():
    """Test retry logic on invalid JSON."""
    llm_provider = Mock()
    llm_provider.generate = AsyncMock(side_effect=[
        "Invalid JSON {",  # First attempt fails
        '{"task_id": "task1", "description": "Task", "subtasks": [], "preconditions": {}, "effects": {}}'  # Second succeeds
    ])
    
    decomposer = GoalDecomposerUseCase(llm_provider=llm_provider, max_retries=3)
    htn = await decomposer.decompose_goal("Simple goal")
    
    assert htn.task_id == "task1"
    assert llm_provider.generate.call_count == 2  # Retried once


@pytest.mark.asyncio
async def test_goal_decomposition_retry_exhausted():
    """Test failure after max retries."""
    llm_provider = Mock()
    llm_provider.generate = AsyncMock(return_value="Invalid JSON {")
    
    decomposer = GoalDecomposerUseCase(llm_provider=llm_provider, max_retries=2)
    
    with pytest.raises(ValueError, match="Failed to decompose goal after 2 attempts"):
        await decomposer.decompose_goal("Goal")
    
    assert llm_provider.generate.call_count == 2


@pytest.mark.asyncio
async def test_goal_decomposition_markdown_code_blocks():
    """Test handling of markdown code blocks in LLM response."""
    llm_provider = Mock()
    llm_provider.generate = AsyncMock(return_value="""
    ```json
    {
      "task_id": "task1",
      "description": "Task",
      "subtasks": [],
      "preconditions": {},
      "effects": {}
    }
    ```
    """)
    
    decomposer = GoalDecomposerUseCase(llm_provider=llm_provider)
    htn = await decomposer.decompose_goal("Goal")
    
    assert htn.task_id == "task1"


@pytest.mark.asyncio
async def test_goal_decomposition_nested_subtasks():
    """Test decomposition with nested subtasks."""
    llm_provider = Mock()
    llm_provider.generate = AsyncMock(return_value="""
    {
      "task_id": "root",
      "description": "Root task",
      "subtasks": [
        {
          "task_id": "parent",
          "description": "Parent task",
          "subtasks": [
            {
              "task_id": "child",
              "description": "Child task",
              "subtasks": [],
              "preconditions": {},
              "effects": {}
            }
          ],
          "preconditions": {},
          "effects": {}
        }
      ],
      "preconditions": {},
      "effects": {}
    }
    """)
    
    decomposer = GoalDecomposerUseCase(llm_provider=llm_provider)
    htn = await decomposer.decompose_goal("Complex goal")
    
    assert htn.task_id == "root"
    assert len(htn.subtasks) == 1
    assert htn.subtasks[0].task_id == "parent"
    assert len(htn.subtasks[0].subtasks) == 1
    assert htn.subtasks[0].subtasks[0].task_id == "child"
    assert htn.get_depth() == 2


def test_validate_htn_success():
    """Test HTN validation with valid structure."""
    decomposer = GoalDecomposerUseCase(llm_provider=Mock())
    
    htn = HTNNode(
        task_id="task1",
        description="Task 1",
        subtasks=[
            HTNNode(
                task_id="subtask1",
                description="Subtask 1",
                preconditions={},
                effects={}
            )
        ],
        preconditions={},
        effects={}
    )
    
    assert decomposer.validate_htn(htn) is True


def test_validate_htn_missing_task_id():
    """Test validation fails on missing task_id."""
    decomposer = GoalDecomposerUseCase(llm_provider=Mock())
    
    htn = HTNNode(
        task_id="",
        description="Task",
        preconditions={},
        effects={}
    )
    
    with pytest.raises(ValueError, match="missing task_id"):
        decomposer.validate_htn(htn)


def test_validate_htn_missing_description():
    """Test validation fails on missing description."""
    decomposer = GoalDecomposerUseCase(llm_provider=Mock())
    
    htn = HTNNode(
        task_id="task1",
        description="",
        preconditions={},
        effects={}
    )
    
    with pytest.raises(ValueError, match="missing description"):
        decomposer.validate_htn(htn)


def test_validate_htn_invalid_preconditions():
    """Test validation fails on non-dict preconditions."""
    decomposer = GoalDecomposerUseCase(llm_provider=Mock())
    
    htn = HTNNode(
        task_id="task1",
        description="Task",
        subtasks=[],
        preconditions="invalid",  # Should be dict
        effects={}
    )
    
    with pytest.raises(ValueError, match="preconditions must be dict"):
        decomposer.validate_htn(htn)


def test_validate_htn_invalid_subtask():
    """Test validation fails on invalid subtask."""
    decomposer = GoalDecomposerUseCase(llm_provider=Mock())
    
    htn = HTNNode(
        task_id="parent",
        description="Parent",
        subtasks=[
            HTNNode(
                task_id="",  # Invalid
                description="Child",
                preconditions={},
                effects={}
            )
        ],
        preconditions={},
        effects={}
    )
    
    with pytest.raises(ValueError, match="Subtask 0 of 'parent' invalid"):
        decomposer.validate_htn(htn)


@pytest.mark.asyncio
async def test_convenience_function():
    """Test convenience function for quick usage."""
    from src.use_cases.goal_decomposer import decompose_goal
    
    llm_provider = Mock()
    llm_provider.generate = AsyncMock(return_value="""
    {
      "task_id": "task1",
      "description": "Task",
      "subtasks": [],
      "preconditions": {},
      "effects": {}
    }
    """)
    
    htn = await decompose_goal("Goal", llm_provider)
    
    assert htn.task_id == "task1"
    assert htn.description == "Task"

