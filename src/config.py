"""
Configuration management for Unified Intelligence CLI.

Supports JSON config files for runtime provider and agent configuration.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Config:
    """
    Application configuration.

    Supports loading from JSON file with CLI argument override.
    """

    # LLM Provider settings
    provider: str = "mock"
    provider_config: Dict[str, Any] = field(default_factory=dict)

    # Execution settings
    parallel: bool = True
    timeout: int = 60
    verbose: bool = False

    # Agent settings (optional custom agent definitions)
    custom_agents: list = field(default_factory=list)

    @classmethod
    def from_file(cls, file_path: str) -> "Config":
        """
        Load configuration from JSON file.

        Args:
            file_path: Path to JSON configuration file

        Returns:
            Config object with loaded settings

        Raises:
            ValueError: If file doesn't exist or is invalid JSON
        """
        path = Path(file_path)

        if not path.exists():
            raise ValueError(f"Config file not found: {file_path}")

        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")

        return cls(
            provider=data.get("provider", "mock"),
            provider_config=data.get("provider_config", {}),
            parallel=data.get("parallel", True),
            timeout=data.get("timeout", 60),
            verbose=data.get("verbose", False),
            custom_agents=data.get("custom_agents", [])
        )

    def merge_cli_args(
        self,
        provider: Optional[str] = None,
        parallel: Optional[bool] = None,
        timeout: Optional[int] = None,
        verbose: Optional[bool] = None
    ) -> "Config":
        """
        Merge CLI arguments with config file settings.

        CLI arguments override config file values.

        Args:
            provider: CLI provider argument
            parallel: CLI parallel flag
            timeout: CLI timeout value
            verbose: CLI verbose flag

        Returns:
            New Config with merged values
        """
        return Config(
            provider=provider if provider is not None else self.provider,
            provider_config=self.provider_config,
            parallel=parallel if parallel is not None else self.parallel,
            timeout=timeout if timeout is not None else self.timeout,
            verbose=verbose if verbose is not None else self.verbose,
            custom_agents=self.custom_agents
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert config to dictionary.

        Useful for serialization and logging.
        """
        return {
            "provider": self.provider,
            "provider_config": self.provider_config,
            "parallel": self.parallel,
            "timeout": self.timeout,
            "verbose": self.verbose,
            "custom_agents": self.custom_agents
        }