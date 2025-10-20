"""Tests for CLITaskExecutor - Deprecated task executor for DSL.

Tests cover:
- Initialization and deprecation warning
- Task-to-agent mapping (exact, lowercase, partial, fallback)
- Task execution with real task modules
- Task execution with router facade
- Task execution fallback path
- Lifecycle callbacks
- Custom task mapping
- Error handling
"""

import pytest
import warnings
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.dsl.adapters.cli_task_executor import CLITaskExecutor


class TestCLITaskExecutorInitialization:
    """Test CLITaskExecutor initialization and configuration."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            executor = CLITaskExecutor()
            
            # Check deprecation warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "CLITaskExecutor is deprecated" in str(w[0].message)
            
            # Check default values
            assert executor.task_coordinator is None
            assert executor.task_to_agent_map == CLITaskExecutor.DEFAULT_TASK_MAPPING
            assert executor.router_facade is None
            assert executor.agent_factory is None
            assert executor.lifecycle is None

    def test_init_with_custom_parameters(self):
        """Test initialization with custom parameters."""
        mock_coordinator = Mock()
        custom_mapping = {"custom_task": "custom-agent"}
        mock_router = Mock()
        mock_factory = Mock()
        mock_lifecycle = Mock()
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            executor = CLITaskExecutor(
                task_coordinator=mock_coordinator,
                task_mapping=custom_mapping,
                router_facade=mock_router,
                agent_factory=mock_factory,
                lifecycle=mock_lifecycle
            )
            
            assert executor.task_coordinator is mock_coordinator
            assert executor.task_to_agent_map == custom_mapping
            assert executor.router_facade is mock_router
            assert executor.agent_factory is mock_factory
            assert executor.lifecycle is mock_lifecycle

    def test_default_task_mapping_content(self):
        """Test that default task mapping contains expected entries."""
        mapping = CLITaskExecutor.DEFAULT_TASK_MAPPING
        
        # Test key categories
        assert mapping["plan"] == "master-orchestrator"
        assert mapping["code"] == "python-specialist"
        assert mapping["test"] == "unit-test-engineer"
        assert mapping["frontend"] == "frontend-lead"
        assert mapping["backend"] == "backend-lead"
        assert mapping["deploy"] == "devops-lead"
        assert mapping["document"] == "technical-writer"
        assert mapping["task"] == "python-specialist"  # fallback


class TestTaskToAgentMapping:
    """Test _get_agent_for_task method."""

    def setup_method(self):
        """Set up test executor."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.executor = CLITaskExecutor()

    def test_exact_match(self):
        """Test exact task name match."""
        agent = self.executor._get_agent_for_task("plan")
        assert agent == "master-orchestrator"

    def test_lowercase_match(self):
        """Test lowercase task name match."""
        agent = self.executor._get_agent_for_task("PLAN")
        assert agent == "master-orchestrator"

    def test_partial_match(self):
        """Test partial task name match."""
        # Test with a task that contains "ui" which maps to "frontend-lead"
        # Use a task name where "ui" appears before other matching keys
        agent = self.executor._get_agent_for_task("ui_component_creation")
        assert agent == "frontend-lead"  # Contains "ui"

    def test_fallback_to_default(self):
        """Test fallback to default agent for unknown tasks."""
        agent = self.executor._get_agent_for_task("unknown_task")
        assert agent == "python-specialist"

    def test_empty_task_name(self):
        """Test empty task name fallback."""
        agent = self.executor._get_agent_for_task("")
        assert agent == "python-specialist"


class TestTaskExecution:
    """Test execute_task method."""

    def setup_method(self):
        """Set up test executor."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.executor = CLITaskExecutor()

    @pytest.mark.asyncio
    async def test_execute_task_fallback_path(self):
        """Test task execution fallback path (no real task modules)."""
        result = await self.executor.execute_task("unknown_task", "test_input")
        
        assert result["task"] == "unknown_task"
        assert result["agent"] == "python-specialist"
        assert result["status"] == "success"
        assert "test_input" in result["description"]
        assert "Completed unknown_task via python-specialist" in result["output"]

    @pytest.mark.asyncio
    async def test_execute_task_no_input(self):
        """Test task execution without input data."""
        result = await self.executor.execute_task("plan")
        
        assert result["task"] == "plan"
        assert result["agent"] == "master-orchestrator"
        assert result["description"] == "Execute plan"

    @pytest.mark.asyncio
    async def test_execute_task_with_router_facade(self):
        """Test task execution with router facade."""
        # Mock router facade and agent factory
        mock_router = Mock()
        mock_factory = Mock()
        mock_decision = Mock()
        mock_agent = Mock()
        mock_agent.role = "routed-agent"
        mock_decision.selected_agent = mock_agent
        mock_decision.domain = "test_domain"
        mock_decision.tier = 2
        mock_decision.mode = "hierarchical"
        mock_decision.scores = {"test": 0.9}
        mock_decision.top_candidates = [mock_agent]
        
        mock_router.route.return_value = mock_decision
        mock_factory.create_extended_agents.return_value = [mock_agent]
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            executor = CLITaskExecutor(
                router_facade=mock_router,
                agent_factory=mock_factory
            )
        
        result = await executor.execute_task("test_task", "input_data")
        
        # Verify router was called
        mock_router.route.assert_called_once()
        call_args = mock_router.route.call_args
        task_obj = call_args[0][0]
        agents = call_args[0][1]
        
        assert task_obj["name"] == "test_task"
        assert task_obj["description"] == "input_data"
        assert agents == [mock_agent]
        
        # Verify result includes routing info
        assert result["agent"] == "routed-agent"
        assert "routing" in result
        assert result["routing"]["domain"] == "test_domain"
        assert result["routing"]["tier"] == 2

    @pytest.mark.asyncio
    async def test_execute_task_router_fallback(self):
        """Test router facade fallback when agent factory fails."""
        mock_router = Mock()
        mock_factory = Mock()
        mock_factory.create_extended_agents.side_effect = Exception("Factory error")
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            executor = CLITaskExecutor(
                router_facade=mock_router,
                agent_factory=mock_factory
            )
        
        result = await executor.execute_task("test_task")
        
        # Should fallback to heuristic mapping
        assert result["agent"] == "unit-test-engineer"  # "test" in task name maps to unit-test-engineer

    @pytest.mark.asyncio
    async def test_execute_task_import_error_fallback(self):
        """Test task execution falls back when imports fail."""
        # This tests the actual behavior when task modules can't be imported
        result = await self.executor.execute_task("nonexistent_task", "input_data")

        # Should fallback to the standard result format
        assert result["task"] == "nonexistent_task"
        assert result["status"] == "success"
        assert "input_data" in result["description"]


class TestLifecycleCallbacks:
    """Test lifecycle callback integration."""

    def setup_method(self):
        """Set up test executor with lifecycle."""
        self.mock_lifecycle = Mock()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.executor = CLITaskExecutor(lifecycle=self.mock_lifecycle)

    @pytest.mark.asyncio
    async def test_lifecycle_before_task_callback(self):
        """Test before task lifecycle callback."""
        await self.executor.execute_task("test_task", "input_data")
        
        self.mock_lifecycle.on_before_task.assert_called_once_with("test_task", "input_data")

    @pytest.mark.asyncio
    async def test_lifecycle_after_task_callback_fallback(self):
        """Test after task lifecycle callback in fallback path."""
        await self.executor.execute_task("test_task", "input_data")
        
        self.mock_lifecycle.on_after_task.assert_called_once()
        call_args = self.mock_lifecycle.on_after_task.call_args
        assert call_args[0][0] == "test_task"  # task_name
        assert isinstance(call_args[0][1], dict)  # result

    @pytest.mark.asyncio
    async def test_lifecycle_after_task_callback_normal_flow(self):
        """Test after task lifecycle callback in normal execution flow."""
        await self.executor.execute_task("test_task", "input_data")

        # Should be called once in the fallback path
        assert self.mock_lifecycle.on_after_task.call_count == 1
        call_args = self.mock_lifecycle.on_after_task.call_args
        assert call_args[0][0] == "test_task"
        assert isinstance(call_args[0][1], dict)  # result dict

    @pytest.mark.asyncio
    async def test_lifecycle_callback_exception_handling(self):
        """Test that lifecycle callback exceptions are handled gracefully."""
        self.mock_lifecycle.on_before_task.side_effect = Exception("Callback error")
        self.mock_lifecycle.on_after_task.side_effect = Exception("Callback error")
        
        # Should not raise exception
        result = await self.executor.execute_task("test_task")
        assert result["status"] == "success"


class TestTaskMappingMethods:
    """Test task mapping utility methods."""

    def setup_method(self):
        """Set up test executor."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.executor = CLITaskExecutor()

    def test_add_task_mapping(self):
        """Test adding custom task mapping."""
        self.executor.add_task_mapping("custom_task", "custom-agent")
        
        assert self.executor.task_to_agent_map["custom_task"] == "custom-agent"
        agent = self.executor._get_agent_for_task("custom_task")
        assert agent == "custom-agent"

    def test_get_task_mapping(self):
        """Test getting task mapping copy."""
        original_mapping = self.executor.task_to_agent_map
        returned_mapping = self.executor.get_task_mapping()
        
        # Should be a copy, not the same object
        assert returned_mapping == original_mapping
        assert returned_mapping is not original_mapping
        
        # Modifying returned mapping shouldn't affect original
        returned_mapping["new_task"] = "new-agent"
        assert "new_task" not in self.executor.task_to_agent_map


class TestErrorHandling:
    """Test error handling scenarios."""

    def setup_method(self):
        """Set up test executor."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.executor = CLITaskExecutor()

    @pytest.mark.asyncio
    async def test_graceful_fallback_behavior(self):
        """Test that executor falls back gracefully when task modules are unavailable."""
        # Test with a task name that doesn't exist in any module
        result = await self.executor.execute_task("completely_unknown_task")

        # Should fallback gracefully to the standard result format
        assert result["status"] == "success"
        assert result["agent"] == "python-specialist"  # fallback agent
        assert result["task"] == "completely_unknown_task"

    @pytest.mark.asyncio
    async def test_async_sleep_execution(self):
        """Test that the async sleep is executed in fallback path."""
        import time
        start_time = time.time()

        await self.executor.execute_task("test_task")

        end_time = time.time()
        # Should have taken at least 0.01 seconds due to asyncio.sleep(0.01)
        assert end_time - start_time >= 0.01


class TestEdgeCases:
    """Test edge cases and additional scenarios."""

    def setup_method(self):
        """Set up test executor."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.executor = CLITaskExecutor()

    @pytest.mark.asyncio
    async def test_none_input_data(self):
        """Test execution with None input data."""
        result = await self.executor.execute_task("test_task", None)

        assert result["task"] == "test_task"
        assert result["description"] == "Execute test_task"  # No input mentioned

    @pytest.mark.asyncio
    async def test_empty_string_input_data(self):
        """Test execution with empty string input data."""
        result = await self.executor.execute_task("test_task", "")

        assert result["task"] == "test_task"
        # Empty string is falsy, so no input is mentioned
        assert result["description"] == "Execute test_task"

    @pytest.mark.asyncio
    async def test_complex_input_data(self):
        """Test execution with complex input data."""
        complex_input = {"key": "value", "nested": {"data": [1, 2, 3]}}
        result = await self.executor.execute_task("test_task", complex_input)

        assert result["task"] == "test_task"
        assert str(complex_input) in result["description"]

    def test_router_facade_without_agent_factory(self):
        """Test router facade behavior when agent factory is None."""
        mock_router = Mock()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            executor = CLITaskExecutor(router_facade=mock_router, agent_factory=None)

        # Should not call router when agent_factory is None
        assert executor.router_facade is mock_router
        assert executor.agent_factory is None

    def test_agent_factory_without_router_facade(self):
        """Test agent factory behavior when router facade is None."""
        mock_factory = Mock()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            executor = CLITaskExecutor(router_facade=None, agent_factory=mock_factory)

        # Should not use factory when router_facade is None
        assert executor.router_facade is None
        assert executor.agent_factory is mock_factory

    @pytest.mark.asyncio
    async def test_router_decision_without_selected_agent_role(self):
        """Test router decision when selected agent has no role attribute."""
        mock_router = Mock()
        mock_factory = Mock()
        mock_decision = Mock()
        mock_agent = Mock(spec=[])  # Agent without role attribute
        mock_decision.selected_agent = mock_agent
        mock_decision.domain = "test_domain"
        mock_decision.tier = 2
        mock_decision.mode = "hierarchical"
        mock_decision.scores = {}
        mock_decision.top_candidates = []

        mock_router.route.return_value = mock_decision
        mock_factory.create_extended_agents.return_value = [mock_agent]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            executor = CLITaskExecutor(
                router_facade=mock_router,
                agent_factory=mock_factory
            )

        result = await executor.execute_task("test_task")

        # Should fallback to heuristic mapping when agent has no role
        assert result["agent"] == "unit-test-engineer"  # "test" maps to this

    @pytest.mark.asyncio
    async def test_agent_factory_fallback_methods(self):
        """Test agent factory fallback when create_extended_agents doesn't exist."""
        mock_router = Mock()
        mock_factory = Mock()
        mock_agent = Mock()
        mock_agent.role = "fallback-agent"
        mock_decision = Mock()
        mock_decision.selected_agent = mock_agent
        mock_decision.domain = "test"
        mock_decision.tier = 1
        mock_decision.mode = "simple"
        mock_decision.scores = {}
        mock_decision.top_candidates = []

        # Remove create_extended_agents, only have create_default_agents
        delattr(mock_factory, 'create_extended_agents') if hasattr(mock_factory, 'create_extended_agents') else None
        mock_factory.create_default_agents.return_value = [mock_agent]

        mock_router.route.return_value = mock_decision

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            executor = CLITaskExecutor(
                router_facade=mock_router,
                agent_factory=mock_factory
            )

        result = await executor.execute_task("test_task")

        # Should use create_default_agents as fallback
        assert result["agent"] == "fallback-agent"
