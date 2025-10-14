"""FileReaderTool: safe file reading with size and line limits."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .base import AgentTool

DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


class FileReaderTool(AgentTool):
    name = "read_file"
    description = "Read contents of a text file under the workspace root with optional line limit."

    def __init__(self, base_dir: Optional[Path] = None, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.max_bytes = max_bytes

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to file (absolute or relative to workspace)"},
                "max_lines": {"type": "integer", "description": "Max lines to read", "default": 10000},
            },
            "required": ["file_path"],
        }

    def _resolve_and_validate(self, file_path: str) -> Path:
        p = Path(file_path)
        if not p.is_absolute():
            p = (self.base_dir / p).resolve()
        else:
            p = p.resolve()
        # Prevent path escape outside base_dir
        base = self.base_dir.resolve()
        if str(p)[: len(str(base))] != str(base):
            raise ValueError("File path escapes workspace root")
        return p

    def execute(self, **kwargs: Any) -> str:
        file_path = kwargs.get("file_path")
        max_lines = int(kwargs.get("max_lines", 10000))
        try:
            path = self._resolve_and_validate(str(file_path))
            if not path.exists() or not path.is_file():
                return f"Error reading file: File not found: {path}"
            size = path.stat().st_size
            if size > self.max_bytes:
                return (
                    f"Error reading file: File too large ({size} bytes exceeds {self.max_bytes} byte limit)"
                )
            # Read with line cap
            with path.open("r", encoding="utf-8", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line)
            content = "".join(lines)
            if max_lines and sum(1 for _ in content.splitlines()) >= max_lines:
                return content + "\n...[truncated]\n"
            return content
        except Exception as e:  # Return error as string per spec
            return f"Error reading file: {e}"

