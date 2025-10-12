"""Generate Next Todos from priorities.yaml.

Clean, small functions with explicit error handling.
"""
from __future__ import annotations

from pathlib import Path
from datetime import date
from typing import List, Dict, Any
import yaml

_PRIORITY_MAP = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def load_priorities(file_path: str) -> Dict[str, Any]:
    """Load priorities YAML into a dict."""
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Priority file not found: {file_path}")
    try:
        with p.open() as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML: {e}")
    return data


def select_top_open_priorities(data: Dict[str, Any], top_n: int = 5) -> List[Dict[str, Any]]:
    """Select top-N open priorities sorted by priority severity then effort."""
    items = [i for i in (data.get("priorities") or []) if i.get("status") == "open"]
    def key(it: Dict[str, Any]):
        sev = _PRIORITY_MAP.get(str(it.get("priority", "low")).lower(), 0)
        eff = it.get("effort_hours") or 999
        return (-sev, eff)
    items.sort(key=key)
    return items[: max(0, top_n)]


def format_next_todos(priorities: List[Dict[str, Any]], date_str: str | None = None) -> str:
    """Format a concise markdown with next todos."""
    d = date_str or date.today().isoformat()
    lines = ["# Next Todos", "", f"Date: {d}", "Reference: priorities.yaml", ""]
    for it in priorities:
        title = it.get("title", "Untitled")
        pr = str(it.get("priority", "low")).capitalize()
        eff = it.get("effort_hours", "?")
        desc = (it.get("description") or "").strip().splitlines()[0:1]
        lines.append(f"- {title} — {pr} (Effort: {eff}h)")
        if desc:
            lines.append(f"  - {desc[0]}")
    return "\n".join(lines) + "\n"


def write_next_todos(output_path: str, content: str) -> None:
    """Write rendered markdown to file, creating parent dir if needed."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content)




def generate_next_todos(priorities_path: str, output_path: str, top_n: int = 5, date_str: str | None = None) -> str:
    """Generate NEXT_TODOS.md from a priorities YAML file.

    Pipeline: load → select → format → write. Returns the output path.
    """
    data = load_priorities(priorities_path)
    top = select_top_open_priorities(data, top_n=top_n)
    md = format_next_todos(top, date_str=date_str)
    write_next_todos(output_path, md)
    return output_path
