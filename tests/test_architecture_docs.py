import re
from pathlib import Path


def test_architecture_overview_doc_exists():
    doc_path = Path("docs/ARCHITECTURE_OVERVIEW.md")
    assert doc_path.exists(), "docs/ARCHITECTURE_OVERVIEW.md should exist"


def test_architecture_overview_has_key_sections():
    text = Path("docs/ARCHITECTURE_OVERVIEW.md").read_text(encoding="utf-8")
    # Required key concepts aligned with Clean Architecture and this repo's structure
    required_keywords = [
        "Entities",
        "Use Cases",
        "Adapters",
        "Interfaces",
        "Dependency Inversion",
        "Routing",
        "DSL",
    ]
    missing = [kw for kw in required_keywords if kw.lower() not in text.lower()]
    assert not missing, f"Missing sections/keywords in ARCHITECTURE_OVERVIEW.md: {missing}"


def test_architecture_overview_references_repo_structure():
    text = Path("docs/ARCHITECTURE_OVERVIEW.md").read_text(encoding="utf-8")
    # Ensure doc maps to the actual directories present in src/
    required_paths = [
        "src/entities",
        "src/use_cases",
        "src/adapters",
        "src/dsl",
        "src/routing",
    ]
    missing = [p for p in required_paths if p not in text]
    assert not missing, f"Doc should reference key repo paths: {missing}"

