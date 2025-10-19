import subprocess, sys

def test_cli_frontend_dry_run_selects_tasks(tmp_path):
    proc = subprocess.run(
        [sys.executable, "scripts/build_rag_patterns.py", "--target", "3", "--domain", "frontend", "--dry-run"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0
    out = proc.stdout
    # Selection message present and non-empty selection triggers execution
    assert "Selected" in out
    assert "Starting execution..." in out


def test_cli_research_dry_run_selects_tasks(tmp_path):
    proc = subprocess.run(
        [sys.executable, "scripts/build_rag_patterns.py", "--target", "3", "--domain", "research", "--dry-run"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0
    out = proc.stdout
    assert "Selected" in out
    assert "Starting execution..." in out
