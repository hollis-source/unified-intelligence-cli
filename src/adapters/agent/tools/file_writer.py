"""FileWriterTool: safe file writer with path validation."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .base import AgentTool


class FileWriterTool(AgentTool):
    name = "write_file"
    description = "Write text content to a file under the workspace root. Creates parent dirs if needed."

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to file (absolute or relative to workspace)"},
                "content": {"type": "string", "description": "Text content to write"},
            },
            "required": ["file_path", "content"],
        }

    def _resolve_and_validate(self, file_path: str) -> Path:
        p = Path(file_path)
        if not p.is_absolute():
            p = (self.base_dir / p).resolve()
        else:
            p = p.resolve()
        base = self.base_dir.resolve()
        if str(p)[: len(str(base))] != str(base):
            raise ValueError("File path escapes workspace root")
        return p

    def execute(self, **kwargs: Any) -> str:
        file_path = kwargs.get("file_path")
        content = kwargs.get("content", "")
        try:
            path = self._resolve_and_validate(str(file_path))
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                f.write(str(content))
            return f"Successfully wrote {len(str(content))} chars to {path}"
        except Exception as e:
            return f"Error writing file: {e}"

