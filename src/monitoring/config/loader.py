"""Configuration loader for endpoint monitoring daemon.

Loads YAML configuration and converts to domain entities.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import yaml

from ..entities import (
    Endpoint,
    FallbackChain,
    EndpointPriority,
    WakeStrategy,
    HealthStatus,
    EndpointState,
)
from datetime import datetime


@dataclass
class MonitoringConfig:
    """Parsed monitoring configuration.

    Contains all domain entities needed to run the daemon.
    """

    endpoints: Dict[str, Endpoint]
    fallback_chains: Dict[str, FallbackChain]
    health_statuses: Dict[str, HealthStatus]


class ConfigLoader:
    """Loads and parses endpoint monitoring configuration from YAML.

    Fail-fast validation: Errors during parsing raise exceptions immediately.
    This ensures daemon only runs with valid configuration.
    """

    @staticmethod
    def load_from_file(config_path: str) -> MonitoringConfig:
        """Load configuration from YAML file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            MonitoringConfig with parsed entities

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
            ValueError: If configuration is invalid
        """
        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_file) as f:
            raw_config = yaml.safe_load(f)

        return ConfigLoader._parse_config(raw_config)

    @staticmethod
    def _parse_config(raw_config: dict) -> MonitoringConfig:
        """Parse raw YAML dict into domain entities.

        Args:
            raw_config: Raw configuration dictionary from YAML

        Returns:
            MonitoringConfig with validated entities

        Raises:
            ValueError: If configuration is invalid
        """
        # Parse endpoints
        endpoints = {}
        for endpoint_id, endpoint_data in raw_config.get("endpoints", {}).items():
            endpoint = ConfigLoader._parse_endpoint(endpoint_id, endpoint_data)
            endpoints[endpoint_id] = endpoint

        # Parse fallback chains
        fallback_chains = {}
        for chain_name, chain_data in raw_config.get("fallback_chains", {}).items():
            chain = ConfigLoader._parse_fallback_chain(chain_name, chain_data)
            fallback_chains[chain_name] = chain

        # Initialize health statuses for all endpoints
        health_statuses = {}
        for endpoint_id in endpoints.keys():
            health_statuses[endpoint_id] = HealthStatus(
                endpoint_id=endpoint_id,
                state=EndpointState.UNKNOWN,
                last_check_time=datetime.now(),
            )

        return MonitoringConfig(
            endpoints=endpoints,
            fallback_chains=fallback_chains,
            health_statuses=health_statuses,
        )

    @staticmethod
    def _parse_endpoint(endpoint_id: str, data: dict) -> Endpoint:
        """Parse endpoint data into Endpoint entity.

        Args:
            endpoint_id: Unique endpoint identifier
            data: Endpoint configuration data

        Returns:
            Validated Endpoint entity

        Raises:
            ValueError: If endpoint data is invalid
        """
        # Parse priority enum
        priority_str = data.get("priority", "MEDIUM").upper()
        try:
            priority = EndpointPriority[priority_str]
        except KeyError:
            raise ValueError(
                f"Invalid priority '{priority_str}' for endpoint {endpoint_id}. "
                f"Valid values: {[p.name for p in EndpointPriority]}"
            )

        # Parse wake strategy enum
        wake_strategy_str = data.get("wake_strategy", "PRIORITY_BASED").upper()
        try:
            wake_strategy = WakeStrategy[wake_strategy_str]
        except KeyError:
            raise ValueError(
                f"Invalid wake_strategy '{wake_strategy_str}' for endpoint {endpoint_id}. "
                f"Valid values: {[w.name for w in WakeStrategy]}"
            )

        # Endpoint entity validates required fields and formats
        return Endpoint(
            id=endpoint_id,
            provider=data["provider"],  # Required
            url=data["url"],  # Required
            priority=priority,
            wake_strategy=wake_strategy,
            auth_config=data.get("auth_config", {}),
            health_check_interval=data.get("health_check_interval"),
            wake_timeout=data.get("wake_timeout", 90),
            fallback_endpoint_id=data.get("fallback_endpoint_id"),
        )

    @staticmethod
    def _parse_fallback_chain(chain_name: str, data: dict) -> FallbackChain:
        """Parse fallback chain data into FallbackChain entity.

        Args:
            chain_name: Unique chain identifier
            data: Fallback chain configuration data

        Returns:
            Validated FallbackChain entity

        Raises:
            ValueError: If chain data is invalid
        """
        # FallbackChain entity validates required fields and self-references
        return FallbackChain(
            name=chain_name,
            primary_endpoint_id=data["primary_endpoint_id"],  # Required
            secondary_endpoint_id=data.get("secondary_endpoint_id"),
            tertiary_endpoint_id=data.get("tertiary_endpoint_id"),
        )
