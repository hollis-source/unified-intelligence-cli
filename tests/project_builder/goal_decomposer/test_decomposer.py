"""Tests for GoalDecomposer - Natural language to HTN conversion.

Tests cover:
- LLM integration with Qwen3-Next-80B-A3B-Thinking
- JSON parsing and repair logic
- Retry logic with stricter prompts
- HTN validation (depth, circular dependencies)
- Error handling for malformed responses
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json

from src.project_builder.goal_decomposer.decomposer import GoalDecomposer
from src.entities.htn.htn_node import HTNNode
from src.interfaces import LLMConfig


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_thinking_model():
    """Mock ITextGenerator for thinking model."""
    model = Mock()
    
    # Return valid HTN JSON
    valid_response = """
    ```json
    {
        "task_id": "create_api",
        "description": "Create REST API",
        "subtasks": [
            {
                "task_id": "design_schema",
                "description": "Design API schema",
                "subtasks": [],
                "preconditions": {},
                "effects": {"artifact_design": "schema.json"}
            },
            {
                "task_id": "implement_endpoints",
                "description": "Implement API endpoints",
                "subtasks": [],
                "preconditions": {"artifact_design": null},
                "effects": {"artifact_code": "api.py"}
            }
        ],
        "preconditions": {},
        "effects": {"api_complete": true}
    }
    ```
    """
    model.generate = Mock(return_value=valid_response)
    return model


@pytest.fixture
def decomposer(mock_thinking_model):
    """Create GoalDecomposer with mocked thinking model."""
    return GoalDecomposer(thinking_model=mock_thinking_model)


@pytest.fixture
def sample_htn_dict():
    """Sample HTN dictionary for testing."""
    return {
        "task_id": "root",
        "description": "Root task",
        "subtasks": [
            {
                "task_id": "subtask1",
                "description": "Subtask 1",
                "subtasks": [],
                "preconditions": {},
                "effects": {"result": "value1"}
            }
        ],
        "preconditions": {},
        "effects": {}
    }


# ============================================================================
# Test Classes
# ============================================================================

class TestGoalDecomposerBasic:
    """Tests for basic goal decomposition."""
    
    @pytest.mark.asyncio
    async def test_decompose_goal_success(self, decomposer, mock_thinking_model):
        """Test successful goal decomposition."""
        result = await decomposer.decompose_goal("Create a REST API")
        
        assert isinstance(result, HTNNode)
        assert result.task_id == "create_api"
        assert result.description == "Create REST API"
        assert len(result.subtasks) == 2
    
    @pytest.mark.asyncio
    async def test_decompose_goal_calls_llm(self, decomposer, mock_thinking_model):
        """Test that decompose_goal calls LLM."""
        await decomposer.decompose_goal("Create a REST API")
        
        mock_thinking_model.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_decompose_goal_uses_correct_config(self, decomposer, mock_thinking_model):
        """Test that decompose_goal uses correct LLM config."""
        await decomposer.decompose_goal("Create a REST API")
        
        call_args = mock_thinking_model.generate.call_args
        config = call_args[1]['config']
        assert isinstance(config, LLMConfig)
        assert config.temperature == 0.4
        assert config.max_tokens == 8192
    
    @pytest.mark.asyncio
    async def test_decompose_goal_removes_root_preconditions(
        self,
        decomposer,
        mock_thinking_model
    ):
        """Test that root task preconditions are removed (safety measure)."""
        # Return HTN with root preconditions
        response_with_preconditions = """
        {
            "task_id": "root",
            "description": "Root",
            "subtasks": [],
            "preconditions": {"invalid": "should_be_removed"},
            "effects": {}
        }
        """
        mock_thinking_model.generate = Mock(return_value=response_with_preconditions)
        
        result = await decomposer.decompose_goal("Test goal")
        
        # Root preconditions should be empty
        assert result.preconditions == {}
    
    @pytest.mark.asyncio
    async def test_decompose_goal_preserves_subtask_structure(
        self,
        decomposer,
        mock_thinking_model
    ):
        """Test that subtask hierarchy is preserved."""
        result = await decomposer.decompose_goal("Create a REST API")
        
        assert len(result.subtasks) == 2
        assert result.subtasks[0].task_id == "design_schema"
        assert result.subtasks[1].task_id == "implement_endpoints"
        # Check preconditions preserved
        assert result.subtasks[1].preconditions == {"artifact_design": None}


class TestLLMIntegration:
    """Tests for LLM integration and prompt generation."""
    
    @pytest.mark.asyncio
    async def test_decompose_builds_correct_prompt(
        self,
        decomposer,
        mock_thinking_model
    ):
        """Test that correct prompt is built for LLM."""
        await decomposer.decompose_goal("Create a REST API")

        call_args = mock_thinking_model.generate.call_args
        # Access keyword arguments
        messages = call_args.kwargs.get('messages') or call_args[1].get('messages')
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "Create a REST API" in messages[0]["content"]
        assert "Hierarchical Task Network" in messages[0]["content"]
    
    @pytest.mark.asyncio
    async def test_decompose_uses_stricter_prompt_on_retry(
        self,
        decomposer,
        mock_thinking_model
    ):
        """Test that stricter prompt is used on retry."""
        # First call fails with JSON error
        mock_thinking_model.generate = Mock(
            side_effect=[
                "invalid json",
                """{"task_id": "root", "description": "Root", "subtasks": [], "preconditions": {}, "effects": {}}"""
            ]
        )

        result = await decomposer.decompose_goal("Create API")

        # Should call generate twice
        assert mock_thinking_model.generate.call_count == 2

        # Second call should have stricter prompt
        second_call_args = mock_thinking_model.generate.call_args_list[1]
        messages = second_call_args.kwargs.get('messages') or second_call_args[1].get('messages')
        prompt = messages[0]["content"]
        assert "CRITICAL" in prompt
        assert "JSON syntax errors" in prompt
    
    @pytest.mark.asyncio
    async def test_decompose_lowers_temperature_on_retry(
        self,
        decomposer,
        mock_thinking_model
    ):
        """Test that temperature is lowered on retry."""
        mock_thinking_model.generate = Mock(
            side_effect=[
                "invalid json",
                """{"task_id": "root", "description": "Root", "subtasks": [], "preconditions": {}, "effects": {}}"""
            ]
        )
        
        await decomposer.decompose_goal("Create API")
        
        # First call: temperature 0.4
        first_config = mock_thinking_model.generate.call_args_list[0][1]['config']
        assert first_config.temperature == 0.4
        
        # Second call: temperature 0.3
        second_config = mock_thinking_model.generate.call_args_list[1][1]['config']
        assert second_config.temperature == 0.3


class TestJSONParsing:
    """Tests for JSON parsing and repair logic."""
    
    @pytest.mark.asyncio
    async def test_parse_json_from_markdown_code_block(
        self,
        decomposer,
        mock_thinking_model
    ):
        """Test parsing JSON from markdown code block."""
        response = """
        Here's the HTN:
        ```json
        {"task_id": "test", "description": "Test", "subtasks": [], "preconditions": {}, "effects": {}}
        ```
        """
        mock_thinking_model.generate = Mock(return_value=response)
        
        result = await decomposer.decompose_goal("Test")
        
        assert result.task_id == "test"
    
    @pytest.mark.asyncio
    async def test_parse_json_without_code_block(
        self,
        decomposer,
        mock_thinking_model
    ):
        """Test parsing JSON without markdown code block."""
        response = '{"task_id": "test", "description": "Test", "subtasks": [], "preconditions": {}, "effects": {}}'
        mock_thinking_model.generate = Mock(return_value=response)
        
        result = await decomposer.decompose_goal("Test")
        
        assert result.task_id == "test"
    
    def test_repair_json_removes_trailing_commas(self, decomposer):
        """Test JSON repair removes trailing commas."""
        malformed = '{"key": "value",}'
        repaired = decomposer._repair_json(malformed)
        
        # Should be valid JSON now
        parsed = json.loads(repaired)
        assert parsed["key"] == "value"
    
    def test_repair_json_removes_comments(self, decomposer):
        """Test JSON repair removes comments."""
        malformed = '''
        {
            // This is a comment
            "key": "value"
        }
        '''
        repaired = decomposer._repair_json(malformed)
        
        parsed = json.loads(repaired)
        assert parsed["key"] == "value"
    
    def test_repair_json_adds_missing_commas(self, decomposer):
        """Test JSON repair adds missing commas between objects."""
        malformed = '{"a": "1"\n"b": "2"}'
        repaired = decomposer._repair_json(malformed)
        
        parsed = json.loads(repaired)
        assert parsed["a"] == "1"
        assert parsed["b"] == "2"
    
    @pytest.mark.asyncio
    async def test_parse_with_repair_on_malformed_json(
        self,
        decomposer,
        mock_thinking_model
    ):
        """Test that malformed JSON is repaired automatically."""
        # JSON with trailing comma
        malformed_response = '{"task_id": "test", "description": "Test", "subtasks": [], "preconditions": {}, "effects": {},}'
        mock_thinking_model.generate = Mock(return_value=malformed_response)
        
        result = await decomposer.decompose_goal("Test")
        
        assert result.task_id == "test"


class TestRetryLogic:
    """Tests for retry logic on failures."""
    
    @pytest.mark.asyncio
    async def test_decompose_retries_on_json_error(
        self,
        decomposer,
        mock_thinking_model
    ):
        """Test retry on JSON parsing error."""
        mock_thinking_model.generate = Mock(
            side_effect=[
                "completely invalid",
                """{"task_id": "root", "description": "Root", "subtasks": [], "preconditions": {}, "effects": {}}"""
            ]
        )
        
        result = await decomposer.decompose_goal("Create API")
        
        assert mock_thinking_model.generate.call_count == 2
        assert result.task_id == "root"
    
    @pytest.mark.asyncio
    async def test_decompose_respects_max_retries(
        self,
        decomposer,
        mock_thinking_model
    ):
        """Test that max_retries is respected."""
        mock_thinking_model.generate = Mock(return_value="invalid json always")
        
        with pytest.raises(ValueError) as exc_info:
            await decomposer.decompose_goal("Create API")
        
        assert "Failed to decompose goal after 3 attempts" in str(exc_info.value)
        assert mock_thinking_model.generate.call_count == 3
    
    @pytest.mark.asyncio
    async def test_decompose_retries_on_validation_error(
        self,
        decomposer,
        mock_thinking_model
    ):
        """Test retry on HTN validation error."""
        # First response: HTN too deep (depth > 5)
        # Second response: Valid HTN
        mock_thinking_model.generate = Mock(
            side_effect=[
                """{"task_id": "root", "description": "Root", "subtasks": [
                    {"task_id": "l1", "description": "L1", "subtasks": [
                        {"task_id": "l2", "description": "L2", "subtasks": [
                            {"task_id": "l3", "description": "L3", "subtasks": [
                                {"task_id": "l4", "description": "L4", "subtasks": [
                                    {"task_id": "l5", "description": "L5", "subtasks": [
                                        {"task_id": "l6", "description": "L6", "subtasks": [], "preconditions": {}, "effects": {}}
                                    ], "preconditions": {}, "effects": {}}
                                ], "preconditions": {}, "effects": {}}
                            ], "preconditions": {}, "effects": {}}
                        ], "preconditions": {}, "effects": {}}
                    ], "preconditions": {}, "effects": {}}
                ], "preconditions": {}, "effects": {}}""",
                """{"task_id": "root", "description": "Root", "subtasks": [], "preconditions": {}, "effects": {}}"""
            ]
        )
        
        result = await decomposer.decompose_goal("Create API")

        assert mock_thinking_model.generate.call_count == 2
        assert result.task_id == "root"


class TestHTNValidation:
    """Tests for HTN structure validation."""

    @pytest.mark.asyncio
    async def test_validate_htn_rejects_excessive_depth(
        self,
        decomposer,
        mock_thinking_model
    ):
        """Test that HTN with depth > 5 is rejected."""
        # Create deeply nested HTN (depth 6)
        deep_htn = """
        {"task_id": "root", "description": "Root", "subtasks": [
            {"task_id": "l1", "description": "L1", "subtasks": [
                {"task_id": "l2", "description": "L2", "subtasks": [
                    {"task_id": "l3", "description": "L3", "subtasks": [
                        {"task_id": "l4", "description": "L4", "subtasks": [
                            {"task_id": "l5", "description": "L5", "subtasks": [
                                {"task_id": "l6", "description": "L6", "subtasks": [], "preconditions": {}, "effects": {}}
                            ], "preconditions": {}, "effects": {}}
                        ], "preconditions": {}, "effects": {}}
                    ], "preconditions": {}, "effects": {}}
                ], "preconditions": {}, "effects": {}}
            ], "preconditions": {}, "effects": {}}
        ], "preconditions": {}, "effects": {}}
        """
        mock_thinking_model.generate = Mock(return_value=deep_htn)

        with pytest.raises(ValueError) as exc_info:
            await decomposer.decompose_goal("Create API")

        assert "depth" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_htn_detects_circular_dependencies(
        self,
        decomposer
    ):
        """Test detection of circular task dependencies."""
        # Create HTN with duplicate task_id (simpler circular check)
        node1 = HTNNode(task_id="task1", description="Task 1")
        node2 = HTNNode(task_id="task1", description="Task 1 duplicate")  # Same ID!
        node1.add_subtask(node2)

        with pytest.raises(ValueError) as exc_info:
            decomposer._validate_htn(node1)

        assert "circular" in str(exc_info.value).lower()

    def test_validate_htn_accepts_valid_structure(self, decomposer):
        """Test that valid HTN passes validation."""
        valid_htn = HTNNode(
            task_id="root",
            description="Root",
            subtasks=[
                HTNNode(task_id="task1", description="Task 1"),
                HTNNode(task_id="task2", description="Task 2")
            ]
        )

        # Should not raise
        decomposer._validate_htn(valid_htn)


class TestDictToHTNConversion:
    """Tests for dictionary to HTNNode conversion."""

    def test_dict_to_htn_basic(self, decomposer, sample_htn_dict):
        """Test basic dictionary to HTN conversion."""
        result = decomposer._dict_to_htn(sample_htn_dict)

        assert isinstance(result, HTNNode)
        assert result.task_id == "root"
        assert result.description == "Root task"

    def test_dict_to_htn_with_subtasks(self, decomposer, sample_htn_dict):
        """Test conversion with subtasks."""
        result = decomposer._dict_to_htn(sample_htn_dict)

        assert len(result.subtasks) == 1
        assert result.subtasks[0].task_id == "subtask1"

    def test_dict_to_htn_preserves_preconditions(self, decomposer):
        """Test that preconditions are preserved."""
        htn_dict = {
            "task_id": "test",
            "description": "Test",
            "subtasks": [],
            "preconditions": {"file_path": None},
            "effects": {}
        }

        result = decomposer._dict_to_htn(htn_dict)

        assert result.preconditions == {"file_path": None}

    def test_dict_to_htn_preserves_effects(self, decomposer):
        """Test that effects are preserved."""
        htn_dict = {
            "task_id": "test",
            "description": "Test",
            "subtasks": [],
            "preconditions": {},
            "effects": {"artifact_code": "code.py"}
        }

        result = decomposer._dict_to_htn(htn_dict)

        assert result.effects == {"artifact_code": "code.py"}

    def test_dict_to_htn_missing_task_id(self, decomposer):
        """Test error on missing task_id."""
        invalid_dict = {
            "description": "Test",
            "subtasks": []
        }

        with pytest.raises(ValueError) as exc_info:
            decomposer._dict_to_htn(invalid_dict)

        assert "task_id" in str(exc_info.value)

    def test_dict_to_htn_missing_description(self, decomposer):
        """Test error on missing description."""
        invalid_dict = {
            "task_id": "test",
            "subtasks": []
        }

        with pytest.raises(ValueError) as exc_info:
            decomposer._dict_to_htn(invalid_dict)

        assert "description" in str(exc_info.value)
