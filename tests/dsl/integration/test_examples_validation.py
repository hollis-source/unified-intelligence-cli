import pytest
from pathlib import Path

from src.dsl.use_cases.workflow_validator import WorkflowValidator, ValidationReport


EXAMPLES_DIR = Path("examples/workflows")
EXAMPLE_WORKFLOWS = sorted(EXAMPLES_DIR.glob("*.ct"))


@pytest.mark.parametrize("workflow_path", EXAMPLE_WORKFLOWS, ids=[p.name for p in EXAMPLE_WORKFLOWS])
def test_examples_validate_without_crash(workflow_path: Path):
    """All example .ct workflows should be processed by the validator without crashing.

    This test ensures the validator returns a well-formed ValidationReport for each
    example. It does not require success; it only asserts consistency invariants.
    """
    validator = WorkflowValidator()
    report: ValidationReport = validator.validate_file(workflow_path)

    # Invariants: shapes
    assert isinstance(report.success, bool)
    assert isinstance(report.errors, list)
    assert isinstance(report.warnings, list)

    # Consistency: success implies no errors; failure implies at least one error
    if report.success:
        assert len(report.errors) == 0
    else:
        assert len(report.errors) >= 1

