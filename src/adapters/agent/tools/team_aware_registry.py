"""Team-aware Tool Registry wrapper.

Clean Architecture: Adapter that decorates ToolRegistry to enforce team policies.
SOLID: SRP (filtering only), DIP (depends on ToolRegistry abstraction), OCP (extends behavior via composition).

Security posture: allowlist per team (secure-by-default). Unknown team => no tools.
Logs policy violations with clear messages; never silently fails.
"""
from __future__ import annotations

import logging
from threading import RLock
from typing import Dict, List, Optional

from .base import AgentTool
from .registry import ToolRegistry


logger = logging.getLogger(__name__)


class TeamAwareToolRegistry:
    """A wrapper around ToolRegistry that filters tools by team policy.

    Usage patterns:
    - Pass team_name per method call for explicit control
    - Optionally set a default_team_name at construction for convenience
    """

    def __init__(
        self,
        base_registry: ToolRegistry,
        team_policies: Dict[str, List[str]] | None = None,
        default_team_name: Optional[str] = None,
    ) -> None:
        if not isinstance(base_registry, ToolRegistry):
            raise TypeError("base_registry must be a ToolRegistry instance")
        self._base = base_registry
        # Copy policies defensively for thread-safety
        self._policies: Dict[str, List[str]] = {k: list(v) for k, v in (team_policies or {}).items()}
        self._default_team = default_team_name
        self._lock = RLock()

    # ---- Policy management ----
    def is_tool_allowed(self, tool_name: str, team_name: Optional[str] = None) -> bool:
        """Check if tool is allowed for a team.

        Secure-by-default: returns False if team not found or policy empty.
        """
        team = team_name or self._default_team
        if not team:
            return False
        with self._lock:
            allowed = self._policies.get(team)
            if not allowed:
                return False
            return tool_name in allowed

    def set_team_policy(self, team_name: str, allowed_tools: List[str]) -> None:
        """Atomically set policy for a team."""
        with self._lock:
            self._policies[team_name] = list(allowed_tools)

    def update_team_policies(self, team_policies: Dict[str, List[str]]) -> None:
        """Replace entire policy mapping atomically."""
        with self._lock:
            self._policies = {k: list(v) for k, v in team_policies.items()}

    # ---- Tool accessors ----
    def get_tool(self, tool_name: str, team_name: Optional[str] = None) -> Optional[AgentTool]:
        """Get tool only if allowed for team; returns None otherwise.

        Logs a warning on policy violation or unknown team/tool.
        """
        if not self.is_tool_allowed(tool_name, team_name):
            team = team_name or self._default_team or "<unset>"
            # Differentiate unknown team vs disallowed tool
            with self._lock:
                known_team = team in self._policies
            if not known_team:
                logger.warning(
                    "TeamAwareToolRegistry: unknown team attempted tool access",
                    extra={"extra_fields": {"team": team, "tool": tool_name, "event": "unknown_team"}},
                )
            else:
                logger.warning(
                    "TeamAwareToolRegistry: tool not allowed for team",
                    extra={"extra_fields": {"team": team, "tool": tool_name, "event": "policy_denied"}},
                )
            return None

        tool = self._base.get_tool(tool_name)
        if tool is None:
            logger.warning(
                "TeamAwareToolRegistry: requested tool does not exist",
                extra={"extra_fields": {"team": team_name or self._default_team or "<unset>", "tool": tool_name, "event": "unknown_tool"}},
            )
        return tool

    def get_tool_descriptions(self, team_name: Optional[str] = None) -> str:
        """Get LLM-formatted descriptions for tools allowed to the team.

        Follows the same format as ToolRegistry.get_tool_descriptions().
        Returns empty string for unknown team or no allowed tools.
        """
        team = team_name or self._default_team
        if not team:
            return ""
        with self._lock:
            allowed = list(self._policies.get(team, []))
        parts: List[str] = []
        for name in allowed:
            tool = self._base.get_tool(name)
            if not tool:
                # Skip missing tools but log for visibility
                logger.warning(
                    "TeamAwareToolRegistry: allowed tool missing in base registry",
                    extra={"extra_fields": {"team": team, "tool": name, "event": "missing_base_tool"}},
                )
                continue
            parts.append(
                f"Tool: {tool.name}\n"
                f"Description: {tool.description}\n"
                f"Parameters: {tool.parameters}\n"
            )
        return "\n".join(parts)

    # ---- Introspection helpers ----
    def list_allowed_tools(self, team_name: Optional[str] = None) -> List[str]:
        """List allowed tool names for the team (sorted)."""
        team = team_name or self._default_team
        if not team:
            return []
        with self._lock:
            allowed = self._policies.get(team, [])
            return sorted(allowed)

