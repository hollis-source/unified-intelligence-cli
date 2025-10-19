import subprocess, sys

def test_cli_unknown_domain_exits_gracefully(tmp_path):
    # Run with a domain that likely has no tasks
    proc = subprocess.run(
        [sys.executable, "scripts/build_rag_patterns.py", "--target", "3", "--domain", "unknown-domain-zzz", "--dry-run"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    # Should not crash; exit code 0
    assert proc.returncode == 0
    out = proc.stdout
    # Should print friendly message and "Nothing to execute. Exiting."
    assert "No tasks available for the selected domain" in out or "Loaded 0 tasks" in out
    assert "Nothing to execute. Exiting." in out

