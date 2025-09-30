"""Unit tests for configuration management."""

import json
import pytest
from pathlib import Path
from src.config import Config


class TestConfig:
    """Test Config class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()

        assert config.provider == "mock"
        assert config.parallel is True
        assert config.timeout == 60
        assert config.verbose is False
        assert config.provider_config == {}
        assert config.custom_agents == []

    def test_config_from_dict(self):
        """Test creating config with custom values."""
        config = Config(
            provider="grok",
            parallel=False,
            timeout=120,
            verbose=True
        )

        assert config.provider == "grok"
        assert config.parallel is False
        assert config.timeout == 120
        assert config.verbose is True

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = Config(provider="grok", timeout=90)
        config_dict = config.to_dict()

        assert config_dict["provider"] == "grok"
        assert config_dict["timeout"] == 90
        assert config_dict["parallel"] is True  # default
        assert "verbose" in config_dict

    def test_merge_cli_args_overrides(self):
        """Test CLI args override config file values."""
        config = Config(provider="mock", verbose=False, timeout=60)

        merged = config.merge_cli_args(
            provider="grok",
            verbose=True,
            timeout=120
        )

        assert merged.provider == "grok"
        assert merged.verbose is True
        assert merged.timeout == 120

    def test_merge_cli_args_partial_override(self):
        """Test partial CLI arg override (some None)."""
        config = Config(provider="mock", verbose=False, timeout=60)

        merged = config.merge_cli_args(
            provider="grok",
            verbose=None,  # Keep config value
            timeout=None   # Keep config value
        )

        assert merged.provider == "grok"
        assert merged.verbose is False  # From config
        assert merged.timeout == 60     # From config


class TestConfigFromFile:
    """Test loading config from JSON files."""

    def test_from_file_valid_json(self, tmp_path):
        """Test loading valid JSON config file."""
        config_file = tmp_path / "config.json"
        config_data = {
            "provider": "grok",
            "provider_config": {"model": "grok-code-fast-1"},
            "parallel": False,
            "timeout": 120,
            "verbose": True,
            "custom_agents": [
                {"role": "security", "capabilities": ["audit", "pentest"]}
            ]
        }

        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        config = Config.from_file(str(config_file))

        assert config.provider == "grok"
        assert config.provider_config == {"model": "grok-code-fast-1"}
        assert config.parallel is False
        assert config.timeout == 120
        assert config.verbose is True
        assert len(config.custom_agents) == 1

    def test_from_file_minimal_json(self, tmp_path):
        """Test loading JSON with only some fields."""
        config_file = tmp_path / "config.json"
        config_data = {"provider": "grok"}

        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        config = Config.from_file(str(config_file))

        assert config.provider == "grok"
        # Defaults
        assert config.parallel is True
        assert config.timeout == 60
        assert config.verbose is False

    def test_from_file_not_found(self):
        """Test loading non-existent config file."""
        with pytest.raises(ValueError, match="Config file not found"):
            Config.from_file("/nonexistent/config.json")

    def test_from_file_invalid_json(self, tmp_path):
        """Test loading invalid JSON."""
        config_file = tmp_path / "bad_config.json"

        with open(config_file, 'w') as f:
            f.write("{ invalid json }")

        with pytest.raises(ValueError, match="Invalid JSON"):
            Config.from_file(str(config_file))

    def test_from_file_with_cli_merge(self, tmp_path):
        """Test loading config file and merging with CLI args."""
        config_file = tmp_path / "config.json"
        config_data = {
            "provider": "mock",
            "timeout": 60,
            "verbose": False
        }

        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        config = Config.from_file(str(config_file))
        merged = config.merge_cli_args(
            provider="grok",  # Override
            verbose=True      # Override
            # timeout stays 60
        )

        assert merged.provider == "grok"
        assert merged.verbose is True
        assert merged.timeout == 60  # From file