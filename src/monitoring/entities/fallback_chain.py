"""Fallback chain entity - defines fallback routing between endpoints."""

from dataclasses import dataclass
from typing import Optional, List


@dataclass(frozen=True)
class FallbackChain:
    """Defines fallback routing for an endpoint.

    Represents a chain of endpoints to try in order: primary → secondary → tertiary.
    Immutable to ensure thread-safety and consistent behavior.

    Attributes:
        name: Descriptive name for this fallback chain (e.g., "qwen3-production")
        primary_endpoint_id: ID of primary endpoint (tried first)
        secondary_endpoint_id: ID of secondary endpoint (tried if primary fails)
        tertiary_endpoint_id: ID of tertiary endpoint (tried if secondary fails)

    Example:
        chain = FallbackChain(
            name="qwen3-production",
            primary_endpoint_id="qwen3-primary",
            secondary_endpoint_id="qwen3-secondary",
            tertiary_endpoint_id="qwen3-tertiary"
        )
    """

    name: str
    primary_endpoint_id: str
    secondary_endpoint_id: Optional[str] = None
    tertiary_endpoint_id: Optional[str] = None

    def __post_init__(self):
        """Validate fallback chain configuration at creation time."""
        if not self.name or not self.name.strip():
            raise ValueError("Fallback chain name cannot be empty")

        if not self.primary_endpoint_id or not self.primary_endpoint_id.strip():
            raise ValueError("Primary endpoint ID cannot be empty")

        # Validate no self-references
        if self.secondary_endpoint_id == self.primary_endpoint_id:
            raise ValueError("Secondary endpoint cannot be same as primary")

        if self.tertiary_endpoint_id == self.primary_endpoint_id:
            raise ValueError("Tertiary endpoint cannot be same as primary")

        if (self.secondary_endpoint_id and self.tertiary_endpoint_id and
                self.tertiary_endpoint_id == self.secondary_endpoint_id):
            raise ValueError("Tertiary endpoint cannot be same as secondary")

    def get_endpoints(self) -> List[str]:
        """Get all endpoint IDs in the chain (in order).

        Returns:
            List of endpoint IDs (primary, secondary, tertiary) excluding None values
        """
        endpoints = [self.primary_endpoint_id]

        if self.secondary_endpoint_id:
            endpoints.append(self.secondary_endpoint_id)

        if self.tertiary_endpoint_id:
            endpoints.append(self.tertiary_endpoint_id)

        return endpoints

    def get_next_endpoint(self, current_endpoint_id: str) -> Optional[str]:
        """Get next endpoint in fallback chain after current.

        Args:
            current_endpoint_id: ID of current endpoint (that failed)

        Returns:
            ID of next endpoint to try, or None if end of chain

        Example:
            chain = FallbackChain(primary="A", secondary="B", tertiary="C")
            chain.get_next_endpoint("A")  # Returns "B"
            chain.get_next_endpoint("B")  # Returns "C"
            chain.get_next_endpoint("C")  # Returns None
        """
        if current_endpoint_id == self.primary_endpoint_id:
            return self.secondary_endpoint_id

        if current_endpoint_id == self.secondary_endpoint_id:
            return self.tertiary_endpoint_id

        # Current endpoint not in chain or already at end
        return None

    def has_fallback(self) -> bool:
        """Check if chain has any fallback endpoints (not just primary)."""
        return self.secondary_endpoint_id is not None

    def chain_length(self) -> int:
        """Get length of fallback chain (number of endpoints)."""
        return len(self.get_endpoints())

    def __str__(self) -> str:
        """Human-readable string representation."""
        endpoints = " → ".join(self.get_endpoints())
        return f"FallbackChain({self.name}: {endpoints})"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"FallbackChain(name={self.name!r}, primary={self.primary_endpoint_id!r}, "
            f"secondary={self.secondary_endpoint_id!r}, tertiary={self.tertiary_endpoint_id!r})"
        )
