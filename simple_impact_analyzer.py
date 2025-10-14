#!/usr/bin/env python3
"""
Simple Impact Analyzer - Quick impact analysis for naming violations.

This script performs a simplified but comprehensive impact analysis for 
high/critical priority naming violations.

Usage:
    python simple_impact_analyzer.py

Outputs:
    - impact_analysis_report.json: Detailed impact analysis
    - breaking_changes_forecast.md: Human-readable breaking changes forecast
    - test_update_requirements.md: Test update requirements
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any
import subprocess


def analyze_directory_impact(dir_path: str, dir_name: str, root_path: Path) -> Dict[str, Any]:
    """Analyze impact of renaming a directory."""
    impact = {
        "type": "directory",
        "current_name": dir_name,
        "path": dir_path,
        "dependencies": [],
        "breaking_change_risk": "high",
        "estimated_hours": 2.0
    }
    
    # Find import statements that reference this directory
    try:
        # Use grep to find imports
        module_path = dir_path.replace("/", ".")
        grep_patterns = [
            f"from {module_path}",
            f"import {module_path}"
        ]
        
        for pattern in grep_patterns:
            try:
                result = subprocess.run(
                    ["grep", "-r", "-n", pattern, str(root_path), "--include=*.py"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if ':' in line:
                            file_path, line_num, content = line.split(':', 2)
                            impact["dependencies"].append({
                                "file": file_path.replace(str(root_path) + "/", ""),
                                "line": int(line_num),
                                "content": content.strip()
                            })
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pass
    except Exception:
        pass
    
    # Adjust risk based on number of dependencies
    if len(impact["dependencies"]) > 10:
        impact["breaking_change_risk"] = "critical"
        impact["estimated_hours"] = 4.0
    elif len(impact["dependencies"]) > 5:
        impact["breaking_change_risk"] = "high"
        impact["estimated_hours"] = 3.0
    
    return impact


def analyze_function_impact(file_path: str, func_name: str, root_path: Path) -> Dict[str, Any]:
    """Analyze impact of renaming a function."""
    impact = {
        "type": "function",
        "current_name": func_name,
        "path": file_path,
        "dependencies": [],
        "breaking_change_risk": "medium",
        "estimated_hours": 1.0
    }
    
    # Find function calls
    try:
        # Use grep to find function calls
        pattern = f"{func_name}("
        result = subprocess.run(
            ["grep", "-r", "-n", pattern, str(root_path), "--include=*.py"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if ':' in line:
                    file_path_found, line_num, content = line.split(':', 2)
                    impact["dependencies"].append({
                        "file": file_path_found.replace(str(root_path) + "/", ""),
                        "line": int(line_num),
                        "content": content.strip()
                    })
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        pass
    
    # Adjust risk based on dependencies and location
    if "interface" in file_path.lower() or "main.py" in file_path:
        impact["breaking_change_risk"] = "critical"
        impact["estimated_hours"] = 2.0
    elif len(impact["dependencies"]) > 5:
        impact["breaking_change_risk"] = "high"
        impact["estimated_hours"] = 1.5
    
    return impact


def find_test_files(violation_name: str, root_path: Path) -> List[str]:
    """Find test files that might test the violated name."""
    test_files = []
    
    try:
        # Use grep to find test references
        result = subprocess.run(
            ["grep", "-r", "-l", violation_name, str(root_path / "tests"), "--include=*.py"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            files = result.stdout.strip().split('\n')
            test_files = [f.replace(str(root_path) + "/", "") for f in files if f]
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        pass
    
    return test_files


def find_documentation_references(violation_name: str, root_path: Path) -> List[Dict[str, Any]]:
    """Find documentation references to the violated name."""
    doc_refs = []
    
    try:
        # Search in markdown files
        result = subprocess.run(
            ["grep", "-r", "-n", violation_name, str(root_path), "--include=*.md"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if ':' in line:
                    file_path, line_num, content = line.split(':', 2)
                    doc_refs.append({
                        "file": file_path.replace(str(root_path) + "/", ""),
                        "line": int(line_num),
                        "content": content.strip()
                    })
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        pass
    
    return doc_refs


def analyze_violations_impact(phase_files: List[str]) -> List[Dict[str, Any]]:
    """Analyze impact for violations in phase files."""
    root_path = Path(".")
    all_analyses = []
    
    for phase_file in phase_files:
        if not Path(phase_file).exists():
            continue
        
        print(f"Analyzing {phase_file}...")
        
        with open(phase_file) as f:
            phase_data = json.load(f)
        
        violations_analyzed = 0
        
        for file_path, violations in phase_data["files_to_refactor"].items():
            for violation in violations:
                violations_analyzed += 1
                if violations_analyzed % 20 == 0:
                    print(f"  Progress: {violations_analyzed} violations analyzed")
                
                violation_type = violation["violation_type"]
                current_name = violation["current_name"]
                
                if violation_type.startswith("directory_"):
                    analysis = analyze_directory_impact(file_path, current_name, root_path)
                elif violation_type.startswith("function_"):
                    analysis = analyze_function_impact(file_path, current_name, root_path)
                else:
                    # Simple analysis for other types
                    analysis = {
                        "type": violation_type,
                        "current_name": current_name,
                        "path": file_path,
                        "dependencies": [],
                        "breaking_change_risk": "low",
                        "estimated_hours": 0.5
                    }
                
                # Add test and documentation analysis
                analysis["test_files"] = find_test_files(current_name, root_path)
                analysis["documentation_refs"] = find_documentation_references(current_name, root_path)
                analysis["violation"] = violation
                
                all_analyses.append(analysis)
    
    return all_analyses


def generate_reports(analyses: List[Dict[str, Any]]):
    """Generate impact analysis reports."""
    
    # Calculate summary statistics
    total_dependencies = sum(len(a["dependencies"]) for a in analyses)
    total_test_files = sum(len(a["test_files"]) for a in analyses)
    total_doc_refs = sum(len(a["documentation_refs"]) for a in analyses)
    total_hours = sum(a["estimated_hours"] for a in analyses)
    
    risk_counts = {}
    for analysis in analyses:
        risk = analysis["breaking_change_risk"]
        risk_counts[risk] = risk_counts.get(risk, 0) + 1
    
    # Generate JSON report
    json_report = {
        "summary": {
            "total_violations_analyzed": len(analyses),
            "total_dependencies": total_dependencies,
            "total_test_files_affected": total_test_files,
            "total_documentation_references": total_doc_refs,
            "estimated_total_hours": total_hours,
            "breaking_change_risk_distribution": risk_counts
        },
        "analyses": analyses
    }
    
    with open("impact_analysis_report.json", "w") as f:
        json.dump(json_report, f, indent=2)
    
    # Generate breaking changes forecast
    md_content = "# Breaking Changes Forecast\n\n"
    md_content += f"**Total Violations Analyzed:** {len(analyses)}\n"
    md_content += f"**Total Dependencies:** {total_dependencies}\n"
    md_content += f"**Estimated Total Time:** {total_hours:.1f} hours\n\n"
    
    md_content += "## Risk Distribution\n\n"
    for risk, count in sorted(risk_counts.items()):
        md_content += f"- **{risk.title()}:** {count} violations\n"
    md_content += "\n"
    
    # Show high-risk violations
    high_risk = [a for a in analyses if a["breaking_change_risk"] in ["critical", "high"]]
    if high_risk:
        md_content += "## High-Risk Changes\n\n"
        for analysis in high_risk[:10]:
            md_content += f"### {analysis['current_name']}\n"
            md_content += f"- **Path:** `{analysis['path']}`\n"
            md_content += f"- **Type:** {analysis['type']}\n"
            md_content += f"- **Risk:** {analysis['breaking_change_risk']}\n"
            md_content += f"- **Dependencies:** {len(analysis['dependencies'])}\n"
            md_content += f"- **Estimated Time:** {analysis['estimated_hours']}h\n\n"
    
    with open("breaking_changes_forecast.md", "w") as f:
        f.write(md_content)
    
    # Generate test update requirements
    test_md = "# Test Update Requirements\n\n"
    test_md += f"**Total Test Files Affected:** {total_test_files}\n\n"
    
    violations_with_tests = [a for a in analyses if a["test_files"]]
    if violations_with_tests:
        test_md += "## Violations with Test Coverage\n\n"
        for analysis in violations_with_tests:
            test_md += f"### {analysis['current_name']}\n"
            test_md += f"- **Path:** `{analysis['path']}`\n"
            test_md += f"- **Test Files:** {len(analysis['test_files'])}\n"
            for test_file in analysis["test_files"]:
                test_md += f"  - `{test_file}`\n"
            test_md += "\n"
    
    with open("test_update_requirements.md", "w") as f:
        f.write(test_md)
    
    print(f"\nReports generated:")
    print(f"  - impact_analysis_report.json")
    print(f"  - breaking_changes_forecast.md")
    print(f"  - test_update_requirements.md")


def main():
    """Main entry point."""
    phase_files = ["phase_2_goals.json", "phase_3_goals.json"]
    
    print("Starting impact analysis...")
    analyses = analyze_violations_impact(phase_files)
    
    print(f"Analyzed {len(analyses)} violations")
    generate_reports(analyses)
    
    print("Impact analysis complete!")


if __name__ == "__main__":
    main()
