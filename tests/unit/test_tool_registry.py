"""Unit tests for tool registry system."""

import pytest
from src.tool_registry import ToolRegistry, ToolMetadata, default_registry
import src.tools  # Import to trigger tool registration


class TestToolMetadata:
    """Test ToolMetadata dataclass."""

    def test_metadata_creation(self):
        """Test creating tool metadata."""
        def dummy_func(x: int) -> int:
            return x * 2

        metadata = ToolMetadata(
            name="test_tool",
            function=dummy_func,
            description="Test description",
            parameters={"x": {"type": "integer"}},
            required_params=["x"]
        )

        assert metadata.name == "test_tool"
        assert metadata.function == dummy_func
        assert metadata.description == "Test description"
        assert "x" in metadata.parameters
        assert metadata.required_params == ["x"]

    def test_to_openai_format(self):
        """Test converting metadata to OpenAI format."""
        def dummy_func(x: int) -> int:
            return x * 2

        metadata = ToolMetadata(
            name="test_tool",
            function=dummy_func,
            description="Test description",
            parameters={"x": {"type": "integer", "description": "Input value"}},
            required_params=["x"]
        )

        openai_format = metadata.to_openai_format()

        assert openai_format["type"] == "function"
        assert openai_format["function"]["name"] == "test_tool"
        assert openai_format["function"]["description"] == "Test description"
        assert "x" in openai_format["function"]["parameters"]["properties"]
        assert openai_format["function"]["parameters"]["required"] == ["x"]


class TestToolRegistry:
    """Test ToolRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create fresh registry for each test."""
        return ToolRegistry()

    @pytest.fixture
    def sample_tool(self):
        """Sample tool function for testing."""
        def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b
        return add

    def test_registry_initialization(self, registry):
        """Test registry starts empty."""
        assert len(registry) == 0
        assert registry.list_tools() == []

    def test_register_function_directly(self, registry, sample_tool):
        """Test registering a function directly."""
        registry.register_function(
            function=sample_tool,
            name="add",
            description="Add two numbers",
            parameters={
                "a": {"type": "integer"},
                "b": {"type": "integer"}
            },
            required=["a", "b"]
        )

        assert len(registry) == 1
        assert "add" in registry
        assert registry.get_tool("add") == sample_tool

    def test_register_with_decorator(self, registry):
        """Test registering with decorator pattern."""
        @registry.register(
            name="multiply",
            description="Multiply two numbers",
            parameters={
                "x": {"type": "integer"},
                "y": {"type": "integer"}
            },
            required=["x", "y"]
        )
        def multiply(x: int, y: int) -> int:
            return x * y

        assert "multiply" in registry
        assert registry.execute_tool("multiply", x=3, y=4) == 12

    def test_get_tool(self, registry, sample_tool):
        """Test retrieving tool by name."""
        registry.register_function(
            function=sample_tool,
            name="add",
            description="Add",
            parameters={},
            required=[]
        )

        tool = registry.get_tool("add")
        assert tool is not None
        assert tool(2, 3) == 5

    def test_get_tool_not_found(self, registry):
        """Test retrieving nonexistent tool."""
        tool = registry.get_tool("nonexistent")
        assert tool is None

    def test_get_metadata(self, registry, sample_tool):
        """Test retrieving tool metadata."""
        registry.register_function(
            function=sample_tool,
            name="add",
            description="Add numbers",
            parameters={"a": {"type": "integer"}},
            required=["a"]
        )

        metadata = registry.get_metadata("add")
        assert metadata is not None
        assert metadata.name == "add"
        assert metadata.description == "Add numbers"
        assert "a" in metadata.parameters

    def test_list_tools(self, registry):
        """Test listing all tool names."""
        def tool1():
            pass

        def tool2():
            pass

        registry.register_function(tool1, "tool1", "desc1", {})
        registry.register_function(tool2, "tool2", "desc2", {})

        tools = registry.list_tools()
        assert len(tools) == 2
        assert "tool1" in tools
        assert "tool2" in tools

    def test_get_openai_tools(self, registry, sample_tool):
        """Test getting all tools in OpenAI format."""
        registry.register_function(
            function=sample_tool,
            name="add",
            description="Add numbers",
            parameters={"a": {"type": "integer"}, "b": {"type": "integer"}},
            required=["a", "b"]
        )

        openai_tools = registry.get_openai_tools()

        assert len(openai_tools) == 1
        assert openai_tools[0]["type"] == "function"
        assert openai_tools[0]["function"]["name"] == "add"
        assert openai_tools[0]["function"]["description"] == "Add numbers"

    def test_execute_tool(self, registry, sample_tool):
        """Test executing a registered tool."""
        registry.register_function(
            function=sample_tool,
            name="add",
            description="Add",
            parameters={"a": {"type": "integer"}, "b": {"type": "integer"}},
            required=["a", "b"]
        )

        result = registry.execute_tool("add", a=5, b=7)
        assert result == 12

    def test_execute_tool_not_found(self, registry):
        """Test executing nonexistent tool raises error."""
        with pytest.raises(ValueError, match="not found"):
            registry.execute_tool("nonexistent", x=1)

    def test_execute_tool_missing_required_param(self, registry):
        """Test executing tool with missing required param."""
        def requires_x(x: int) -> int:
            return x * 2

        registry.register_function(
            function=requires_x,
            name="double",
            description="Double a number",
            parameters={"x": {"type": "integer"}},
            required=["x"]
        )

        with pytest.raises(TypeError, match="Missing required parameter"):
            registry.execute_tool("double")  # Missing x

    def test_validate_tool(self, registry, sample_tool):
        """Test tool validation."""
        registry.register_function(
            function=sample_tool,
            name="add",
            description="Add",
            parameters={"a": {"type": "integer"}, "b": {"type": "integer"}},
            required=["a", "b"]
        )

        assert registry.validate_tool("add") is True
        assert registry.validate_tool("nonexistent") is False

    def test_validate_tool_invalid_required(self, registry):
        """Test validation fails for invalid required params."""
        def dummy():
            pass

        registry.register_function(
            function=dummy,
            name="invalid",
            description="Invalid tool",
            parameters={"x": {"type": "integer"}},
            required=["x", "y"]  # y not in parameters
        )

        assert registry.validate_tool("invalid") is False

    def test_contains_operator(self, registry, sample_tool):
        """Test 'in' operator for registry."""
        registry.register_function(
            function=sample_tool,
            name="add",
            description="Add",
            parameters={},
            required=[]
        )

        assert "add" in registry
        assert "nonexistent" not in registry

    def test_len_operator(self, registry):
        """Test len() operator for registry."""
        assert len(registry) == 0

        def tool1():
            pass

        registry.register_function(tool1, "tool1", "desc", {})
        assert len(registry) == 1

        def tool2():
            pass

        registry.register_function(tool2, "tool2", "desc", {})
        assert len(registry) == 2

    def test_repr(self, registry):
        """Test string representation."""
        repr_str = repr(registry)
        assert "ToolRegistry" in repr_str
        assert "tools=0" in repr_str

    def test_multiple_tools(self, registry):
        """Test registering and using multiple tools."""
        @registry.register(
            name="add",
            description="Add",
            parameters={"a": {"type": "integer"}, "b": {"type": "integer"}},
            required=["a", "b"]
        )
        def add(a: int, b: int) -> int:
            return a + b

        @registry.register(
            name="multiply",
            description="Multiply",
            parameters={"x": {"type": "integer"}, "y": {"type": "integer"}},
            required=["x", "y"]
        )
        def multiply(x: int, y: int) -> int:
            return x * y

        assert len(registry) == 2
        assert registry.execute_tool("add", a=2, b=3) == 5
        assert registry.execute_tool("multiply", x=2, y=3) == 6


class TestDefaultRegistry:
    """Test the global default_registry singleton."""

    def test_default_registry_exists(self):
        """Test that default registry is available."""
        assert default_registry is not None
        assert isinstance(default_registry, ToolRegistry)

    def test_default_registry_has_tools(self):
        """Test that default registry has registered tools from tools.py."""
        # These should be registered by tools.py
        expected_tools = ["run_command", "read_file_content", "write_file_content", "list_files"]

        for tool_name in expected_tools:
            assert tool_name in default_registry

    def test_default_registry_openai_format(self):
        """Test that default registry provides OpenAI format tools."""
        openai_tools = default_registry.get_openai_tools()

        assert len(openai_tools) >= 4  # At least the 4 core tools
        assert all(tool["type"] == "function" for tool in openai_tools)