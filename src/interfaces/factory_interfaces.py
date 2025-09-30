"""Factory interfaces - DIP: Depend on abstractions, not concretions."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from src.entities import Agent
from src.interfaces.llm_provider import ITextGenerator


class IAgentFactory(ABC):
    """
    Interface for agent creation.

    DIP: High-level modules depend on this abstraction.
    OCP: Extend by implementing new factories, not modifying this.
    """

    @abstractmethod
    def create_default_agents(self) -> List[Agent]:
        """
        Create default agent team.

        Returns:
            List of configured agents
        """
        pass

    @abstractmethod
    def create_from_config(self, config: List[Dict[str, Any]]) -> List[Agent]:
        """
        Create agents from configuration.

        Args:
            config: List of agent configurations

        Returns:
            List of configured agents
        """
        pass


class IProviderFactory(ABC):
    """
    Interface for LLM provider creation.

    DIP: Composition root depends on this abstraction.
    Strategy Pattern: Allows runtime provider selection.
    """

    @abstractmethod
    def create_provider(
        self,
        provider_type: str,
        config: Optional[Dict[str, Any]] = None
    ) -> ITextGenerator:
        """
        Create LLM provider by type.

        Args:
            provider_type: Type of provider (mock, grok, openai)
            config: Provider configuration

        Returns:
            ITextGenerator implementation

        Raises:
            ValueError: If provider type not found
        """
        pass

    @abstractmethod
    def register_provider(self, name: str, provider_class: Any) -> None:
        """
        Register a new provider type.

        OCP: Extend without modifying existing code.

        Args:
            name: Provider identifier
            provider_class: Class implementing ITextGenerator
        """
        pass