from pathlib import Path


def test_best_practices_doc_exists():
    doc = Path("docs/BEST_PRACTICES.md")
    assert doc.exists(), "docs/BEST_PRACTICES.md should exist"


def test_best_practices_has_key_sections():
    text = Path("docs/BEST_PRACTICES.md").read_text(encoding="utf-8")
    required = [
        "Clean Architecture",
        "SOLID",
        "TDD",
        "Functions < 20 lines",
        "Explicit error handling",
        "DRY",
        "Dependency Inversion",
        "Interfaces",
        "Adapters",
    ]
    missing = [kw for kw in required if kw.lower() not in text.lower()]
    assert not missing, f"Missing required best-practice topics: {missing}"

