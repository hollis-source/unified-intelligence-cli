import textwrap
from pathlib import Path

import yaml

from src.utils.next_todos import (
    load_priorities,
    select_top_open_priorities,
    format_next_todos,
    write_next_todos,
)


def test_generate_next_todos_end_to_end(tmp_path):
    # Arrange: sample priorities
    data = {
        "priorities": [
            {"id": "a", "title": "Critical task", "status": "open", "priority": "critical", "effort_hours": 5},
            {"id": "b", "title": "High task", "status": "open", "priority": "high", "effort_hours": 3},
            {"id": "c", "title": "Closed task", "status": "completed", "priority": "high", "effort_hours": 2},
        ]
    }
    pfile = tmp_path / "priorities.yaml"
    pfile.write_text(yaml.safe_dump(data))

    # Act: compose via utilities
    loaded = load_priorities(str(pfile))
    top = select_top_open_priorities(loaded, top_n=1)
    md = format_next_todos(top, date_str="2025-10-11")
    outfile = tmp_path / "NEXT_TODOS.md"
    write_next_todos(str(outfile), md)

    # Assert
    content = outfile.read_text()
    assert content.startswith("# Next Todos")
    assert "2025-10-11" in content
    assert "Critical task" in content




def test_generate_next_todos_helper(tmp_path):
    from src.utils.next_todos import generate_next_todos

    data = {
        "priorities": [
            {"id": "x", "title": "High task", "status": "open", "priority": "high", "effort_hours": 2},
            {"id": "y", "title": "Low task", "status": "open", "priority": "low", "effort_hours": 1},
        ]
    }
    pfile = tmp_path / "priorities.yaml"
    pfile.write_text(yaml.safe_dump(data))
    outfile = tmp_path / "NEXT_TODOS.md"

    generate_next_todos(str(pfile), str(outfile), top_n=1, date_str="2025-10-11")

    content = outfile.read_text()
    assert content.startswith("# Next Todos")
    assert "2025-10-11" in content
    assert "High task" in content
