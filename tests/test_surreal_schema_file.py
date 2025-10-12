import re
from pathlib import Path

SCHEMA_PATH = Path('scripts/init-surreal.surql')


def test_surreal_schema_indexes_present_and_correct():
    text = SCHEMA_PATH.read_text(encoding='utf-8')

    # Non-unique index on project_id (allows versioning)
    assert re.search(r"^DEFINE INDEX\s+project_id_idx\s+ON TABLE\s+projects\s+COLUMNS\s+project_id;.*$", text, flags=re.MULTILINE), (
        "Expected non-unique index on project_id to allow multiple versions per project"
    )

    # Unique composite index on (project_id, version)
    assert re.search(r"^DEFINE INDEX\s+project_version_idx\s+ON TABLE\s+projects\s+COLUMNS\s+project_id,\s*version\s+UNIQUE;.*$", text, flags=re.MULTILINE), (
        "Expected UNIQUE composite index on (project_id, version)"
    )

