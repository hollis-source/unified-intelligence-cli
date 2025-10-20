"""Workflow Environment Interface - Configuration abstraction for DSL runtime.

Addresses Sprint 5 P1-2: DSL Runtime Coupling
- Extracts environment configuration from execution logic
- Enables dependency injection for all DSL dependencies
- Follows Interface Segregation Principle (ISP)

Clean Architecture: Interface layer (contracts between use cases and adapters).
SOLID: ISP - minimal interface, DIP - depend on abstractions not concretions.
"""

from typing import Protocol, Optional, runtime_checkable
from abc import ABC, abstractmethod


@runtime_checkable
class TaskExecutor(Protocol):
    """Protocol for task execution (existing interface)."""

    async def execute(self, task_name: str, context: Optional[dict] = None):
        """Execute a task by name with optional context."""
        ...


@runtime_checkable
class Parser(Protocol):
    """Protocol for DSL parsing."""

    def parse(self, dsl_text: str):
        """Parse DSL text to AST."""
        ...


@runtime_checkable
class HTNCompiler(Protocol):
    """Protocol for HTN compilation."""

    def compile(self, ast_node):
        """Compile AST node to HTN structure."""
        ...


class IWorkflowEnvironment(ABC):
    """Abstract interface for DSL workflow environment configuration.

    Provides all dependencies needed by DSL executors without coupling
    to concrete implementations. Enables:
    - Dependency Injection (DIP)
    - Easy testing with mocks
    - Flexible configuration (dev, test, prod)
    - Separation of concerns (SRP)

    Example:
        # Production environment
        env = ProductionWorkflowEnvironment(
            router_facade=router,
            agent_factory=factory,
            lifecycle=callbacks
        )

        # Test environment
        env = TestWorkflowEnvironment(
            task_executor=MockTaskExecutor(),
            parser=MockParser()
        )

        # Use in executor
        executor = LifecycleWorkflowExecutor(environment=env)
    """

    @abstractmethod
    def get_task_executor(self) -> TaskExecutor:
        """
        Get task executor instance.

        Returns:
            Configured task executor (e.g., CLITaskExecutor with router/factory/lifecycle)
        """
        pass

    @abstractmethod
    def get_parser(self) -> Parser:
        """
        Get DSL parser instance.

        Returns:
            DSL parser for converting text to AST
        """
        pass

    @abstractmethod
    def get_htn_compiler(self) -> HTNCompiler:
        """
        Get HTN compiler instance.

        Returns:
            HTN compiler for converting AST to HTN structures
        """
        pass


class DefaultWorkflowEnvironment(IWorkflowEnvironment):
    """Default workflow environment with standard implementations.

    Uses concrete implementations directly - suitable for simple use cases
    where configuration isn't needed. For production, use configured environment
    with router_facade, lifecycle, etc.

    Example:
        env = DefaultWorkflowEnvironment()
        executor = LifecycleWorkflowExecutor(environment=env)
    """

    def __init__(self):
        """Initialize default environment with standard implementations."""
        self._task_executor = None
        self._parser = None
        self._htn_compiler = None

    def get_task_executor(self) -> TaskExecutor:
        """Get default task executor (CLITaskExecutor with no config)."""
        if self._task_executor is None:
            from src.dsl.adapters.cli_task_executor import CLITaskExecutor
            self._task_executor = CLITaskExecutor()
        return self._task_executor

    def get_parser(self) -> Parser:
        """Get default parser."""
        if self._parser is None:
            from src.dsl.adapters.parser import Parser as ParserImpl
            self._parser = ParserImpl()
        return self._parser

    def get_htn_compiler(self) -> HTNCompiler:
        """Get default HTN compiler."""
        if self._htn_compiler is None:
            from src.dsl.adapters.htn_compiler import HTNCompiler as HTNCompilerImpl
            self._htn_compiler = HTNCompilerImpl()
        return self._htn_compiler


class ConfiguredWorkflowEnvironment(IWorkflowEnvironment):
    """Configured workflow environment with explicit dependencies.

    Accepts pre-configured instances via constructor - ideal for production
    where you want to inject router, factory, lifecycle callbacks, etc.

    Example:
        from src.dsl.adapters.cli_task_executor import CLITaskExecutor
        from src.routing.router_facade import RouterFacade
        from src.factories.agent_factory import AgentFactory

        # Create configured components
        router = RouterFacade(...)
        factory = AgentFactory(...)
        lifecycle = LifecycleCallbacks(...)
        task_executor = CLITaskExecutor(
            router_facade=router,
            agent_factory=factory,
            lifecycle=lifecycle
        )

        # Create environment
        env = ConfiguredWorkflowEnvironment(task_executor=task_executor)

        # Use in executor
        executor = LifecycleWorkflowExecutor(environment=env)
    """

    def __init__(
        self,
        task_executor: Optional[TaskExecutor] = None,
        parser: Optional[Parser] = None,
        htn_compiler: Optional[HTNCompiler] = None
    ):
        """
        Initialize configured environment with explicit dependencies.

        Args:
            task_executor: Pre-configured task executor (optional)
            parser: Pre-configured parser (optional)
            htn_compiler: Pre-configured HTN compiler (optional)

        Note: If dependencies are None, will fall back to defaults.
        """
        self._task_executor = task_executor
        self._parser = parser
        self._htn_compiler = htn_compiler

    def get_task_executor(self) -> TaskExecutor:
        """Get configured or default task executor."""
        if self._task_executor is None:
            from src.dsl.adapters.cli_task_executor import CLITaskExecutor
            self._task_executor = CLITaskExecutor()
        return self._task_executor

    def get_parser(self) -> Parser:
        """Get configured or default parser."""
        if self._parser is None:
            from src.dsl.adapters.parser import Parser as ParserImpl
            self._parser = ParserImpl()
        return self._parser

    def get_htn_compiler(self) -> HTNCompiler:
        """Get configured or default HTN compiler."""
        if self._htn_compiler is None:
            from src.dsl.adapters.htn_compiler import HTNCompiler as HTNCompilerImpl
            self._htn_compiler = HTNCompilerImpl()
        return self._htn_compiler
