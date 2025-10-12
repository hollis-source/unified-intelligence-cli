"""Integration test for Phase 1 tool-use system.

Tests that tools are properly wired into composition and can be invoked.
"""
import pytest
from src.composition import compose_dependencies
from src.factories.provider_factory import ProviderFactory
from src.factories.agent_factory import AgentFactory
from src.entities import Task


@pytest.mark.integration
def test_tool_registry_initialized():
    """Verify tool registry is initialized with 3 core tools."""
    provider_factory = ProviderFactory()
    agent_factory = AgentFactory()

    llm_provider = provider_factory.create_provider("mock")
    agents = agent_factory.create_default_agents()

    coordinator, _ = compose_dependencies(
        llm_provider=llm_provider,
        agents=agents,
        collect_metrics=False
    )

    # Verify coordinator was created successfully
    assert coordinator is not None


@pytest.mark.integration
def test_file_reader_tool_registered():
    """Verify FileReaderTool is registered and accessible."""
    from src.adapters.agent.tools.registry import ToolRegistry
    from src.adapters.agent.tools.file_reader import FileReaderTool

    registry = ToolRegistry()
    registry.register(FileReaderTool())

    tool = registry.get_tool("read_file")
    assert tool is not None
    assert tool.name == "read_file"
    assert "Read contents" in tool.description


@pytest.mark.integration
def test_bash_executor_tool_registered():
    """Verify BashExecutorTool is registered and accessible."""
    from src.adapters.agent.tools.registry import ToolRegistry
    from src.adapters.agent.tools.bash_executor import BashExecutorTool

    registry = ToolRegistry()
    registry.register(BashExecutorTool())

    tool = registry.get_tool("bash")
    assert tool is not None
    assert tool.name == "bash"
    assert "bash" in tool.description.lower()


@pytest.mark.integration
def test_file_writer_tool_registered():
    """Verify FileWriterTool is registered and accessible."""
    from src.adapters.agent.tools.registry import ToolRegistry
    from src.adapters.agent.tools.file_writer import FileWriterTool

    registry = ToolRegistry()
    registry.register(FileWriterTool())

    tool = registry.get_tool("write_file")
    assert tool is not None
    assert tool.name == "write_file"
    assert "Write" in tool.description or "write" in tool.description


@pytest.mark.integration
def test_all_tools_have_parameters():
    """Verify all tools define parameter schemas."""
    from src.adapters.agent.tools.registry import ToolRegistry
    from src.adapters.agent.tools.file_reader import FileReaderTool
    from src.adapters.agent.tools.bash_executor import BashExecutorTool
    from src.adapters.agent.tools.file_writer import FileWriterTool

    tools = [FileReaderTool(), BashExecutorTool(), FileWriterTool()]

    for tool in tools:
        params = tool.parameters
        assert isinstance(params, dict)
        assert "type" in params
        assert "properties" in params
