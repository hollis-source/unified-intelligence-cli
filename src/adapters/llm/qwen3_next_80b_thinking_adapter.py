"""
Qwen3-Next-80B-A3B-Thinking Adapter - Premium reasoning via HF Inference Endpoint.

This adapter provides access to Qwen3-Next-80B-A3B-Thinking, an 80B parameter
thinking model optimized for complex reasoning tasks.

Architecture Pattern: Clean Architecture + Dependency Inversion Principle (DIP)
- Implements ITextGenerator interface
- Hides HuggingFace InferenceClient specifics
- Provides stable interface for reasoning-heavy inference

Model Capabilities:
- 80B total params, 3B activated (High-Sparsity MoE)
- 262K context (extensible to 1M with YaRN)
- Explicit thinking process in <think> tags
- Outperforms Gemini-2.5-Flash-Thinking on reasoning benchmarks

Performance Metrics:
- AIME25: 87.8% (vs 72% Gemini-Flash)
- HMMT25: 73.9% (vs 64.2% Gemini-Flash)
- LiveCodeBench: 68.7% (vs 61.2% Gemini-Flash)
- Cost: $10/hour when active (scale-to-zero saves costs)

Best Practices (from model card):
- Temperature: 0.6, TopP: 0.95, TopK: 20
- Max output: 32,768 tokens (81,920 for complex math/code)
- Multi-turn: Only include final answer in history (not thinking)
"""

from typing import List, Dict, Any, Optional
import os
import requests
from dataclasses import dataclass

from src.interfaces import ITextGenerator, LLMConfig


@dataclass
class ThinkingResponse:
    """
    Response from thinking model with separated thinking and answer.

    Attributes:
        thinking: The reasoning process (<think> content)
        answer: The final answer/output
        raw: Full raw response
    """
    thinking: str
    answer: str
    raw: str


class Qwen3Next80BThinkingAdapter(ITextGenerator):
    """
    Adapter for Qwen3-Next-80B-A3B-Thinking via HF Inference Endpoint.

    DIP: Implements interface, hides InferenceClient specifics.
    SRP: Single responsibility - premium reasoning inference.

    Special Features:
    - Parses thinking process separately from final answer
    - Optimized parameters for reasoning tasks
    - Supports ultra-long context (262K tokens)

    Attributes:
        endpoint_url: HF Inference Endpoint URL
        client: InferenceClient for API calls
        model_name: Display name for logging
        token: HF authentication token
    """

    def __init__(
        self,
        endpoint_url: str = "https://crlqq5n5zwaz4rnh.us-east-2.aws.endpoints.huggingface.cloud",
        token: Optional[str] = None,
        timeout: int = 300  # 5 minutes for complex reasoning
    ):
        """
        Initialize Qwen3-Next-80B-Thinking adapter.

        Args:
            endpoint_url: HF Inference Endpoint URL
            token: HF token (defaults to HF_TOKEN env var)
            timeout: Request timeout in seconds (default: 300 for complex reasoning)
        """
        self.endpoint_url = endpoint_url
        self.token = token or os.getenv("HF_TOKEN")
        self.timeout = timeout
        self.model_name = "Qwen3-Next-80B-Thinking"

        if not self.token:
            raise ValueError(
                "HF_TOKEN not found. Set HF_TOKEN environment variable or pass token parameter."
            )

        # Store endpoint configuration
        # Use requests directly for dedicated Inference Endpoints
        self.api_url = f"{self.endpoint_url}/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def generate(
        self,
        messages: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None
    ) -> str:
        """
        Generate text using Qwen3-Next-80B-Thinking via Inference Endpoint.

        Adapter pattern: Translates interface to InferenceClient format.

        Args:
            messages: Conversation in standard format:
                     [{\"role\": \"system\", \"content\": \"...\"},
                      {\"role\": \"user\", \"content\": \"...\"},
                      {\"role\": \"assistant\", \"content\": \"...\"}]
            config: Optional LLM configuration

        Returns:
            Generated text response (final answer only, thinking stripped)

        Implementation Details:
        - Uses chat_completion API (OpenAI-compatible)
        - Automatically strips thinking content from response
        - Applies optimal parameters for reasoning (temp=0.6, etc.)
        - First request may take 2-3 min if scaled to zero

        Performance:
        - Warm latency: ~10-20s for complex reasoning
        - Cold start: 2-3 minutes (scale-to-zero)
        - Cost: $10/hour when active
        """
        # Apply optimized config for thinking model
        if config is None:
            config = LLMConfig(
                temperature=0.6,  # Recommended by model card
                max_tokens=32768  # Adequate for most reasoning tasks
            )

        # Extract parameters
        temperature = config.temperature if config.temperature is not None else 0.6
        max_tokens = config.max_tokens if config.max_tokens is not None else 32768
        top_p = 0.95  # Recommended by model card

        try:
            # Call HF Inference Endpoint via requests
            payload = {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "stream": False
            }

            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            # Extract response text
            result = response.json()
            message = result["choices"][0]["message"]
            full_response = message.get("content", "")

            # Parse thinking and answer
            thinking_response = self._parse_thinking(full_response)

            # Return only final answer (thinking stripped)
            # Note: thinking is available via generate_with_thinking()
            return thinking_response.answer

        except Exception as e:
            # Log error and re-raise with context
            error_msg = f"Qwen3-Next-80B Endpoint error: {e}"
            raise RuntimeError(error_msg) from e

    def generate_with_thinking(
        self,
        messages: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None
    ) -> ThinkingResponse:
        """
        Generate with explicit thinking process exposed.

        Same as generate() but returns both thinking and answer.

        Args:
            messages: Conversation messages
            config: Optional LLM configuration

        Returns:
            ThinkingResponse with thinking, answer, and raw text

        Example:
            >>> response = adapter.generate_with_thinking([...])
            >>> print("Reasoning:", response.thinking)
            >>> print("Answer:", response.answer)
        """
        if config is None:
            config = LLMConfig(
                temperature=0.6,
                max_tokens=32768
            )

        # Extract parameters
        temperature = config.temperature if config.temperature is not None else 0.6
        max_tokens = config.max_tokens if config.max_tokens is not None else 32768
        top_p = 0.95

        try:
            # Call HF Inference Endpoint via requests
            payload = {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "stream": False
            }

            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            # Extract response text
            result = response.json()
            message = result["choices"][0]["message"]
            full_response = message.get("content", "")

            return self._parse_thinking(full_response)

        except Exception as e:
            error_msg = f"Qwen3-Next-80B Endpoint error: {e}"
            raise RuntimeError(error_msg) from e

    def _parse_thinking(self, full_response: str) -> ThinkingResponse:
        """
        Parse thinking content from model response.

        The model outputs: <think>reasoning</think>final_answer
        We need to separate these components.

        Args:
            full_response: Full model output

        Returns:
            ThinkingResponse with separated thinking and answer
        """
        # Look for </think> tag
        think_end = "</think>"

        if think_end in full_response:
            # Split on </think>
            parts = full_response.split(think_end, 1)

            # Everything before </think> is thinking (strip <think> if present)
            thinking = parts[0].replace("<think>", "").strip()

            # Everything after </think> is final answer
            answer = parts[1].strip() if len(parts) > 1 else ""
        else:
            # No thinking tags found (shouldn't happen with this model)
            thinking = ""
            answer = full_response.strip()

        return ThinkingResponse(
            thinking=thinking,
            answer=answer,
            raw=full_response
        )

    def generate_batch(
        self,
        batch_messages: List[List[Dict[str, Any]]],
        config: Optional[LLMConfig] = None
    ) -> List[str]:
        """
        Generate responses for batch of message sequences.

        Args:
            batch_messages: List of message sequences
            config: Optional LLM configuration

        Returns:
            List of generated responses (final answers only)

        Note: Current implementation processes sequentially.
        For true parallel processing, use async implementation.
        """
        return [self.generate(messages, config) for messages in batch_messages]

    def close(self):
        """
        Cleanup resources (placeholder for interface compatibility).

        HF InferenceClient doesn't require explicit cleanup.
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()
        return False


# Convenience function for quick usage
def create_qwen3_next_thinking(
    endpoint_url: str = None,
    token: Optional[str] = None
) -> Qwen3Next80BThinkingAdapter:
    """
    Factory function to create Qwen3-Next-80B-Thinking adapter.

    Args:
        endpoint_url: HF Inference Endpoint URL (optional, uses default if not provided)
        token: HF token (optional, uses HF_TOKEN env var if not provided)

    Returns:
        Configured Qwen3Next80BThinkingAdapter instance

    Example:
        >>> adapter = create_qwen3_next_thinking()
        >>> messages = [{\"role\": \"user\", \"content\": \"Solve this complex problem...\"}]
        >>> response = adapter.generate_with_thinking(messages)
        >>> print("Reasoning:", response.thinking)
        >>> print("Answer:", response.answer)
    """
    return Qwen3Next80BThinkingAdapter(endpoint_url=endpoint_url, token=token)
