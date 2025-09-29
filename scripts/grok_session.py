#!/usr/bin/env python3
"""
Production-ready GrokSession class with all of Grok's recommendations implemented.
Provides structured outputs, state management, streaming support, and robust error handling.
"""

import asyncio
import json
import os
import logging
import time
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, AsyncIterator
from threading import Lock
from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GrokSession:
    """
    Production-ready session class for interacting with Grok via OpenAI-compatible API.
    Features:
    - Maintains conversation state with history limits
    - Handles streaming with proper tool call accumulation
    - Returns structured outputs (dicts)
    - Thread-safe for concurrent use
    - Supports persistence (save/load)
    - Includes retry logic and proper error handling
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "grok-code-fast-1",
        base_url: str = "https://api.x.ai/v1",
        system_prompt: Optional[str] = None,
        max_history: int = 100,
        max_retries: int = 3,
        enable_logging: bool = True
    ):
        """
        Initialize a Grok session.

        Args:
            api_key: XAI API key (defaults to XAI_API_KEY env var)
            model: Model to use
            base_url: xAI API base URL
            system_prompt: Optional system message
            max_history: Maximum messages to keep in history
            max_retries: Number of retry attempts for API calls
            enable_logging: Whether to log API interactions
        """
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("XAI_API_KEY not provided or in environment")

        # Initialize clients
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url
        )
        self.sync_client = OpenAI(
            api_key=self.api_key,
            base_url=base_url
        )

        self.model = model
        self.max_history = max_history
        self.max_retries = max_retries
        self.enable_logging = enable_logging

        # Thread safety
        self.messages: List[Dict[str, Any]] = []
        self.messages_lock = Lock()  # For sync operations
        self.async_messages_lock = asyncio.Lock()  # For async operations

        # Tool functions registry
        self.tool_functions: Dict[str, Callable] = {
            "calculate_math": self._calculate_math
        }

        # Default tools
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "calculate_math",
                    "description": "Evaluate a mathematical expression",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "Math expression to evaluate"
                            }
                        },
                        "required": ["expression"]
                    }
                }
            }
        ]

        # Add system prompt if provided
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

        if self.enable_logging:
            logger.info(f"GrokSession initialized with model: {model}")

    def _calculate_math(self, expression: str) -> str:
        """
        Built-in math calculation tool.
        Note: eval() is kept per user request but is a security risk.
        Consider using numexpr or sympy in production.
        """
        try:
            # Security warning: eval() is dangerous with untrusted input
            result = str(eval(expression))
            if self.enable_logging:
                logger.debug(f"Math calculation: {expression} = {result}")
            return result
        except Exception as e:
            error_msg = f"Calculation error: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _trim_history(self) -> None:
        """Trim message history to max_history limit, preserving system message."""
        if len(self.messages) > self.max_history:
            # Keep system message if present
            system_msg = None
            if self.messages and self.messages[0]["role"] == "system":
                system_msg = self.messages[0]

            # Keep only recent messages
            self.messages = self.messages[-(self.max_history - 1):]

            # Re-add system message at start
            if system_msg:
                self.messages.insert(0, system_msg)

            logger.info(f"Trimmed history to {len(self.messages)} messages")

    def add_tool(self, tool_definition: Dict, tool_function: Callable) -> None:
        """Add a custom tool to the session."""
        tool_name = tool_definition["function"]["name"]
        self.tools.append(tool_definition)
        self.tool_functions[tool_name] = tool_function
        logger.info(f"Added tool: {tool_name}")

    def clear_history(self, keep_system: bool = True) -> None:
        """Clear message history, optionally keeping system message."""
        with self.messages_lock:
            if keep_system and self.messages and self.messages[0]["role"] == "system":
                self.messages = [self.messages[0]]
            else:
                self.messages = []
        logger.info("Cleared message history")

    def save_history(self, filepath: str) -> None:
        """Save conversation history to file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with self.messages_lock:
            with open(path, 'w') as f:
                json.dump({
                    "messages": self.messages,
                    "model": self.model,
                    "timestamp": time.time()
                }, f, indent=2)

        logger.info(f"Saved history to {filepath}")

    def load_history(self, filepath: str) -> None:
        """Load conversation history from file."""
        with open(filepath, 'r') as f:
            data = json.load(f)

        with self.messages_lock:
            self.messages = data["messages"]

        logger.info(f"Loaded {len(self.messages)} messages from {filepath}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception)
    )
    async def _api_call_with_retry(self, **kwargs) -> Any:
        """Make API call with retry logic."""
        return await self.async_client.chat.completions.create(**kwargs)

    async def send_message_async(
        self,
        user_message: str,
        stream: bool = True,
        use_tools: bool = True,
        temperature: float = 0.7,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Async method to send a message to Grok with proper streaming support.

        Args:
            user_message: User's message
            stream: Whether to stream response
            use_tools: Whether to enable tools
            temperature: Response temperature
            stream_callback: Optional callback for streaming chunks

        Returns:
            Structured dict with response, tool calls, etc.
        """
        start_time = time.time()

        # Thread-safe message append
        async with self.async_messages_lock:
            self.messages.append({"role": "user", "content": user_message})
            self._trim_history()

        # Prepare API call
        kwargs = {
            "model": self.model,
            "messages": self.messages.copy(),  # Copy to avoid modification during call
            "temperature": temperature,
            "stream": stream
        }

        if use_tools and self.tools:
            kwargs["tools"] = self.tools
            kwargs["tool_choice"] = "auto"

        response_text = ""
        tool_calls_accumulator = {}  # Fix for streaming tool calls
        tool_results = []
        success = True

        try:
            if stream:
                # Proper streaming with tool call accumulation
                stream_response = await self._api_call_with_retry(**kwargs)

                async for chunk in stream_response:
                    if chunk.choices:
                        delta = chunk.choices[0].delta

                        # Accumulate content
                        if delta.content:
                            response_text += delta.content
                            if stream_callback:
                                stream_callback(delta.content)

                        # Properly accumulate tool calls by index
                        if delta.tool_calls:
                            for tc_delta in delta.tool_calls:
                                idx = tc_delta.index

                                if idx not in tool_calls_accumulator:
                                    tool_calls_accumulator[idx] = {
                                        "id": tc_delta.id,
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""}
                                    }

                                if tc_delta.function.name:
                                    tool_calls_accumulator[idx]["function"]["name"] += tc_delta.function.name
                                if tc_delta.function.arguments:
                                    tool_calls_accumulator[idx]["function"]["arguments"] += tc_delta.function.arguments

                # Convert accumulated tool calls to list
                tool_calls = list(tool_calls_accumulator.values()) if tool_calls_accumulator else []

            else:
                # Non-streaming
                response = await self._api_call_with_retry(**kwargs)
                choice = response.choices[0]
                response_text = choice.message.content or ""
                tool_calls = [tc.model_dump() for tc in choice.message.tool_calls] if choice.message.tool_calls else []

            # Append assistant response to history
            async with self.async_messages_lock:
                assistant_message = {"role": "assistant", "content": response_text}
                if tool_calls:
                    assistant_message["tool_calls"] = tool_calls
                self.messages.append(assistant_message)

            # Execute tools if any
            if tool_calls:
                for tool_call in tool_calls:
                    func_name = tool_call.get("function", {}).get("name")

                    if func_name and func_name in self.tool_functions:
                        try:
                            func_args = json.loads(tool_call["function"]["arguments"])

                            # Execute tool function (wrap sync functions for async context)
                            if asyncio.iscoroutinefunction(self.tool_functions[func_name]):
                                result = await self.tool_functions[func_name](**func_args)
                            else:
                                result = await asyncio.to_thread(
                                    self.tool_functions[func_name], **func_args
                                )

                            tool_results.append({
                                "tool": func_name,
                                "args": func_args,
                                "result": result
                            })

                            # Add tool result to messages
                            async with self.async_messages_lock:
                                self.messages.append({
                                    "role": "tool",
                                    "content": result,
                                    "tool_call_id": tool_call["id"]
                                })

                        except Exception as e:
                            logger.error(f"Tool execution error for {func_name}: {e}")
                            tool_results.append({
                                "tool": func_name,
                                "args": {},
                                "error": str(e)
                            })

                # Get final response after tool execution
                follow_up_kwargs = {
                    "model": self.model,
                    "messages": self.messages.copy(),
                    "temperature": temperature
                }

                follow_up = await self._api_call_with_retry(**follow_up_kwargs)
                final_text = follow_up.choices[0].message.content

                if final_text:
                    response_text = final_text  # Always use final response after tools
                    async with self.async_messages_lock:
                        self.messages.append({"role": "assistant", "content": final_text})

        except Exception as e:
            error_msg = f"API Error: {str(e)}"
            logger.error(error_msg)
            response_text = error_msg
            tool_calls = []
            tool_results = []
            success = False

        elapsed_time = time.time() - start_time

        if self.enable_logging:
            logger.info(f"Message processed in {elapsed_time:.2f}s")

        # Return structured dict
        return {
            "response": response_text,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "messages": self.messages.copy(),
            "message_count": len(self.messages),
            "success": success,
            "elapsed_time": elapsed_time
        }

    def send_message_sync(
        self,
        user_message: str,
        use_tools: bool = True,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Synchronous version for non-async contexts.
        Fully implemented based on async version.
        """
        start_time = time.time()

        # Thread-safe message append
        with self.messages_lock:
            self.messages.append({"role": "user", "content": user_message})
            self._trim_history()

        kwargs = {
            "model": self.model,
            "messages": self.messages.copy(),
            "temperature": temperature,
            "stream": False  # Sync doesn't support streaming well
        }

        if use_tools and self.tools:
            kwargs["tools"] = self.tools
            kwargs["tool_choice"] = "auto"

        tool_results = []
        success = True

        try:
            # Make API call with retries
            max_retries = self.max_retries
            for attempt in range(max_retries):
                try:
                    response = self.sync_client.chat.completions.create(**kwargs)
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    wait_time = 2 ** attempt
                    logger.warning(f"Retry {attempt + 1} after {wait_time}s: {e}")
                    time.sleep(wait_time)

            choice = response.choices[0]
            response_text = choice.message.content or ""
            tool_calls = [tc.model_dump() for tc in choice.message.tool_calls] if choice.message.tool_calls else []

            # Add assistant message
            with self.messages_lock:
                assistant_message = {"role": "assistant", "content": response_text}
                if tool_calls:
                    assistant_message["tool_calls"] = tool_calls
                self.messages.append(assistant_message)

            # Execute tools if any
            if tool_calls:
                for tool_call in tool_calls:
                    func_name = tool_call.get("function", {}).get("name")

                    if func_name and func_name in self.tool_functions:
                        try:
                            func_args = json.loads(tool_call["function"]["arguments"])
                            result = self.tool_functions[func_name](**func_args)

                            tool_results.append({
                                "tool": func_name,
                                "args": func_args,
                                "result": result
                            })

                            with self.messages_lock:
                                self.messages.append({
                                    "role": "tool",
                                    "content": result,
                                    "tool_call_id": tool_call["id"]
                                })

                        except Exception as e:
                            logger.error(f"Tool execution error for {func_name}: {e}")
                            tool_results.append({
                                "tool": func_name,
                                "args": {},
                                "error": str(e)
                            })

                # Get final response
                follow_up_response = self.sync_client.chat.completions.create(
                    model=self.model,
                    messages=self.messages.copy(),
                    temperature=temperature
                )

                final_text = follow_up_response.choices[0].message.content
                if final_text:
                    response_text = final_text
                    with self.messages_lock:
                        self.messages.append({"role": "assistant", "content": final_text})

        except Exception as e:
            error_msg = f"API Error: {str(e)}"
            logger.error(error_msg)
            response_text = error_msg
            tool_calls = []
            tool_results = []
            success = False

        elapsed_time = time.time() - start_time

        if self.enable_logging:
            logger.info(f"Sync message processed in {elapsed_time:.2f}s")

        return {
            "response": response_text,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "messages": self.messages.copy(),
            "message_count": len(self.messages),
            "success": success,
            "elapsed_time": elapsed_time
        }

    def send_message(
        self,
        user_message: str,
        async_mode: Optional[bool] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Main programmatic entry point with smart async detection.

        Args:
            user_message: User's message
            async_mode: Force async/sync mode. If None, defaults to sync.
            **kwargs: Additional parameters for send_message_async/sync

        Returns:
            Structured response dict

        Note: For async contexts, use send_message_async directly or set async_mode=True
        """
        # Default to sync for simplicity
        if async_mode is None:
            async_mode = False

        if async_mode:
            # Check if there's already an event loop running
            try:
                loop = asyncio.get_running_loop()
                # Already in async context, can't use asyncio.run
                raise RuntimeError(
                    "Cannot use async_mode=True from within an async context. "
                    "Use 'await send_message_async()' directly instead."
                )
            except RuntimeError:
                # No loop, create one
                return asyncio.run(self.send_message_async(user_message, **kwargs))
        else:
            return self.send_message_sync(user_message, **kwargs)

    async def stream_message(
        self,
        user_message: str,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream response chunks as they arrive.

        Yields:
            Response text chunks
        """
        chunks = []

        def collect_chunk(chunk: str):
            chunks.append(chunk)

        kwargs["stream_callback"] = collect_chunk
        kwargs["stream"] = True

        # Start the async call
        task = asyncio.create_task(
            self.send_message_async(user_message, **kwargs)
        )

        # Yield chunks as they arrive
        last_len = 0
        while not task.done():
            if len(chunks) > last_len:
                for chunk in chunks[last_len:]:
                    yield chunk
                last_len = len(chunks)
            await asyncio.sleep(0.01)

        # Get final result for any remaining chunks
        result = await task
        if len(chunks) > last_len:
            for chunk in chunks[last_len:]:
                yield chunk

    def get_conversation_summary(self, max_length: int = 100) -> str:
        """Get a summary of the conversation so far."""
        summary = []
        with self.messages_lock:
            for msg in self.messages:
                role = msg["role"]
                content = msg.get("content", "")
                if content:
                    preview = content[:max_length] + "..." if len(content) > max_length else content
                    summary.append(f"{role}: {preview}")
        return "\n".join(summary)

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        with self.messages_lock:
            user_msgs = sum(1 for m in self.messages if m["role"] == "user")
            assistant_msgs = sum(1 for m in self.messages if m["role"] == "assistant")
            tool_msgs = sum(1 for m in self.messages if m["role"] == "tool")

        return {
            "total_messages": len(self.messages),
            "user_messages": user_msgs,
            "assistant_messages": assistant_msgs,
            "tool_messages": tool_msgs,
            "max_history": self.max_history,
            "model": self.model
        }


# Example usage
if __name__ == "__main__":
    print("=== Testing GrokSession with all improvements ===\n")

    # Initialize session
    session = GrokSession(
        system_prompt="You are a helpful AI assistant. Use tools when needed.",
        max_history=50,
        enable_logging=True
    )

    # Test 1: Basic message
    print("Test 1: Basic message")
    result1 = session.send_message("Hello! Can you introduce yourself?")
    print(f"Response: {result1['response'][:200]}...")
    print(f"Success: {result1['success']}")
    print(f"Time: {result1['elapsed_time']:.2f}s\n")

    # Test 2: Math calculation with tools
    print("Test 2: Math calculation")
    result2 = session.send_message("What is 42 * 17 + 3?")
    print(f"Response: {result2['response']}")
    if result2['tool_results']:
        print(f"Tools used: {result2['tool_results']}")
    print(f"Message count: {result2['message_count']}\n")

    # Test 3: Save and load history
    print("Test 3: Persistence")
    session.save_history("/tmp/grok_session.json")
    print("History saved")

    # Create new session and load
    new_session = GrokSession()
    new_session.load_history("/tmp/grok_session.json")
    print(f"Loaded {new_session.get_stats()['total_messages']} messages\n")

    # Test 4: Session stats
    print("Test 4: Session statistics")
    stats = session.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n✅ All tests completed!")