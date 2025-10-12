"""Tongyi-DeepResearch-30B adapter - Integrates llama.cpp server with Clean Architecture.

Adapter for Tongyi-DeepResearch-30B model served via llama.cpp Docker container.
Follows DIP: Implements ITextGenerator interface, hides HTTP client details.
"""

import requests
import logging
import time
import re
import json
from typing import List, Dict, Any, Optional
from src.interfaces import ITextGenerator, IToolSupportedProvider, LLMConfig

# Week 4: Debug logging for HTTP operations
logger = logging.getLogger(__name__)


class TongyiDeepResearchAdapter(IToolSupportedProvider):
    """
    Adapter for Tongyi-DeepResearch-30B via llama.cpp server.

    Architecture:
    - Clean Architecture: Adapter layer (external interface)
    - DIP: Implements ITextGenerator, hides HTTP specifics
    - SRP: Single responsibility - HTTP communication with llama.cpp

    Server: http://localhost:8080 (Docker container)
    Model: Alibaba-NLP_Tongyi-DeepResearch-30B-A3B-Q8_0.gguf (31 GB)
    """

    def __init__(
        self,
        server_url: str = "http://localhost:8080",
        timeout: int = 300
    ):
        """
        Initialize Tongyi adapter.

        Args:
            server_url: llama.cpp server URL
            timeout: Request timeout in seconds (default 5 minutes)
        """
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self._validate_server()

    def _validate_server(self) -> None:
        """Validate llama.cpp server is accessible."""
        try:
            response = requests.get(
                f"{self.server_url}/health",
                timeout=5
            )
            if response.status_code != 200:
                raise ConnectionError(
                    f"llama.cpp server unhealthy: {response.status_code}"
                )
        except requests.RequestException as e:
            raise ConnectionError(
                f"Cannot connect to llama.cpp server at {self.server_url}: {e}"
            )

    def _messages_to_prompt(
        self,
        messages: List[Dict[str, Any]]
    ) -> str:
        """
        Convert OpenAI message format to llama.cpp prompt.

        Tongyi uses Qwen chat template: <|im_start|>role\ncontent<|im_end|>

        Args:
            messages: OpenAI-style messages

        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt_parts.append(
                f"<|im_start|>{role}\n{content}<|im_end|>"
            )

        # Add assistant start token for generation
        prompt_parts.append("<|im_start|>assistant\n")

        return "\n".join(prompt_parts)

    def generate(
        self,
        messages: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None
    ) -> str:
        """
        Generate text using Tongyi-DeepResearch-30B.

        Implements ITextGenerator.generate() contract.
        Adapter pattern: Translates interface to llama.cpp API.

        Args:
            messages: Conversation messages in OpenAI format
            config: Optional LLM configuration

        Returns:
            Generated text response

        Raises:
            ConnectionError: If server is unreachable
            ValueError: If generation fails
        """
        logger.debug(f"Tongyi generate() called with {len(messages)} messages")

        # Convert messages to prompt
        prompt = self._messages_to_prompt(messages)
        logger.debug(f"Prompt length: {len(prompt)} characters")

        # Build request payload
        max_tokens = config.max_tokens if config and config.max_tokens else 512
        temperature = config.temperature if config and config.temperature else 0.7

        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": temperature,
            "stop": ["<|im_end|>"],
            "stream": False
        }

        logger.debug(f"HTTP Request: POST {self.server_url}/completion")
        logger.debug(f"Parameters: max_tokens={max_tokens}, temperature={temperature}")

        # Call llama.cpp server
        try:
            start_time = time.time()

            response = requests.post(
                f"{self.server_url}/completion",
                json=payload,
                timeout=self.timeout
            )

            elapsed_time = time.time() - start_time
            logger.debug(f"HTTP Response: {response.status_code} ({elapsed_time:.2f}s)")

            response.raise_for_status()

            result = response.json()
            content = result.get("content", "")

            logger.debug(f"Response content length: {len(content)} characters")

            if not content:
                logger.debug("Empty response from server")
                raise ValueError("Empty response from llama.cpp server")

            return content.strip()

        except requests.Timeout:
            logger.debug(f"Request timed out after {self.timeout}s")
            raise TimeoutError(
                f"Request timed out after {self.timeout}s"
            )
        except requests.RequestException as e:
            logger.debug(f"HTTP request failed: {e}")
            raise ConnectionError(
                f"HTTP request failed: {e}"
            )
        except (KeyError, ValueError) as e:
            logger.debug(f"Invalid response format: {e}")
            raise ValueError(
                f"Invalid response format: {e}"
            )
    def supports_tools(self) -> bool:
        """
        Check if this provider supports tool calling.

        Week 5: Tongyi supports tools via prompt-based approach.
        """
        return True

    def generate_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None
    ) -> Dict[str, Any]:
        """
        Generate response with tool calling capability.

        Week 5: Prompt-based tool calling implementation.
        Uses special markers for tool calls: TOOL_CALL: tool_name(args)

        Args:
            messages: Conversation messages
            tools: Tool definitions in OpenAI format
            config: Optional configuration

        Returns:
            Dict with response, tool_calls, tool_results
        """
        logger.debug(f"generate_with_tools called with {len(tools)} tools")

        # Build tool descriptions for prompt
        tool_descriptions = self._format_tools_for_prompt(tools)

        # Inject tool instructions into system message
        enhanced_messages = self._inject_tool_instructions(messages, tool_descriptions)

        # Initial generation
        response_text = self.generate(enhanced_messages, config)
        logger.debug(f"Initial response length: {len(response_text)} characters")

        # Parse tool calls from response
        tool_calls = self._parse_tool_calls(response_text)
        logger.debug(f"Parsed {len(tool_calls)} tool calls")

        # Execute tools
        tool_results = []
        if tool_calls:
            tool_results = self._execute_tools(tool_calls)
            logger.debug(f"Executed {len(tool_results)} tools")

            # Continue generation with tool results
            result_messages = enhanced_messages + [
                {"role": "assistant", "content": response_text},
                {"role": "user", "content": f"Tool results: {json.dumps(tool_results)}"}
            ]

            response_text = self.generate(result_messages, config)
            logger.debug("Generated final response with tool results")

        return {
            "response": response_text,
            "tool_calls": tool_calls,
            "tool_results": tool_results
        }

    def _format_tools_for_prompt(self, tools: List[Dict[str, Any]]) -> str:
        """Format tool definitions for prompt injection."""
        tool_lines = ["Available tools:"]
        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name", "unknown")
            desc = func.get("description", "")
            params = func.get("parameters", {}).get("properties", {})

            param_str = ", ".join(params.keys()) if params else "no parameters"
            tool_lines.append(f"- {name}({param_str}): {desc}")

        return "\n".join(tool_lines)

    def _inject_tool_instructions(
        self,
        messages: List[Dict[str, Any]],
        tool_descriptions: str
    ) -> List[Dict[str, Any]]:
        """Inject tool calling instructions into messages."""
        tool_instruction = f"""
{tool_descriptions}

To use a tool, output: TOOL_CALL: tool_name(arg1="value1", arg2="value2")
Example: TOOL_CALL: list_files(directory="src/", pattern="*.py")
"""
        enhanced = messages.copy()

        # Find or create system message
        if enhanced and enhanced[0].get("role") == "system":
            enhanced[0] = {
                "role": "system",
                "content": enhanced[0]["content"] + "\n\n" + tool_instruction
            }
        else:
            enhanced.insert(0, {"role": "system", "content": tool_instruction})

        return enhanced

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse tool calls from model response.

        Looks for pattern: TOOL_CALL: tool_name(args)
        """
        tool_calls = []

        # Pattern: TOOL_CALL: tool_name(arg1="value", arg2="value")
        pattern = r'TOOL_CALL:\s*(\w+)\((.*?)\)'

        matches = re.finditer(pattern, response, re.MULTILINE)

        for match in matches:
            tool_name = match.group(1)
            args_str = match.group(2)

            # Parse arguments (simple key="value" format)
            args = {}
            if args_str:
                # Match key="value" or key='value'
                arg_pattern = r'(\w+)=["\'](.*?)["\']'
                for arg_match in re.finditer(arg_pattern, args_str):
                    key = arg_match.group(1)
                    value = arg_match.group(2)
                    args[key] = value

            tool_calls.append({
                "name": tool_name,
                "arguments": args
            })

            logger.debug(f"Parsed tool call: {tool_name}({args})")

        return tool_calls

    def _execute_tools(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute tool calls using ToolRegistry."""
        from src.tool_registry import default_registry

        results = []

        for call in tool_calls:
            tool_name = call["name"]
            tool_args = call["arguments"]

            logger.debug(f"Executing tool: {tool_name} with args {tool_args}")

            try:
                # Execute tool via registry
                result = default_registry.execute_tool(tool_name, **tool_args)

                results.append({
                    "tool": tool_name,
                    "status": "success",
                    "output": result
                })

                logger.debug(f"Tool {tool_name} executed successfully")

            except Exception as e:
                logger.debug(f"Tool {tool_name} failed: {e}")

                results.append({
                    "tool": tool_name,
                    "status": "error",
                    "error": str(e)
                })

        return results
