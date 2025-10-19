import subprocess, sys, re

def test_build_rag_patterns_smoke_single_task_frontend():
    # Run a minimal non-dry-run batch to ensure end-to-end execution works
    proc = subprocess.run(
        [sys.executable, "scripts/build_rag_patterns.py", "--target", "1", "--parallel", "1", "--domain", "frontend"],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0
    out = proc.stdout
    # Should include execution summary and at least one SUCCESS entry for the single task
    assert "EXECUTION SUMMARY" in out
    # Look for the per-task success line
    assert re.search(r"Task\s+.*SUCCESS \(", out), out
    # And ensure total summary shows Success: at least 1
    assert re.search(r"Success:\s*[1-9]", out), out


def test_build_rag_patterns_smoke_single_task_research():
    proc = subprocess.run(
        [sys.executable, "scripts/build_rag_patterns.py", "--target", "1", "--parallel", "1", "--domain", "research"],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0
    out = proc.stdout
    assert "EXECUTION SUMMARY" in out
    assert re.search(r"Task\s+.*SUCCESS \(", out), out
    assert re.search(r"Success:\s*[1-9]", out), out


def test_build_rag_patterns_smoke_single_task_backend():
    proc = subprocess.run(
        [sys.executable, "scripts/build_rag_patterns.py", "--target", "1", "--parallel", "1", "--domain", "backend"],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0
    out = proc.stdout
    assert "EXECUTION SUMMARY" in out
    assert re.search(r"Task\s+.*SUCCESS \(", out), out
    assert re.search(r"Success:\s*[1-9]", out), out
