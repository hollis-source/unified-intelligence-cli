import os
import importlib.util
from pathlib import Path


def load_auto_delegate_module():
    path = Path('.claude/hooks/auto_delegate.py')
    spec = importlib.util.spec_from_file_location('auto_delegate', str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    return module


def test_build_ssh_command_without_jump(monkeypatch, tmp_path):
    m = load_auto_delegate_module()

    # Patch module-level constants for predictable output
    monkeypatch.setattr(m, 'SSH_HOST', 'root@10.0.0.1', raising=False)
    monkeypatch.setattr(m, 'SSH_KEY', '/home/test/.ssh/id_ed25519', raising=False)
    monkeypatch.setattr(m, 'AUGGIE_NODE', '/opt/node/bin/node', raising=False)
    monkeypatch.setattr(m, 'AUGGIE_CLI', '/opt/node/bin/auggie', raising=False)

    # Ensure no jump host
    monkeypatch.delenv('SSH_JUMP_HOST', raising=False)

    task_file = str(tmp_path / '.auggie_task_123.txt')
    cmd = m.build_auggie_ssh_command(task_file)

    assert cmd.startswith('ssh -i /home/test/.ssh/id_ed25519 root@10.0.0.1 "cd /home/ui-cli_jake/unified-intelligence-cli')
    assert f"'Read and execute {task_file}'" in cmd


def test_build_ssh_command_with_jump(monkeypatch, tmp_path):
    m = load_auto_delegate_module()

    # Patch module-level constants for predictable output
    monkeypatch.setattr(m, 'SSH_HOST', 'root@10.0.0.2', raising=False)
    monkeypatch.setattr(m, 'SSH_KEY', '/home/test/.ssh/id_ed25519', raising=False)
    monkeypatch.setattr(m, 'AUGGIE_NODE', '/opt/node/bin/node', raising=False)
    monkeypatch.setattr(m, 'AUGGIE_CLI', '/opt/node/bin/auggie', raising=False)

    # Set jump host to syd2
    monkeypatch.setenv('SSH_JUMP_HOST', 'syd2')

    task_file = str(tmp_path / '.auggie_task_456.txt')
    cmd = m.build_auggie_ssh_command(task_file)

    assert cmd.startswith('ssh -J syd2 -i /home/test/.ssh/id_ed25519 root@10.0.0.2 "cd /home/ui-cli_jake/unified-intelligence-cli')
    assert f"'Read and execute {task_file}'" in cmd

