#!/usr/bin/env python3
"""Consult Grok about our interface design."""

from grok_session import GrokSession

# The interface we're designing
interface_code = '''
"""LLM Provider interface - ISP: Narrow interface for LLM interactions."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ILLMProvider(ABC):
    """
    Abstract interface for LLM providers.
    ISP: Minimal interface - just what use cases need.
    """

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate response from LLM.

        Args:
            prompt: Input prompt
            **kwargs: Provider-specific options

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    def supports_tools(self) -> bool:
        """Check if provider supports tool/function calling."""
        pass
'''

context = '''
We're building a Unified Intelligence CLI following Clean Architecture principles.
This is for the interfaces layer that will be used by use cases to interact with LLMs.
We want to follow SOLID principles, especially:
- ISP (Interface Segregation): Small, specific interfaces
- DIP (Dependency Inversion): Depend on abstractions

The use cases will coordinate multiple agents that need to:
1. Generate responses from LLMs (Grok, Claude, OpenAI, etc.)
2. Potentially use tools/functions
3. Be easily testable with mock implementations
'''

question = '''
Review this ILLMProvider interface design. Is it following ISP correctly?
Should we:
1. Keep it this minimal?
2. Add more methods like streaming, conversation history, or temperature control?
3. Split into even smaller interfaces (e.g., ITextGenerator, IToolUser)?
4. Handle provider-specific features differently?

Provide specific recommendations based on Clean Architecture and your experience with LLM APIs.
'''

# Consult Grok
session = GrokSession(
    system_prompt="You are Grok. Analyze this code architecture critically, focusing on SOLID principles and Clean Architecture.",
    enable_logging=False
)

print("Consulting Grok about interface design...")
print("=" * 60)

full_query = f"Context:\n{context}\n\nInterface Code:\n```python\n{interface_code}\n```\n\nQuestion:\n{question}"

result = session.send_message(full_query)
print(result['response'])