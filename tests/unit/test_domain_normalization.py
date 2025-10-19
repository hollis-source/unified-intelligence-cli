from pathlib import Path
import pytest

# Import TaskTemplate and normalize_domain
from scripts.build_rag_patterns import TaskTemplate
from scripts.ab_routing_eval import normalize_domain


def test_normalize_domain_mappings():
    assert normalize_domain("test") == "testing"
    assert normalize_domain("tests") == "testing"
    assert normalize_domain("quality") == "qa"
    assert normalize_domain("quality-assurance") == "qa"
    assert normalize_domain("Qa") == "qa"
    assert normalize_domain("") == ""


def test_tasktemplate_path_inference_testing_from_test_dir():
    t = TaskTemplate(Path("tasks/test/sample.yaml"), {"metadata": {"tags": []}, "prompt": ""})
    assert t.domain == "testing"


def test_tasktemplate_path_inference_frontend_devops():
    """Frontend and devops path-based inference"""
    t_fe = TaskTemplate(Path("tasks/frontend/fe.yaml"), {"metadata": {"tags": []}, "prompt": ""})
    t_do = TaskTemplate(Path("tasks/devops/do.yaml"), {"metadata": {"tags": []}, "prompt": ""})
    assert t_fe.domain == "frontend"
    assert t_do.domain == "devops"


def test_tasktemplate_tag_inference_overrides_unknown():
    t = TaskTemplate(Path("tasks/misc/unknown.yaml"), {"metadata": {"tags": ["react", "frontend"]}, "prompt": ""})
    assert t.domain == "frontend"


# Additional comprehensive tests for normalize_domain edge cases
def test_normalize_domain_case_insensitivity():
    """Test case insensitive normalization"""
    assert normalize_domain("TEST") == "testing"
    assert normalize_domain("Test") == "testing"
    assert normalize_domain("TESTS") == "testing"
    assert normalize_domain("QA") == "qa"
    assert normalize_domain("Quality") == "qa"
    assert normalize_domain("QUALITY-ASSURANCE") == "qa"


def test_normalize_domain_whitespace_handling():
    """Test whitespace trimming"""
    assert normalize_domain("  test  ") == "testing"
    assert normalize_domain("  qa  ") == "qa"
    assert normalize_domain("\tquality\n") == "qa"


def test_normalize_domain_passthrough_canonical():
    """Test canonical domains pass through unchanged"""
    canonical = ["testing", "qa", "frontend", "backend", "devops", "research", "architecture"]
    for domain in canonical:
        assert normalize_domain(domain) == domain


def test_normalize_domain_passthrough_unknown():
    """Test unknown domains pass through as lowercase"""
    assert normalize_domain("unknown") == "unknown"
    assert normalize_domain("Custom") == "custom"
    assert normalize_domain("SPECIAL") == "special"


# Additional TaskTemplate inference tests
def test_tasktemplate_tests_directory_to_testing():
    """tasks/tests/ → testing"""
    t = TaskTemplate(Path("tasks/tests/test-01.yaml"), {"metadata": {"tags": []}, "prompt": ""})
    assert t.domain == "testing"


def test_tasktemplate_testing_directory():
    """tasks/testing/ → testing"""
    t = TaskTemplate(Path("tasks/testing/test-01.yaml"), {"metadata": {"tags": []}, "prompt": ""})
    assert t.domain == "testing"


def test_tasktemplate_qa_directory():
    """tasks/qa/ → qa"""
    t = TaskTemplate(Path("tasks/qa/qa-01.yaml"), {"metadata": {"tags": []}, "prompt": ""})
    assert t.domain == "qa"


def test_tasktemplate_research_directory():
    """tasks/research/ → research"""
    t = TaskTemplate(Path("tasks/research/research-01.yaml"), {"metadata": {"tags": []}, "prompt": ""})
    assert t.domain == "research"


def test_tasktemplate_architect_directory():
    """tasks/architect/ → architecture"""
    t = TaskTemplate(Path("tasks/architect/arch-01.yaml"), {"metadata": {"tags": []}, "prompt": ""})
    assert t.domain == "architecture"


def test_tasktemplate_database_to_backend():
    """tasks/database/ → backend"""
    t = TaskTemplate(Path("tasks/database/db-01.yaml"), {"metadata": {"tags": []}, "prompt": ""})
    assert t.domain == "backend"


def test_tasktemplate_python_to_backend():
    """tasks/python/ → backend"""
    t = TaskTemplate(Path("tasks/python/py-01.yaml"), {"metadata": {"tags": []}, "prompt": ""})
    assert t.domain == "backend"


# Tag-based inference tests
def test_tasktemplate_react_tag_to_frontend():
    """Tag 'react' → frontend"""
    t = TaskTemplate(Path("tasks/misc/task.yaml"), {"metadata": {"tags": ["react"]}, "prompt": ""})
    assert t.domain == "frontend"


def test_tasktemplate_ui_tag_to_frontend():
    """Tag 'ui' → frontend"""
    t = TaskTemplate(Path("tasks/misc/task.yaml"), {"metadata": {"tags": ["ui"]}, "prompt": ""})
    assert t.domain == "frontend"


def test_tasktemplate_api_tag_to_backend():
    """Tag 'api' → backend"""
    t = TaskTemplate(Path("tasks/misc/task.yaml"), {"metadata": {"tags": ["api"]}, "prompt": ""})
    assert t.domain == "backend"


def test_tasktemplate_database_tag_to_backend():
    """Tag 'database' → backend"""
    t = TaskTemplate(Path("tasks/misc/task.yaml"), {"metadata": {"tags": ["database"]}, "prompt": ""})
    assert t.domain == "backend"


def test_tasktemplate_acceptance_tag_to_qa():
    """Tag 'acceptance' → qa"""
    t = TaskTemplate(Path("tasks/misc/task.yaml"), {"metadata": {"tags": ["acceptance"]}, "prompt": ""})
    assert t.domain == "qa"


def test_tasktemplate_testing_tag():
    """Tag 'testing' → testing"""
    t = TaskTemplate(Path("tasks/misc/task.yaml"), {"metadata": {"tags": ["testing"]}, "prompt": ""})
    assert t.domain == "testing"


def test_tasktemplate_test_tag():
    """Tag 'test' → testing"""
    t = TaskTemplate(Path("tasks/misc/task.yaml"), {"metadata": {"tags": ["test"]}, "prompt": ""})
    assert t.domain == "testing"


def test_tasktemplate_ci_tag_to_devops():
    """Tag 'ci' → devops"""
    t = TaskTemplate(Path("tasks/misc/task.yaml"), {"metadata": {"tags": ["ci"]}, "prompt": ""})
    assert t.domain == "devops"


def test_tasktemplate_deployment_tag_to_devops():
    """Tag 'deployment' → devops"""
    t = TaskTemplate(Path("tasks/misc/task.yaml"), {"metadata": {"tags": ["deployment"]}, "prompt": ""})
    assert t.domain == "devops"


def test_tasktemplate_adr_tag_to_research():
    """Tag 'adr' → research"""
    t = TaskTemplate(Path("tasks/misc/task.yaml"), {"metadata": {"tags": ["adr"]}, "prompt": ""})
    assert t.domain == "research"


def test_tasktemplate_benchmarking_tag_to_research():
    """Tag 'benchmarking' → research"""
    t = TaskTemplate(Path("tasks/misc/task.yaml"), {"metadata": {"tags": ["benchmarking"]}, "prompt": ""})
    assert t.domain == "research"


def test_tasktemplate_architecture_tag():
    """Tag 'architecture' → architecture"""
    t = TaskTemplate(Path("tasks/misc/task.yaml"), {"metadata": {"tags": ["architecture"]}, "prompt": ""})
    assert t.domain == "architecture"


# Path precedence tests
def test_tasktemplate_path_takes_precedence_over_tags():
    """Path-based inference takes precedence over tags"""
    t = TaskTemplate(Path("tasks/frontend/task.yaml"), {"metadata": {"tags": ["backend"]}, "prompt": ""})
    assert t.domain == "frontend"  # Path wins


def test_tasktemplate_case_insensitive_path():
    """Path matching is case insensitive"""
    t1 = TaskTemplate(Path("tasks/TEST/test.yaml"), {"metadata": {"tags": []}, "prompt": ""})
    assert t1.domain == "testing"

    t2 = TaskTemplate(Path("tasks/QA/qa.yaml"), {"metadata": {"tags": []}, "prompt": ""})
    assert t2.domain == "qa"


def test_tasktemplate_case_insensitive_tags():
    """Tag matching is case insensitive"""
    t1 = TaskTemplate(Path("tasks/misc/task.yaml"), {"metadata": {"tags": ["FRONTEND"]}, "prompt": ""})
    assert t1.domain == "frontend"

    t2 = TaskTemplate(Path("tasks/misc/task.yaml"), {"metadata": {"tags": ["QA"]}, "prompt": ""})
    assert t2.domain == "qa"


# Unknown domain test
def test_tasktemplate_unknown_domain():
    """No path/tag match → unknown"""
    t = TaskTemplate(Path("tasks/misc/random.yaml"), {"metadata": {"tags": []}, "prompt": ""})
    assert t.domain == "unknown"


# Integration tests combining both functions
def test_integration_test_directory_normalizes():
    """tasks/test/ → testing (infer) → testing (normalize)"""
    t = TaskTemplate(Path("tasks/test/test.yaml"), {"metadata": {"tags": []}, "prompt": ""})
    inferred = t.domain
    normalized = normalize_domain(inferred)
    assert inferred == "testing"
    assert normalized == "testing"


def test_integration_all_inferred_domains_normalize_to_self():
    """All domains from _infer_domain should normalize to themselves"""
    paths = {
        "tasks/testing/t.yaml": "testing",
        "tasks/qa/q.yaml": "qa",
        "tasks/frontend/f.yaml": "frontend",
        "tasks/database/b.yaml": "backend",  # database path → backend
        "tasks/devops/d.yaml": "devops",
        "tasks/research/r.yaml": "research",
        "tasks/architect/a.yaml": "architecture",
    }
    for path_str, expected in paths.items():
        t = TaskTemplate(Path(path_str), {"metadata": {"tags": []}, "prompt": ""})
        assert t.domain == expected
        assert normalize_domain(t.domain) == expected


# Edge cases
def test_normalize_domain_none_returns_empty():
    """None input returns empty string (handled by 'if not d')"""
    assert normalize_domain(None) == ""


def test_tasktemplate_empty_metadata():
    """Empty metadata → unknown"""
    t = TaskTemplate(Path("tasks/misc/task.yaml"), {"prompt": "test"})
    assert t.domain == "unknown"

