"""
Unit tests for template anomaly report script.

Validates that the script correctly:
- Scans all task templates
- Detects domain inconsistencies
- Generates valid JSON reports
- Provides actionable recommendations
"""

import json
import subprocess
import sys
from pathlib import Path
import pytest


def test_script_runs_successfully():
    """Verify script executes without errors."""
    result = subprocess.run(
        [sys.executable, "scripts/template_anomaly_report.py", "--output", "logs/test_anomaly_report.json"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "."}
    )
    
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert "Report written to:" in result.stderr


def test_json_report_structure():
    """Verify JSON report has expected structure."""
    # Run script
    subprocess.run(
        [sys.executable, "scripts/template_anomaly_report.py", "--output", "logs/test_anomaly_report.json"],
        capture_output=True,
        env={"PYTHONPATH": "."}
    )
    
    # Load report
    report_path = Path("logs/test_anomaly_report.json")
    assert report_path.exists(), "Report file not created"
    
    with open(report_path) as f:
        report = json.load(f)
    
    # Validate structure
    assert "summary" in report
    assert "domain_distribution" in report
    assert "anomalies" in report
    assert "recommendations" in report
    
    # Validate summary fields
    summary = report["summary"]
    assert "total_templates" in summary
    assert "anomaly_count" in summary
    assert "anomaly_rate_pct" in summary
    assert "error_count" in summary
    assert "warning_count" in summary
    assert "info_count" in summary
    
    # Validate types
    assert isinstance(summary["total_templates"], int)
    assert isinstance(summary["anomaly_count"], int)
    assert isinstance(report["domain_distribution"], dict)
    assert isinstance(report["anomalies"], list)
    assert isinstance(report["recommendations"], list)


def test_all_templates_scanned():
    """Verify all task YAML files are scanned."""
    # Count actual YAML files
    tasks_dir = Path("tasks")
    yaml_files = list(tasks_dir.glob("**/*.yaml"))
    expected_count = len(yaml_files)
    
    # Run script
    subprocess.run(
        [sys.executable, "scripts/template_anomaly_report.py", "--output", "logs/test_anomaly_report.json"],
        capture_output=True,
        env={"PYTHONPATH": "."}
    )
    
    # Load report
    with open("logs/test_anomaly_report.json") as f:
        report = json.load(f)
    
    # Verify count matches
    assert report["summary"]["total_templates"] == expected_count


def test_domain_distribution_sums_to_total():
    """Verify domain distribution counts sum to total templates."""
    # Run script
    subprocess.run(
        [sys.executable, "scripts/template_anomaly_report.py", "--output", "logs/test_anomaly_report.json"],
        capture_output=True,
        env={"PYTHONPATH": "."}
    )
    
    # Load report
    with open("logs/test_anomaly_report.json") as f:
        report = json.load(f)
    
    total = report["summary"]["total_templates"]
    domain_sum = sum(d["count"] for d in report["domain_distribution"].values())
    
    assert domain_sum == total, f"Domain counts ({domain_sum}) don't sum to total ({total})"


def test_no_anomalies_in_current_templates():
    """
    Verify current templates have no anomalies.
    
    This test ensures template quality is maintained. If it fails,
    review the anomalies in logs/test_anomaly_report.json.
    """
    # Run script
    result = subprocess.run(
        [sys.executable, "scripts/template_anomaly_report.py", "--output", "logs/test_anomaly_report.json"],
        capture_output=True,
        env={"PYTHONPATH": "."}
    )
    
    # Load report
    with open("logs/test_anomaly_report.json") as f:
        report = json.load(f)
    
    # Should have 0 errors (warnings and info are acceptable)
    assert report["summary"]["error_count"] == 0, (
        f"Found {report['summary']['error_count']} template errors. "
        f"Review logs/test_anomaly_report.json for details."
    )


def test_verbose_mode():
    """Verify verbose mode produces detailed output."""
    result = subprocess.run(
        [sys.executable, "scripts/template_anomaly_report.py", "--output", "logs/test_anomaly_report.json", "--verbose"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "."}
    )
    
    assert "Domain Distribution" in result.stdout
    assert "backend" in result.stdout  # Should show at least one domain


def test_custom_output_path():
    """Verify custom output path works."""
    custom_path = "logs/custom_anomaly_report.json"
    
    result = subprocess.run(
        [sys.executable, "scripts/template_anomaly_report.py", "--output", custom_path],
        capture_output=True,
        env={"PYTHONPATH": "."}
    )
    
    assert result.returncode == 0
    assert Path(custom_path).exists()
    
    # Cleanup
    Path(custom_path).unlink()


def test_anomaly_fields_structure():
    """Verify anomaly entries have expected fields if any exist."""
    # Run script
    subprocess.run(
        [sys.executable, "scripts/template_anomaly_report.py", "--output", "logs/test_anomaly_report.json"],
        capture_output=True,
        env={"PYTHONPATH": "."}
    )
    
    # Load report
    with open("logs/test_anomaly_report.json") as f:
        report = json.load(f)
    
    # If anomalies exist, validate structure
    for anomaly in report["anomalies"]:
        assert "file" in anomaly
        assert "inferred_domain" in anomaly
        assert "normalized_domain" in anomaly
        assert "severity" in anomaly
        assert "issues" in anomaly
        assert "tags" in anomaly
        
        assert anomaly["severity"] in ["info", "warning", "error"]
        assert isinstance(anomaly["issues"], list)
        assert isinstance(anomaly["tags"], list)
