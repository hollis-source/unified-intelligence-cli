import json
import os
from pathlib import Path
from src.adapters.cli.claude_settings import load_claude_settings, ClaudeOutputSettings


def test_defaults_when_no_file(monkeypatch):
    # Ensure env not set
    monkeypatch.delenv('CLAUDE_SETTINGS_PATH', raising=False)
    s = load_claude_settings(cli_path=None)
    assert isinstance(s, ClaudeOutputSettings)
    assert s.redact_thoughts is True
    assert s.verbosity == 'normal'


def test_env_path_overrides_default(monkeypatch, tmp_path):
    cfg = {"output": {"verbosity": "verbose", "redact_thoughts": False}}
    p = tmp_path / 'env_settings.json'
    p.write_text(json.dumps(cfg))
    monkeypatch.setenv('CLAUDE_SETTINGS_PATH', str(p))
    s = load_claude_settings(cli_path=None)
    assert s.verbosity == 'verbose'
    assert s.redact_thoughts is False


def test_cli_path_overrides_env(monkeypatch, tmp_path):
    env_cfg = {"output": {"verbosity": "normal"}}
    cli_cfg = {"output": {"verbosity": "debug"}}
    env_p = tmp_path / 'env.json'
    cli_p = tmp_path / 'cli.json'
    env_p.write_text(json.dumps(env_cfg))
    cli_p.write_text(json.dumps(cli_cfg))
    monkeypatch.setenv('CLAUDE_SETTINGS_PATH', str(env_p))
    s = load_claude_settings(cli_path=str(cli_p))
    assert s.verbosity == 'debug'

