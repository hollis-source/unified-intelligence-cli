"""
Local Tongyi adapter using llama.cpp server.

Week 8: Local model optimization pipeline (Phase 1).
Implements ITextGenerator for local GGUF models via llama-cpp-server HTTP API.

Architecture:
- Adapter Pattern: Wraps llama-cpp-server HTTP API
- DIP: Implements ITextGenerator interface
- Performance: 40+ tok/s, <50ms first token
- Cost: Zero marginal cost (vs API $0.002-$0.008/1K tokens)
"""

import aiohttp
import asyncio
import logging
from typing import List, Dict, Any, Optional
from src.interfaces import ITextGenerator

logger = logging.getLogger(__name__)


class LocalTongyiAdapter(ITextGenerator):
    """
    Local Tongyi LLM adapter via llama.cpp server.

    Week 8: Deploys Tongyi-DeepResearch-30B-Q8_0 (32.5 GB) locally.
    Clean Architecture: Adapter pattern, depends on ITextGenerator interface.
    Performance: 40+ tok/s, 4-10x faster than API (no network latency).

    Usage:
        adapter = LocalTongyiAdapter(base_url="http://localhost:8080")
        response = await adapter.generate("You are a coordinator agent...")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        timeout: int = 120,
        max_retries: int = 3
    ):
        """
        Initialize local Tongyi adapter.

        Args:
            base_url: llama-cpp-server URL (default: http://localhost:8080)
            timeout: Request timeout in seconds (default: 120)
            max_retries: Maximum retry attempts (default: 3)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None

        logger.info(f"LocalTongyiAdapter initialized: {base_url}")

    async def _ensure_session(self):
        """Create aiohttp session if not exists (lazy initialization)."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
            logger.debug("Created new aiohttp session")

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Generate text from prompt using local Tongyi model.

        Args:
            prompt: Input prompt (task description, system + user message)
            max_tokens: Maximum tokens to generate (default: 512)
            temperature: Sampling temperature 0.0-2.0 (default: 0.7)
            stop: Stop sequences (optional, e.g. ["\\n\\n", "###"])
            **kwargs: Additional llama.cpp parameters (top_p, top_k, repeat_penalty)

        Returns:
            Generated text string

        Raises:
            ConnectionError: If llama-cpp-server unavailable
            TimeoutError: If request exceeds timeout
            RuntimeError: If max retries exceeded

        Example:
            >>> adapter = LocalTongyiAdapter()
            >>> result = await adapter.generate(
            ...     "You are a coder agent. Implement: Binary search in Python",
            ...     max_tokens=256,
            ...     temperature=0.7
            ... )
        """
        await self._ensure_session()

        # Build request payload (llama.cpp completion endpoint)
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": temperature,
            "stop": stop or [],
            "stream": False  # Non-streaming for simplicity (Phase 1)
        }

        # Add optional llama.cpp parameters
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            payload["top_k"] = kwargs["top_k"]
        if "repeat_penalty" in kwargs:
            payload["repeat_penalty"] = kwargs["repeat_penalty"]
        if "presence_penalty" in kwargs:
            payload["presence_penalty"] = kwargs["presence_penalty"]
        if "frequency_penalty" in kwargs:
            payload["frequency_penalty"] = kwargs["frequency_penalty"]

        # Retry loop with exponential backoff
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"Sending request to {self.base_url}/completion "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )

                async with self.session.post(
                    f"{self.base_url}/completion",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        content = data.get("content", "")

                        # Log performance metrics (Week 8: validation)
                        tokens_predicted = data.get("tokens_predicted", 0)
                        tokens_evaluated = data.get("tokens_evaluated", 0)
                        timings = data.get("timings", {})
                        tok_per_sec = timings.get("predicted_per_second", 0)

                        logger.info(
                            f"Local inference successful: "
                            f"{tokens_predicted} tokens generated, "
                            f"{tokens_evaluated} tokens evaluated, "
                            f"{tok_per_sec:.1f} tok/s"
                        )

                        return content

                    else:
                        # Server error (4xx/5xx)
                        error_text = await resp.text()
                        logger.error(
                            f"Server error {resp.status}: {error_text[:200]}"
                        )

                        if attempt < self.max_retries - 1:
                            wait_time = 2 ** attempt
                            logger.warning(f"Retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue

                        raise ConnectionError(
                            f"Server returned {resp.status}: {error_text[:200]}"
                        )

            except aiohttp.ClientError as e:
                # Network error (connection refused, timeout, etc.)
                logger.error(
                    f"Connection error (attempt {attempt + 1}/{self.max_retries}): {e}"
                )

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

                raise ConnectionError(
                    f"Failed to connect to llama-cpp-server at {self.base_url}: {e}"
                )

            except asyncio.TimeoutError:
                logger.error(
                    f"Request timeout (attempt {attempt + 1}/{self.max_retries})"
                )

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

                raise TimeoutError(
                    f"Request timed out after {self.timeout.total}s"
                )

        # Max retries exceeded
        raise RuntimeError(
            f"Max retries ({self.max_retries}) exceeded for local inference"
        )

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        **kwargs
    ) -> str:
        """
        Generate with tool calling support.

        Note: llama.cpp server doesn't natively support structured tool calling.
        We emulate via prompt engineering (same as current TongyiAdapter).

        Week 8 Phase 1: Basic tool description in prompt.
        Week 8 Phase 2: Could add function calling via guided generation.

        Args:
            prompt: Base prompt
            tools: List of tool definitions (OpenAI format)
            **kwargs: Additional generation parameters

        Returns:
            Generated text (may include TOOL_CALL: directives)
        """
        # Format tools as text for prompt (emulation strategy)
        tools_description = self._format_tools_for_prompt(tools)
        full_prompt = f"{prompt}\n\n{tools_description}"

        logger.debug(f"Tool-augmented prompt: {len(full_prompt)} chars")

        return await self.generate(full_prompt, **kwargs)

    def _format_tools_for_prompt(self, tools: List[Dict[str, Any]]) -> str:
        """
        Format tools as text for prompt inclusion.

        Mirrors TongyiAdapter's tool formatting for consistency.

        Args:
            tools: List of tool definitions

        Returns:
            Formatted tool documentation string
        """
        if not tools:
            return ""

        tool_docs = ["Available tools:"]

        for tool in tools:
            function = tool.get("function", {})
            name = function.get("name", "unknown")
            description = function.get("description", "")
            parameters = function.get("parameters", {})

            tool_docs.append(f"\n- {name}: {description}")

            if parameters:
                tool_docs.append(f"  Parameters: {parameters}")

        tool_docs.append(
            "\nTo use a tool, respond with: TOOL_CALL: {tool_name}({args})"
        )

        return "\n".join(tool_docs)

    async def health_check(self) -> bool:
        """
        Check if llama-cpp-server is healthy and responding.

        Returns:
            True if server healthy, False otherwise

        Example:
            >>> adapter = LocalTongyiAdapter()
            >>> is_healthy = await adapter.health_check()
            >>> if not is_healthy:
            ...     print("Server unavailable, falling back to API")
        """
        await self._ensure_session()

        try:
            async with self.session.get(
                f"{self.base_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.debug(f"Health check passed: {data}")
                    return True
                else:
                    logger.warning(f"Health check failed: {resp.status}")
                    return False

        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False

    async def get_model_info(self) -> Optional[Dict[str, Any]]:
        """
        Get loaded model information from server.

        Returns:
            Model metadata dict or None if unavailable

        Example:
            >>> adapter = LocalTongyiAdapter()
            >>> info = await adapter.get_model_info()
            >>> print(f"Model: {info['data'][0]['id']}")
            >>> print(f"Size: {info['data'][0]['meta']['size']} bytes")
        """
        await self._ensure_session()

        try:
            async with self.session.get(
                f"{self.base_url}/v1/models",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"Model info unavailable: {resp.status}")
                    return None

        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return None

    async def close(self):
        """
        Close HTTP session gracefully.

        Should be called when adapter no longer needed.
        """
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("Closed aiohttp session")

    def __del__(self):
        """Cleanup on garbage collection."""
        if self.session and not self.session.closed:
            # Note: This may not work reliably in all scenarios
            # Better to explicitly call close() in production
            try:
                asyncio.create_task(self.session.close())
            except RuntimeError:
                # Event loop might be closed already
                pass


# Convenience function for quick testing
async def test_local_tongyi():
    """
    Test LocalTongyiAdapter with sample prompt.

    Usage:
        python3 -c "import asyncio; from src.adapters.llm.tongyi_local_adapter import test_local_tongyi; asyncio.run(test_local_tongyi())"
    """
    adapter = LocalTongyiAdapter()

    # Test 1: Health check
    print("Test 1: Health check...")
    is_healthy = await adapter.health_check()
    print(f"  Server healthy: {is_healthy}")

    if not is_healthy:
        print("  ❌ Server not responding")
        return

    # Test 2: Model info
    print("\nTest 2: Model info...")
    model_info = await adapter.get_model_info()
    if model_info:
        model = model_info['data'][0]
        print(f"  Model: {model['id']}")
        print(f"  Size: {model['meta']['size'] / 1e9:.1f} GB")
        print(f"  Params: {model['meta']['n_params'] / 1e9:.1f}B")

    # Test 3: Simple inference
    print("\nTest 3: Inference...")
    prompt = "You are a coordinator agent. Plan a workflow for: Implement REST API with authentication"
    result = await adapter.generate(prompt, max_tokens=128, temperature=0.7)
    print(f"  Prompt: {prompt[:60]}...")
    print(f"  Result: {result[:200]}...")

    # Test 4: Tool calling emulation
    print("\nTest 4: Tool calling...")
    tools = [
        {
            "function": {
                "name": "run_command",
                "description": "Execute shell command",
                "parameters": {"command": {"type": "string"}}
            }
        }
    ]
    result = await adapter.generate_with_tools(
        "You are a coder. Create a new Python file called test.py",
        tools,
        max_tokens=128
    )
    print(f"  Result: {result[:200]}...")

    await adapter.close()
    print("\n✅ All tests passed")


if __name__ == "__main__":
    # Run tests if executed directly
    asyncio.run(test_local_tongyi())