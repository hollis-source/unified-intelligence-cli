"""BashExecutorTool: execute bash commands with timeout and cwd sandbox."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from .base import AgentTool


class BashExecutorTool(AgentTool):
    name = "bash"
    description = "Execute a bash command in the workspace directory with timeout. Returns stdout/stderr."

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Bash command to run"},
                "timeout": {"type": "integer", "description": "Timeout seconds", "default": 30},
            },
            "required": ["command"],
        }

    def execute(self, **kwargs: Any) -> str:
        command = kwargs.get("command", "")
        timeout = int(kwargs.get("timeout", 30))
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return f"Error executing command: Timeout after {timeout}s"
        except Exception as e:
            return f"Error executing command: {e}"

