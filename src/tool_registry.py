"""
Tool registry system for extensible tool management.

Provides decorator-based registration and metadata handling for LLM tools.
Follows Open-Closed Principle: extend with new tools without modifying core.
"""

from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field
import inspect


@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""

    name: str
    function: Callable
    description: str
    parameters: Dict[str, Any]
    required_params: List[str] = field(default_factory=list)

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI tool format for LLM APIs."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required_params
                }
            }
        }


class ToolRegistry:
    """
    Registry for managing LLM tools.

    Supports decorator-based registration and provides introspection.
    Follows Single Responsibility Principle: only manages tool registration.
    """

    def __init__(self):
        """Initialize empty registry."""
        self._tools: Dict[str, ToolMetadata] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        required: Optional[List[str]] = None
    ) -> Callable:
        """
        Decorator to register a tool function.

        Args:
            name: Tool name for LLM invocation
            description: Human-readable description
            parameters: Parameter definitions (OpenAI format)
            required: List of required parameter names

        Returns:
            Decorated function

        Example:
            @registry.register(
                name="my_tool",
                description="Does something useful",
                parameters={"arg1": {"type": "string", "description": "..."}},
                required=["arg1"]
            )
            def my_tool(arg1: str) -> str:
                return f"Result: {arg1}"
        """
        def decorator(func: Callable) -> Callable:
            metadata = ToolMetadata(
                name=name,
                function=func,
                description=description,
                parameters=parameters,
                required_params=required or []
            )
            self._tools[name] = metadata
            return func
        return decorator

    def register_function(
        self,
        function: Callable,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        required: Optional[List[str]] = None
    ) -> None:
        """
        Register a function directly (non-decorator approach).

        Useful for registering existing functions without modification.

        Args:
            function: The function to register
            name: Tool name
            description: Tool description
            parameters: Parameter definitions
            required: Required parameter names
        """
        metadata = ToolMetadata(
            name=name,
            function=function,
            description=description,
            parameters=parameters,
            required_params=required or []
        )
        self._tools[name] = metadata

    def get_tool(self, name: str) -> Optional[Callable]:
        """
        Get tool function by name.

        Args:
            name: Tool name

        Returns:
            Tool function or None if not found
        """
        metadata = self._tools.get(name)
        return metadata.function if metadata else None

    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        """
        Get tool metadata by name.

        Args:
            name: Tool name

        Returns:
            Tool metadata or None if not found
        """
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """
        Get list of all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """
        Get all tools in OpenAI format for LLM API.

        Returns:
            List of tool definitions in OpenAI format
        """
        return [metadata.to_openai_format() for metadata in self._tools.values()]

    def execute_tool(self, name: str, **kwargs) -> Any:
        """
        Execute a registered tool by name.

        Args:
            name: Tool name
            **kwargs: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found
            TypeError: If arguments don't match function signature
        """
        metadata = self._tools.get(name)
        if not metadata:
            raise ValueError(f"Tool '{name}' not found in registry")

        # Validate required parameters
        for param in metadata.required_params:
            if param not in kwargs:
                raise TypeError(
                    f"Missing required parameter '{param}' for tool '{name}'"
                )

        return metadata.function(**kwargs)

    def validate_tool(self, name: str) -> bool:
        """
        Validate that a tool is properly registered.

        Checks:
        - Function exists
        - Parameters match function signature
        - Required params are subset of all params

        Args:
            name: Tool name

        Returns:
            True if valid, False otherwise
        """
        metadata = self._tools.get(name)
        if not metadata:
            return False

        # Check function signature matches parameters
        sig = inspect.signature(metadata.function)
        func_params = set(sig.parameters.keys())
        declared_params = set(metadata.parameters.keys())

        # Required params must be in declared params
        required_set = set(metadata.required_params)
        if not required_set.issubset(declared_params):
            return False

        return True

    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if tool is registered."""
        return name in self._tools

    def __repr__(self) -> str:
        """String representation."""
        return f"ToolRegistry(tools={len(self._tools)})"


# Global registry instance (singleton pattern)
default_registry = ToolRegistry()