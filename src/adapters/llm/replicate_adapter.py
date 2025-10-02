"""Replicate GPU Inference Adapter - Fast parallel execution with GPU acceleration.

Adapter for Replicate's GPU inference API using models like Llama 2 70B.
Follows DIP: Implements ITextGenerator interface, hides Replicate API details.

Cost: ~$0.001-0.01 per request
Speed: 2-5x faster than CPU inference (~3-5s vs 12s)
"""

import os
import logging
from typing import List, Dict, Any, Optional
from src.interfaces.llm_provider import ITextGenerator, LLMConfig

logger = logging.getLogger(__name__)


class ReplicateAdapter(ITextGenerator):
    """
    Adapter for Replicate GPU inference.

    Architecture:
    - Clean Architecture: Adapter layer (external interface)
    - DIP: Implements ITextGenerator, hides Replicate specifics
    - SRP: Single responsibility - API communication with Replicate

    Models: meta/llama-2-70b-chat, mistralai/mistral-7b-instruct-v0.2
    """

    def __init__(
        self,
        model: str = "meta/llama-3.1-70b-instruct",
        api_token: Optional[str] = None
    ):
        """
        Initialize Replicate adapter.

        Args:
            model: Replicate model identifier
            api_token: Replicate API token (from env if not provided)
        """
        self.model = model
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")

        if not self.api_token:
            raise ValueError(
                "Replicate API token required. Set REPLICATE_API_TOKEN env var "
                "or pass api_token parameter."
            )

        # Lazy import to avoid dependency if not using Replicate
        try:
            import replicate as replicate_module
            self.replicate = replicate_module
            # Configure token
            os.environ["REPLICATE_API_TOKEN"] = self.api_token
            logger.info(f"Replicate adapter initialized with model: {model}")
        except ImportError:
            raise ImportError(
                "replicate package required. Install with: pip install replicate"
            )

    def _messages_to_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """
        Convert OpenAI message format to a single prompt string.

        Args:
            messages: OpenAI-style messages

        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        # Add final assistant prompt
        prompt_parts.append("Assistant:")

        return "\n\n".join(prompt_parts)

    def generate(
        self,
        messages: List[Dict[str, Any]],
        config: Optional[LLMConfig] = None
    ) -> str:
        """
        Generate text using Replicate GPU inference.

        Implements ITextGenerator.generate() contract.
        Adapter pattern: Translates interface to Replicate API.

        Args:
            messages: Conversation messages in OpenAI format
            config: Optional LLM configuration

        Returns:
            Generated text response

        Raises:
            ConnectionError: If API is unreachable
            ValueError: If generation fails
        """
        logger.debug(f"Replicate generate() called with {len(messages)} messages")

        # Convert messages to prompt
        prompt = self._messages_to_prompt(messages)
        logger.debug(f"Prompt length: {len(prompt)} characters")

        # Build input parameters
        max_tokens = config.max_tokens if config and config.max_tokens else 512
        temperature = config.temperature if config and config.temperature else 0.7

        input_params = {
            "prompt": prompt,
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "repetition_penalty": 1.1
        }

        logger.debug(f"Replicate API call: model={self.model}")
        logger.debug(f"Parameters: max_tokens={max_tokens}, temperature={temperature}")

        try:
            # Call Replicate API
            output = self.replicate.run(
                self.model,
                input=input_params
            )

            # Replicate returns an iterator of strings
            response_text = "".join(output) if hasattr(output, '__iter__') else str(output)

            logger.debug(f"Response length: {len(response_text)} characters")

            if not response_text or not response_text.strip():
                logger.warning("Empty response from Replicate API")
                raise ValueError("Empty response from Replicate API")

            return response_text.strip()

        except Exception as e:
            logger.error(f"Replicate API error: {e}")
            raise ConnectionError(f"Replicate API request failed: {e}")
