"""Tests for Sprint 5 P1-2: DSL Runtime Coupling refactoring.

Validates that:
1. Environment configuration interface works correctly
2. Dependency injection is properly implemented
3. Executors can use mock environments for testing
4. Backward compatibility is maintained
5. No direct coupling to concrete implementations remains
"""

import pytest
from unittest.mock import Mock, AsyncMock
from pathlib import Path

from src.dsl.interface.workflow_environment import (
    IWorkflowEnvironment,
    DefaultWorkflowEnvironment,
    ConfiguredWorkflowEnvironment
)
from src.dsl.use_cases.lifecycle_executor import LifecycleWorkflowExecutor
from src.dsl.use_cases.htn_workflow_executor import HTNWorkflowExecutor
from src.dsl.use_cases.morphism_workflow_executor import MorphismWorkflowExecutor


class MockTaskExecutor:
    """Mock task executor for testing."""

    async def execute(self, task_name: str, context=None):
        return f"Executed: {task_name}"


class MockParser:
    """Mock parser for testing."""

    def parse(self, dsl_text: str):
        return {"type": "mock_ast", "text": dsl_text}


class MockHTNCompiler:
    """Mock HTN compiler for testing."""

    def compile(self, ast_node):
        from src.entity.htn import HTNNode
        return HTNNode(task_id="mock_task", is_primitive_node=True)


class MockWorkflowEnvironment(IWorkflowEnvironment):
    """Mock environment for testing with all dependencies mocked."""

    def __init__(self):
        self._task_executor = MockTaskExecutor()
        self._parser = MockParser()
        self._htn_compiler = MockHTNCompiler()
        self.task_executor_calls = 0
        self.parser_calls = 0
        self.htn_compiler_calls = 0

    def get_task_executor(self):
        self.task_executor_calls += 1
        return self._task_executor

    def get_parser(self):
        self.parser_calls += 1
        return self._parser

    def get_htn_compiler(self):
        self.htn_compiler_calls += 1
        return self._htn_compiler


class TestWorkflowEnvironmentInterface:
    """Test the IWorkflowEnvironment interface and implementations."""

    def test_default_environment_provides_dependencies(self):
        """DefaultWorkflowEnvironment should provide all required dependencies."""
        env = DefaultWorkflowEnvironment()

        task_executor = env.get_task_executor()
        parser = env.get_parser()
        htn_compiler = env.get_htn_compiler()

        assert task_executor is not None
        assert parser is not None
        assert htn_compiler is not None

    def test_default_environment_returns_same_instances(self):
        """DefaultWorkflowEnvironment should return same instances (singleton pattern)."""
        env = DefaultWorkflowEnvironment()

        task_executor1 = env.get_task_executor()
        task_executor2 = env.get_task_executor()

        assert task_executor1 is task_executor2

    def test_configured_environment_with_custom_dependencies(self):
        """ConfiguredWorkflowEnvironment should use provided dependencies."""
        mock_executor = MockTaskExecutor()
        mock_parser = MockParser()
        mock_compiler = MockHTNCompiler()

        env = ConfiguredWorkflowEnvironment(
            task_executor=mock_executor,
            parser=mock_parser,
            htn_compiler=mock_compiler
        )

        assert env.get_task_executor() is mock_executor
        assert env.get_parser() is mock_parser
        assert env.get_htn_compiler() is mock_compiler

    def test_configured_environment_falls_back_to_defaults(self):
        """ConfiguredWorkflowEnvironment should fall back to defaults when not provided."""
        env = ConfiguredWorkflowEnvironment()  # No dependencies provided

        task_executor = env.get_task_executor()
        parser = env.get_parser()
        htn_compiler = env.get_htn_compiler()

        assert task_executor is not None
        assert parser is not None
        assert htn_compiler is not None

    def test_mock_environment_tracks_calls(self):
        """MockWorkflowEnvironment should track dependency access."""
        env = MockWorkflowEnvironment()

        assert env.task_executor_calls == 0
        env.get_task_executor()
        assert env.task_executor_calls == 1

        assert env.parser_calls == 0
        env.get_parser()
        assert env.parser_calls == 1


class TestLifecycleExecutorDependencyInjection:
    """Test LifecycleWorkflowExecutor with dependency injection."""

    def test_executor_with_mock_environment(self):
        """LifecycleWorkflowExecutor should work with mock environment."""
        env = MockWorkflowEnvironment()
        executor = LifecycleWorkflowExecutor(environment=env)

        # Verify dependencies were retrieved from environment
        assert env.task_executor_calls == 1
        assert env.parser_calls == 1

        # Verify executor has correct dependencies
        assert isinstance(executor.task_executor, MockTaskExecutor)
        assert isinstance(executor.parser, MockParser)

    def test_executor_without_environment_uses_defaults(self):
        """LifecycleWorkflowExecutor should use defaults when no environment provided."""
        executor = LifecycleWorkflowExecutor()

        # Should have environment (created internally)
        assert executor.environment is not None
        assert executor.task_executor is not None
        assert executor.parser is not None

    def test_executor_backward_compatibility_with_task_executor_param(self):
        """LifecycleWorkflowExecutor should support legacy task_executor parameter."""
        mock_executor = MockTaskExecutor()
        executor = LifecycleWorkflowExecutor(task_executor=mock_executor)

        # Should wrap in environment
        assert executor.environment is not None
        assert executor.task_executor is mock_executor

    def test_executor_backward_compatibility_with_parser_param(self):
        """LifecycleWorkflowExecutor should support legacy parser parameter."""
        mock_parser = MockParser()
        executor = LifecycleWorkflowExecutor(parser=mock_parser)

        # Should wrap in environment
        assert executor.environment is not None
        assert executor.parser is mock_parser

    def test_executor_environment_takes_precedence_over_legacy_params(self):
        """Environment parameter should take precedence over legacy parameters."""
        env_executor = MockTaskExecutor()
        legacy_executor = MockTaskExecutor()

        env = ConfiguredWorkflowEnvironment(task_executor=env_executor)
        executor = LifecycleWorkflowExecutor(
            environment=env,
            task_executor=legacy_executor  # Should be ignored
        )

        assert executor.task_executor is env_executor


class TestHTNExecutorDependencyInjection:
    """Test HTNWorkflowExecutor with dependency injection."""

    def test_htn_executor_with_mock_environment(self):
        """HTNWorkflowExecutor should work with mock environment."""
        env = MockWorkflowEnvironment()
        executor = HTNWorkflowExecutor(environment=env)

        # Verify dependencies were retrieved from environment
        assert env.task_executor_calls == 1
        assert env.parser_calls == 1
        assert env.htn_compiler_calls == 1

        # Verify executor has correct dependencies
        assert isinstance(executor.task_executor, MockTaskExecutor)
        assert isinstance(executor.parser, MockParser)
        assert isinstance(executor.htn_compiler, MockHTNCompiler)

    def test_htn_executor_without_environment_uses_defaults(self):
        """HTNWorkflowExecutor should use defaults when no environment provided."""
        executor = HTNWorkflowExecutor()

        # Should have environment (created internally or inherited from parent)
        assert executor.environment is not None
        assert executor.task_executor is not None
        assert executor.parser is not None
        assert executor.htn_compiler is not None

    def test_htn_executor_backward_compatibility(self):
        """HTNWorkflowExecutor should support legacy parameters."""
        mock_executor = MockTaskExecutor()
        mock_parser = MockParser()
        executor = HTNWorkflowExecutor(
            task_executor=mock_executor,
            parser=mock_parser
        )

        # Should wrap in environment
        assert executor.environment is not None
        assert executor.task_executor is mock_executor
        assert executor.parser is mock_parser


class TestMorphismExecutorDependencyInjection:
    """Test MorphismWorkflowExecutor with dependency injection."""

    def test_morphism_executor_with_mock_environment(self):
        """MorphismWorkflowExecutor should work with mock environment."""
        env = MockWorkflowEnvironment()
        executor = MorphismWorkflowExecutor(environment=env)

        # Verify dependencies were retrieved from environment
        assert env.task_executor_calls == 1
        assert env.parser_calls == 1
        assert env.htn_compiler_calls == 1

        # Verify executor has correct dependencies
        assert isinstance(executor.task_executor, MockTaskExecutor)
        assert isinstance(executor.parser, MockParser)
        assert isinstance(executor.htn_compiler, MockHTNCompiler)

    def test_morphism_executor_with_transformations(self):
        """MorphismWorkflowExecutor should accept transformations parameter."""
        env = MockWorkflowEnvironment()
        mock_transformations = [Mock()]

        executor = MorphismWorkflowExecutor(
            environment=env,
            transformations=mock_transformations
        )

        assert executor.transformations == mock_transformations

    def test_morphism_executor_backward_compatibility(self):
        """MorphismWorkflowExecutor should support legacy parameters with transformations."""
        mock_executor = MockTaskExecutor()
        mock_parser = MockParser()
        mock_transformations = [Mock()]

        executor = MorphismWorkflowExecutor(
            task_executor=mock_executor,
            parser=mock_parser,
            transformations=mock_transformations
        )

        # Should wrap in environment
        assert executor.environment is not None
        assert executor.task_executor is mock_executor
        assert executor.parser is mock_parser
        assert executor.transformations == mock_transformations


class TestDecouplingValidation:
    """Validate that coupling is removed and SOLID principles are followed."""

    def test_no_direct_cliTaskExecutor_instantiation(self):
        """Executors should not directly instantiate CLITaskExecutor."""
        # This test verifies the refactoring by checking that executors
        # use the environment to get dependencies instead of creating them

        env = MockWorkflowEnvironment()

        # Create all executors with mock environment
        lifecycle_exec = LifecycleWorkflowExecutor(environment=env)
        htn_exec = HTNWorkflowExecutor(environment=env)
        morphism_exec = MorphismWorkflowExecutor(environment=env)

        # All should use mock executor, not CLITaskExecutor
        assert isinstance(lifecycle_exec.task_executor, MockTaskExecutor)
        assert isinstance(htn_exec.task_executor, MockTaskExecutor)
        assert isinstance(morphism_exec.task_executor, MockTaskExecutor)

    def test_dependency_inversion_principle(self):
        """Executors should depend on abstractions (IWorkflowEnvironment), not concretions."""
        # By accepting IWorkflowEnvironment, executors follow DIP

        custom_env = MockWorkflowEnvironment()
        executor = LifecycleWorkflowExecutor(environment=custom_env)

        # Executor should work with any IWorkflowEnvironment implementation
        assert executor.environment is custom_env
        assert isinstance(executor.environment, IWorkflowEnvironment)

    def test_interface_segregation_principle(self):
        """IWorkflowEnvironment should provide minimal, focused interface."""
        # IWorkflowEnvironment has only 3 methods: get_task_executor, get_parser, get_htn_compiler
        # This follows ISP - clients only depend on methods they use

        env = MockWorkflowEnvironment()

        # LifecycleExecutor only needs task_executor and parser
        lifecycle_exec = LifecycleWorkflowExecutor(environment=env)
        assert env.task_executor_calls == 1
        assert env.parser_calls == 1
        assert env.htn_compiler_calls == 0  # Not used by LifecycleExecutor

        # HTNExecutor needs all three
        htn_exec = HTNWorkflowExecutor(environment=env)
        assert env.htn_compiler_calls == 1  # Now used

    def test_single_responsibility_principle(self):
        """Executors should focus on execution, not configuration/construction."""
        # By using environment, executors delegate dependency management

        env = MockWorkflowEnvironment()
        executor = LifecycleWorkflowExecutor(environment=env)

        # Executor focuses on workflow execution, not creating dependencies
        # Environment handles dependency creation/configuration
        assert executor.environment is env
        assert executor.task_executor is env.get_task_executor()


class TestProductionUsagePatterns:
    """Test realistic production usage patterns."""

    def test_production_environment_with_configured_task_executor(self):
        """Simulate production setup with fully configured task executor."""
        # Simulate production task executor with router, factory, lifecycle
        mock_router = Mock()
        mock_factory = Mock()
        mock_lifecycle = Mock()

        from src.dsl.adapters.cli_task_executor import CLITaskExecutor
        configured_executor = CLITaskExecutor(
            router_facade=mock_router,
            agent_factory=mock_factory,
            lifecycle=mock_lifecycle
        )

        # Create environment with configured executor
        env = ConfiguredWorkflowEnvironment(task_executor=configured_executor)

        # Use in executor
        executor = LifecycleWorkflowExecutor(environment=env)

        # Verify configuration is preserved
        assert executor.task_executor.router_facade is mock_router
        assert executor.task_executor.agent_factory is mock_factory
        assert executor.task_executor.lifecycle is mock_lifecycle

    def test_multiple_executors_share_same_environment(self):
        """Multiple executors can share the same configured environment."""
        env = MockWorkflowEnvironment()

        lifecycle_exec = LifecycleWorkflowExecutor(environment=env)
        htn_exec = HTNWorkflowExecutor(environment=env)

        # Both should use same environment instance
        assert lifecycle_exec.environment is env
        assert htn_exec.environment is env

        # Both should get same task executor instance
        assert lifecycle_exec.task_executor is htn_exec.task_executor
