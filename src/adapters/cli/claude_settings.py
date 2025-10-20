"""
Claude/Auggie Output Hooks settings and loader.

Deterministic, configuration-driven output behavior for assistant-facing rendering.
Precedence: CLI/session path > ENV (CLAUDE_SETTINGS_PATH) > file (config/claude_settings.json) > defaults.

No global mutable state: call load_claude_settings() and pass result to formatters.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional, Dict, Any
import json
import os
from pathlib import Path


Verbosity = Literal["quiet", "normal", "verbose", "debug"]
WrapMode = Literal["none", "fenced", "augment_code_snippet"]
TraceFormat = Literal["human", "json", "both"]


@dataclass(frozen=True)
class ClaudeOutputSettings:
    # Output
    redact_thoughts: bool = True
    thought_tag_names: List[str] = field(default_factory=lambda: ["think"])  # case-sensitive
    verbosity: Verbosity = "normal"
    max_chars: int = 0  # 0 = unlimited
    wrap_code_blocks: WrapMode = "augment_code_snippet"
    inline_code_allowed: bool = True

    include_routing_trace: bool = True
    show_top3_domain_scores: bool = True
    include_correlation_id: bool = True
    show_cache_annotations: bool = True

    # Pointers/banners
    quickstart_pointer_enabled: bool = True
    dogfooding_banner_enabled: bool = True

    # Routing trace formatting
    routing_trace_format: TraceFormat = "both"

    @staticmethod
    def defaults() -> "ClaudeOutputSettings":
        return ClaudeOutputSettings()


DEFAULT_SETTINGS_PATH = Path("config/claude_settings.json")
ENV_SETTINGS_PATH = "CLAUDE_SETTINGS_PATH"


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _to_dataclass(flat: Dict[str, Any]) -> ClaudeOutputSettings:
    # Map nested keys like output.redact_thoughts -> constructor args
    output = flat.get("output", {})
    docs = flat.get("docs", {})
    dog = flat.get("dogfooding", {})
    routing = flat.get("routing", {})

    return ClaudeOutputSettings(
        redact_thoughts=bool(output.get("redact_thoughts", True)),
        thought_tag_names=list(output.get("thought_tag_names", ["think"])),
        verbosity=str(output.get("verbosity", "normal")),
        max_chars=int(output.get("max_chars", 0)),
        wrap_code_blocks=str(output.get("wrap_code_blocks", "augment_code_snippet")),
        inline_code_allowed=bool(output.get("inline_code_allowed", True)),
        include_routing_trace=bool(output.get("include_routing_trace", True)),
        show_top3_domain_scores=bool(output.get("show_top3_domain_scores", True)),
        include_correlation_id=bool(output.get("include_correlation_id", True)),
        show_cache_annotations=bool(output.get("show_cache_annotations", True)),
        quickstart_pointer_enabled=bool(docs.get("quickstart_pointer_enabled", True)),
        dogfooding_banner_enabled=bool(dog.get("banner_enabled", True)),
        routing_trace_format=str(routing.get("trace_format", "both")),
    )


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r") as f:
            return json.load(f)
    except Exception:
        # Invalid file -> ignore and fall back to defaults
        return {}


def load_claude_settings(cli_path: Optional[str] = None) -> ClaudeOutputSettings:
    """Load settings with precedence: CLI > ENV > File > Defaults.

    Args:
        cli_path: Optional CLI/session-provided path to settings JSON
    Returns:
        Frozen ClaudeOutputSettings instance
    """
    defaults = ClaudeOutputSettings.defaults()

    # File (base)
    file_path = DEFAULT_SETTINGS_PATH
    env_path = os.getenv(ENV_SETTINGS_PATH)

    if env_path:
        file_path = Path(env_path)
    if cli_path:
        file_path = Path(cli_path)

    file_settings = _load_json(file_path)

    # ENV per-key overrides (flat – kept minimal to avoid complexity). If needed, add later.
    # Precedence merge: defaults <- file <- env-flat <- cli-flat (cli_path only affects file_path)
    merged = _deep_merge(defaults_to_dict(defaults), file_settings)

    return _to_dataclass(merged)


def defaults_to_dict(settings: ClaudeOutputSettings) -> Dict[str, Any]:
    return {
        "output": {
            "redact_thoughts": settings.redact_thoughts,
            "thought_tag_names": settings.thought_tag_names,
            "verbosity": settings.verbosity,
            "max_chars": settings.max_chars,
            "wrap_code_blocks": settings.wrap_code_blocks,
            "inline_code_allowed": settings.inline_code_allowed,
            "include_routing_trace": settings.include_routing_trace,
            "show_top3_domain_scores": settings.show_top3_domain_scores,
            "include_correlation_id": settings.include_correlation_id,
            "show_cache_annotations": settings.show_cache_annotations,
        },
        "docs": {
            "quickstart_pointer_enabled": settings.quickstart_pointer_enabled,
        },
        "dogfooding": {
            "banner_enabled": settings.dogfooding_banner_enabled,
        },
        "routing": {
            "trace_format": settings.routing_trace_format,
        },
    }

