from pathlib import Path
import yaml


def load_yaml(p: Path):
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_template(obj: dict):
    assert isinstance(obj, dict)
    assert "id" in obj and isinstance(obj["id"], str) and obj["id"].strip()
    assert "agent" in obj and isinstance(obj["agent"], str) and obj["agent"].strip()
    assert "prompt" in obj and isinstance(obj["prompt"], str) and obj["prompt"].strip()
    assert "checks" in obj and isinstance(obj["checks"], list) and len(obj["checks"]) > 0
    assert "metadata" in obj and isinstance(obj["metadata"], dict)
    tags = obj["metadata"].get("tags", [])
    assert isinstance(tags, list) and len(tags) > 0
    # Optional fields validation when present
    difficulty = obj["metadata"].get("difficulty")
    if difficulty is not None:
        assert difficulty in {"easy", "medium", "hard"}
    est = obj["metadata"].get("est_runtime_s")
    if est is not None:
        assert isinstance(est, int) and est > 0


def test_frontend_templates_schema():
    files = sorted(Path("tasks/frontend").glob("*.yaml"))
    assert files, "No frontend task templates found"
    for p in files:
        obj = load_yaml(p)
        validate_template(obj)


def test_research_templates_schema():
    files = sorted(Path("tasks/research").glob("*.yaml"))
    assert files, "No research task templates found"
    for p in files:
        obj = load_yaml(p)
        validate_template(obj)

