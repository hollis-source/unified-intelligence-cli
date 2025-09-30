"""Tongyi-DeepResearch-30B adapter - Integrates llama.cpp server with Clean Architecture.

Adapter for Tongyi-DeepResearch-30B model served via llama.cpp Docker container.
Follows DIP: Implements ITextGenerator interface, hides HTTP client details.
"""

import requests
from typing import List, Dict, Any, Optional
from src.interfaces import ITextGenerator, LLMConfig


class TongyiDeepResearchAdapter(ITextGenerator):
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
        # Convert messages to prompt
        prompt = self._messages_to_prompt(messages)

        # Build request payload
        payload = {
            "prompt": prompt,
            "n_predict": config.max_tokens if config and config.max_tokens else 512,
            "temperature": config.temperature if config and config.temperature else 0.7,
            "stop": ["<|im_end|>"],
            "stream": False
        }

        # Call llama.cpp server
        try:
            response = requests.post(
                f"{self.server_url}/completion",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            content = result.get("content", "")

            if not content:
                raise ValueError("Empty response from llama.cpp server")

            return content.strip()

        except requests.Timeout:
            raise TimeoutError(
                f"Request timed out after {self.timeout}s"
            )
        except requests.RequestException as e:
            raise ConnectionError(
                f"HTTP request failed: {e}"
            )
        except (KeyError, ValueError) as e:
            raise ValueError(
                f"Invalid response format: {e}"
            )