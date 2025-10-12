"""Unit tests for FallbackChain entity."""

import pytest
from src.monitoring.entities import FallbackChain


class TestFallbackChainCreation:
    """Tests for FallbackChain creation and validation."""

    def test_create_simple_chain(self):
        """Test creating chain with primary and secondary only."""
        chain = FallbackChain(
            name="test-chain",
            primary_endpoint_id="primary",
            secondary_endpoint_id="secondary",
        )

        assert chain.name == "test-chain"
        assert chain.primary_endpoint_id == "primary"
        assert chain.secondary_endpoint_id == "secondary"
        assert chain.tertiary_endpoint_id is None

    def test_create_full_chain(self):
        """Test creating chain with all three endpoints."""
        chain = FallbackChain(
            name="test-chain",
            primary_endpoint_id="primary",
            secondary_endpoint_id="secondary",
            tertiary_endpoint_id="tertiary",
        )

        assert chain.tertiary_endpoint_id == "tertiary"

    def test_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            FallbackChain(
                name="",
                primary_endpoint_id="primary",
            )

    def test_self_reference_secondary_raises_error(self):
        """Test that secondary = primary raises ValueError."""
        with pytest.raises(ValueError, match="cannot be same as primary"):
            FallbackChain(
                name="test",
                primary_endpoint_id="primary",
                secondary_endpoint_id="primary",  # Same as primary!
            )


class TestFallbackChainMethods:
    """Tests for FallbackChain methods."""

    def test_get_endpoints_full_chain(self):
        """Test get_endpoints with full chain."""
        chain = FallbackChain(
            name="test",
            primary_endpoint_id="A",
            secondary_endpoint_id="B",
            tertiary_endpoint_id="C",
        )

        assert chain.get_endpoints() == ["A", "B", "C"]

    def test_get_endpoints_partial_chain(self):
        """Test get_endpoints with only primary and secondary."""
        chain = FallbackChain(
            name="test",
            primary_endpoint_id="A",
            secondary_endpoint_id="B",
        )

        assert chain.get_endpoints() == ["A", "B"]

    def test_get_next_endpoint_from_primary(self):
        """Test get_next_endpoint from primary."""
        chain = FallbackChain(
            name="test",
            primary_endpoint_id="A",
            secondary_endpoint_id="B",
            tertiary_endpoint_id="C",
        )

        assert chain.get_next_endpoint("A") == "B"

    def test_get_next_endpoint_from_secondary(self):
        """Test get_next_endpoint from secondary."""
        chain = FallbackChain(
            name="test",
            primary_endpoint_id="A",
            secondary_endpoint_id="B",
            tertiary_endpoint_id="C",
        )

        assert chain.get_next_endpoint("B") == "C"

    def test_get_next_endpoint_from_tertiary(self):
        """Test get_next_endpoint from tertiary (end of chain)."""
        chain = FallbackChain(
            name="test",
            primary_endpoint_id="A",
            secondary_endpoint_id="B",
            tertiary_endpoint_id="C",
        )

        assert chain.get_next_endpoint("C") is None

    def test_has_fallback_true(self):
        """Test has_fallback returns True when secondary exists."""
        chain = FallbackChain(
            name="test",
            primary_endpoint_id="A",
            secondary_endpoint_id="B",
        )

        assert chain.has_fallback() is True

    def test_has_fallback_false(self):
        """Test has_fallback returns False with only primary."""
        chain = FallbackChain(
            name="test",
            primary_endpoint_id="A",
        )

        assert chain.has_fallback() is False

    def test_chain_length(self):
        """Test chain_length calculation."""
        chain = FallbackChain(
            name="test",
            primary_endpoint_id="A",
            secondary_endpoint_id="B",
            tertiary_endpoint_id="C",
        )

        assert chain.chain_length() == 3
