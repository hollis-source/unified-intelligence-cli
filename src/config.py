"""
Configuration management for Unified Intelligence CLI.

Supports JSON config files for runtime provider and agent configuration.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import os


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
    debug: bool = False  # Week 3: Debug mode (LLM calls, tool details)
    orchestrator: str = "simple"  # Week 7: Orchestration mode (simple, openai-agents)

    # Data collection settings (Week 9: Model training pipeline)
    collect_data: bool = False  # Enable passive data collection for fine-tuning
    data_dir: str = "data/training"  # Directory to store collected interactions

    # Agent settings (Week 11: Hierarchical agent scaling)
    agent_mode: str = "default"  # Agent configuration: "default" (5 agents), "extended" (8 agents), "scaled" (12 agents)
    custom_agents: list = field(default_factory=list)

    # Routing settings (Week 12: Team-based routing)
    routing_mode: str = "individual"  # Routing mode: "individual" (agent-based) or "team" (team-based)

    # Metrics settings (Week 13: Monitoring & metrics)
    collect_metrics: bool = False  # Enable metrics collection for monitoring
    metrics_dir: str = "data/metrics"  # Directory to store metrics

    # Prompt Framework settings (Phase 2-5)
    validate_prompts: bool = False
    use_prompt_strategy: bool = False
    prompt_min_score: float = 60.0

    # Prompt Metrics (Phase 4/5)
    collect_prompt_metrics: bool = False
    prompt_metrics_store: str = "none"  # none|memory|surreal
    surreal_url: str = ""
    surreal_namespace: str = ""
    surreal_database: str = ""
    surreal_user: str = ""
    surreal_pass: str = ""

    # Cache settings (Phase 1: Cache control)
    cache_enabled: bool = True
    cache_ttl_seconds: int = 14400  # 4 hours default
    cache_namespace: str = ""

    # RAG settings (RAG Integration)
    enable_rag: bool = False  # Enable RAG for pattern learning and adaptive routing

    # Output validation settings (Week 14: P2.2)
    validate_outputs: bool = False  # Enable post-execution output validation

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
            debug=data.get("debug", False),
            orchestrator=data.get("orchestrator", "simple"),
            collect_data=data.get("collect_data", False),
            data_dir=data.get("data_dir", "data/training"),
            agent_mode=data.get("agent_mode", "default"),
            custom_agents=data.get("custom_agents", []),
            routing_mode=data.get("routing_mode", "individual"),
            collect_metrics=data.get("collect_metrics", False),
            metrics_dir=data.get("metrics_dir", "data/metrics"),
            validate_prompts=data.get("validate_prompts", False),
            use_prompt_strategy=data.get("use_prompt_strategy", False),
            prompt_min_score=float(data.get("prompt_min_score", 60.0)),
            collect_prompt_metrics=data.get("collect_prompt_metrics", False),
            prompt_metrics_store=data.get("prompt_metrics_store", "none"),
            surreal_url=data.get("surreal_url", ""),
            surreal_namespace=data.get("surreal_namespace", ""),
            surreal_database=data.get("surreal_database", ""),
            surreal_user=data.get("surreal_user", ""),
            surreal_pass=data.get("surreal_pass", ""),
            cache_enabled=data.get("cache_enabled", True),
            cache_ttl_seconds=data.get("cache_ttl_seconds", int(os.getenv("ATADO_CACHE_TTL_SECONDS", 14400))),
            cache_namespace=data.get("cache_namespace", os.getenv("ATADO_CACHE_NAMESPACE", "")),
            enable_rag=data.get("enable_rag", False),
            validate_outputs=data.get("validate_outputs", False)
        )

    def merge_cli_args(
        self,
        provider: Optional[str] = None,
        parallel: Optional[bool] = None,
        timeout: Optional[int] = None,
        verbose: Optional[bool] = None,
        debug: Optional[bool] = None,
        orchestrator: Optional[str] = None,
        collect_data: Optional[bool] = None,
        data_dir: Optional[str] = None,
        agent_mode: Optional[str] = None,
        routing_mode: Optional[str] = None,
        collect_metrics: Optional[bool] = None,
        metrics_dir: Optional[str] = None,
        validate_prompts: Optional[bool] = None,
        use_prompt_strategy: Optional[bool] = None,
        prompt_min_score: Optional[float] = None,
        collect_prompt_metrics: Optional[bool] = None,
        prompt_metrics_store: Optional[str] = None,
        surreal_url: Optional[str] = None,
        surreal_namespace: Optional[str] = None,
        surreal_database: Optional[str] = None,
        surreal_user: Optional[str] = None,
        surreal_pass: Optional[str] = None,
        cache_enabled: Optional[bool] = None,
        cache_ttl_seconds: Optional[int] = None,
        cache_namespace: Optional[str] = None,
        enable_rag: Optional[bool] = None,
        validate_outputs: Optional[bool] = None
    ) -> "Config":

        """
        Merge CLI arguments with config file settings.

        CLI arguments override config file values.

        Args:
            provider: CLI provider argument
            parallel: CLI parallel flag
            timeout: CLI timeout value
            verbose: CLI verbose flag
            debug: CLI debug flag (Week 3)
            orchestrator: CLI orchestrator mode (Week 7)
            collect_data: CLI data collection flag (Week 9)
            data_dir: CLI data directory (Week 9)
            agent_mode: CLI agent mode (Week 11)
            routing_mode: CLI routing mode (Week 12)
            collect_metrics: CLI metrics collection flag (Week 13)
            metrics_dir: CLI metrics directory (Week 13)
            validate_prompts: Enable prompt validation (Phase 2)
            use_prompt_strategy: Use PromptStrategy and templates (Phase 2/3)
            prompt_min_score: Min validation score threshold (Phase 2)
            collect_prompt_metrics: Enable prompt metrics logging (Phase 4)
            prompt_metrics_store: Metrics store type (none|surreal|memory) (Phase 4/5)
            surreal_url/namespace/database/user/pass: SurrealDB config (Phase 4/5)
            cache_enabled: Enable/disable cache (Phase 1)
            cache_ttl_seconds: Cache TTL seconds (Phase 1)
            cache_namespace: Cache key namespace/prefix (Phase 1)

        Returns:
            New Config with merged values
        """
        # Resolve env defaults for cache if not provided
        env_cache_enabled = os.getenv("ATADO_CACHE")
        env_cache_ttl = os.getenv("ATADO_CACHE_TTL_SECONDS")
        env_cache_ns = os.getenv("ATADO_CACHE_NAMESPACE")
        # Default: disable cache in prod unless explicitly enabled
        atado_env = os.getenv("ATADO_ENV", "dev")
        resolved_cache_enabled = (
            cache_enabled if cache_enabled is not None
            else (
                (False if atado_env == "prod" and env_cache_enabled is None else self.cache_enabled)
                if env_cache_enabled is None else env_cache_enabled not in ["0", "false", "False"]
            )
        )
        resolved_cache_ttl = int(
            cache_ttl_seconds if cache_ttl_seconds is not None
            else (self.cache_ttl_seconds if env_cache_ttl is None else int(env_cache_ttl))
        )
        resolved_cache_ns = (
            cache_namespace if cache_namespace is not None
            else (self.cache_namespace if env_cache_ns is None else env_cache_ns)
        )

        return Config(
            provider=provider if provider is not None else self.provider,
            provider_config=self.provider_config,
            parallel=parallel if parallel is not None else self.parallel,
            timeout=timeout if timeout is not None else self.timeout,
            verbose=verbose if verbose is not None else self.verbose,
            debug=debug if debug is not None else self.debug,
            orchestrator=orchestrator if orchestrator is not None else self.orchestrator,
            collect_data=collect_data if collect_data is not None else self.collect_data,
            data_dir=data_dir if data_dir is not None else self.data_dir,
            agent_mode=agent_mode if agent_mode is not None else self.agent_mode,
            custom_agents=self.custom_agents,
            routing_mode=routing_mode if routing_mode is not None else self.routing_mode,
            collect_metrics=collect_metrics if collect_metrics is not None else self.collect_metrics,
            metrics_dir=metrics_dir if metrics_dir is not None else self.metrics_dir,
            validate_prompts=validate_prompts if validate_prompts is not None else self.validate_prompts,
            use_prompt_strategy=use_prompt_strategy if use_prompt_strategy is not None else self.use_prompt_strategy,
            prompt_min_score=prompt_min_score if prompt_min_score is not None else self.prompt_min_score,
            collect_prompt_metrics=collect_prompt_metrics if collect_prompt_metrics is not None else self.collect_prompt_metrics,
            prompt_metrics_store=prompt_metrics_store if prompt_metrics_store is not None else self.prompt_metrics_store,
            surreal_url=surreal_url if surreal_url is not None else self.surreal_url,
            surreal_namespace=surreal_namespace if surreal_namespace is not None else self.surreal_namespace,
            surreal_database=surreal_database if surreal_database is not None else self.surreal_database,
            surreal_user=surreal_user if surreal_user is not None else self.surreal_user,
            surreal_pass=surreal_pass if surreal_pass is not None else self.surreal_pass,
            cache_enabled=resolved_cache_enabled,
            cache_ttl_seconds=resolved_cache_ttl,
            cache_namespace=resolved_cache_ns,
            enable_rag=enable_rag if enable_rag is not None else self.enable_rag,
            validate_outputs=validate_outputs if validate_outputs is not None else self.validate_outputs
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
            "debug": self.debug,
            "orchestrator": self.orchestrator,
            "collect_data": self.collect_data,
            "data_dir": self.data_dir,
            "agent_mode": self.agent_mode,
            "custom_agents": self.custom_agents,
            "routing_mode": self.routing_mode,
            "collect_metrics": self.collect_metrics,
            "metrics_dir": self.metrics_dir,
            "validate_prompts": self.validate_prompts,
            "use_prompt_strategy": self.use_prompt_strategy,
            "prompt_min_score": self.prompt_min_score,
            "collect_prompt_metrics": self.collect_prompt_metrics,
            "prompt_metrics_store": self.prompt_metrics_store,
            "surreal_url": self.surreal_url,
            "surreal_namespace": self.surreal_namespace,
            "surreal_database": self.surreal_database,
            "surreal_user": self.surreal_user,
            "surreal_pass": self.surreal_pass,
            "cache_enabled": self.cache_enabled,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "cache_namespace": self.cache_namespace,
            "enable_rag": self.enable_rag,
            "validate_outputs": self.validate_outputs
        }