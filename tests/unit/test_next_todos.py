import textwrap
from pathlib import Path
import yaml
from datetime import date

from src.utils.next_todos import (
    load_priorities,
    select_top_open_priorities,
    format_next_todos,
    write_next_todos,
)


def make_sample_priorities(tmp_path: Path) -> Path:
    data = {
        "priorities": [
            {
                "id": "a",
                "title": "Critical task",
                "description": "Do critical thing",
                "status": "open",
                "priority": "critical",
                "effort_hours": 5,
            },
            {
                "id": "b",
                "title": "Medium task",
                "description": "Do medium thing",
                "status": "open",
                "priority": "medium",
                "effort_hours": 3,
            },
            {
                "id": "c",
                "title": "Closed task",
                "description": "Already done",
                "status": "completed",
                "priority": "high",
                "effort_hours": 2,
            },
            {
                "id": "d",
                "title": "High task",
                "description": "Do high thing",
                "status": "open",
                "priority": "high",
                "effort_hours": 2,
            },
        ]
    }
    p = tmp_path / "priorities.yaml"
    p.write_text(yaml.safe_dump(data))
    return p


def test_select_top_open_priorities_sorts_and_limits(tmp_path):
    pf = make_sample_priorities(tmp_path)
    data = load_priorities(str(pf))
    top = select_top_open_priorities(data, top_n=2)

    # Expect two items, critical first, then high
    assert len(top) == 2
    assert top[0]["title"] == "Critical task"
    assert top[1]["title"] == "High task"


def test_format_next_todos_structure(tmp_path):
    pf = make_sample_priorities(tmp_path)
    data = load_priorities(str(pf))
    top = select_top_open_priorities(data, top_n=3)

    md = format_next_todos(top, date_str="2025-10-11")

    # Basic structure
    assert md.startswith("# Next Todos")
    assert "2025-10-11" in md
    # Contains titles and effort hours
    assert "Critical task" in md and "High task" in md
    assert "Effort:" in md


def test_write_next_todos_writes_file(tmp_path):
    content = textwrap.dedent(
        """
        # Next Todos
        - Item
        """
    ).strip()
    out = tmp_path / "NEXT_TODOS.md"
    write_next_todos(str(out), content)

    assert out.exists()
    assert out.read_text().strip().startswith("# Next Todos")

