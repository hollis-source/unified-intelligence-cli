"""Code Review Tasks - Multi-Model AI Code Review via Broadcast Composition.

Demonstrates broadcast composition for parallel AI-powered code analysis.
Tasks implement the multi_model_code_review.ct workflow.

Category Theory Foundation:
- Broadcast composition: (f × g) ∘ duplicate :: A → (B × D)
- Parallel execution: max(time(f), time(g)) vs time(f) + time(g)
- Type-safe composition validated at parse time

Clean Architecture: Use Cases layer (business logic for code review).
SOLID: SRP - each task has one responsibility.

Sprint: Testing broadcast composition with production use case
Reference: examples/workflows/multi_model_code_review.ct
"""

import asyncio
import subprocess
from typing import Any, Dict, List
from pathlib import Path
from datetime import datetime


# ============================================================================
# Step 1: Foundation Tasks (Data Acquisition + 2 Analyzers)
# ============================================================================

async def get_code_diff(input_data: Any = None) -> Dict[str, Any]:
    """
    Get git diff for staged and unstaged changes.

    Type: () -> CodeDiff

    Returns:
        CodeDiff structure with diff content and metadata
    """
    # Get unstaged diff
    unstaged_result = subprocess.run(
        ["git", "diff"],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )

    # Get staged diff
    staged_result = subprocess.run(
        ["git", "diff", "--staged"],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )

    # Combine diffs
    combined_diff = staged_result.stdout + "\n" + unstaged_result.stdout

    # Get changed files
    files_result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )

    changed_files = [f for f in files_result.stdout.strip().split('\n') if f]

    return {
        "task": "get_code_diff",
        "type": "CodeDiff",
        "status": "success",
        "diff_content": combined_diff,
        "changed_files": changed_files,
        "file_count": len(changed_files),
        "has_changes": bool(combined_diff.strip()),
        "timestamp": datetime.now().isoformat()
    }


async def analyze_solid(input_data: Any = None) -> Dict[str, Any]:
    """
    Analyze code for SOLID principles violations.

    Type: CodeDiff -> SOLIDReport

    Simulates AI-powered analysis with realistic latency (0.5s).
    In production, this would call multi-agent orchestrator with specialized model.

    Args:
        input_data: CodeDiff from get_code_diff

    Returns:
        SOLIDReport with violations and recommendations
    """
    # Simulate AI model analysis latency
    await asyncio.sleep(0.5)

    # Extract diff content
    diff_content = input_data.get("diff_content", "") if isinstance(input_data, dict) else str(input_data)

    # Mock SOLID analysis (production would use AI model)
    violations = []

    if "class" in diff_content and len(diff_content.split('\n')) > 50:
        violations.append({
            "principle": "SRP",
            "severity": "medium",
            "description": "Large class detected - may violate Single Responsibility Principle",
            "recommendation": "Consider splitting into smaller, focused classes"
        })

    if "import" in diff_content and diff_content.count("import") > 10:
        violations.append({
            "principle": "DIP",
            "severity": "low",
            "description": "Many imports detected - check for concrete dependencies",
            "recommendation": "Depend on abstractions (interfaces) not concretions"
        })

    return {
        "task": "analyze_solid",
        "type": "SOLIDReport",
        "status": "success",
        "violations": violations,
        "violation_count": len(violations),
        "principles_checked": ["SRP", "OCP", "LSP", "ISP", "DIP"],
        "execution_time": 0.5,
        "timestamp": datetime.now().isoformat()
    }


async def analyze_security(input_data: Any = None) -> Dict[str, Any]:
    """
    Analyze code for security vulnerabilities.

    Type: CodeDiff -> SecurityReport

    Simulates AI-powered security analysis with realistic latency (0.6s).
    In production, this would call specialized security analysis model.

    Args:
        input_data: CodeDiff from get_code_diff

    Returns:
        SecurityReport with vulnerabilities and severity ratings
    """
    # Simulate AI model analysis latency
    await asyncio.sleep(0.6)

    # Extract diff content
    diff_content = input_data.get("diff_content", "") if isinstance(input_data, dict) else str(input_data)

    # Mock security analysis (production would use AI model)
    vulnerabilities = []

    if "password" in diff_content.lower() or "api_key" in diff_content.lower():
        vulnerabilities.append({
            "type": "credential-exposure",
            "severity": "high",
            "description": "Potential credential exposure detected",
            "recommendation": "Use environment variables or secrets manager",
            "cwe": "CWE-798"
        })

    if "eval(" in diff_content or "exec(" in diff_content:
        vulnerabilities.append({
            "type": "code-injection",
            "severity": "critical",
            "description": "Dangerous eval/exec usage detected",
            "recommendation": "Avoid dynamic code execution, use safer alternatives",
            "cwe": "CWE-95"
        })

    if "sql" in diff_content.lower() and "%" in diff_content:
        vulnerabilities.append({
            "type": "sql-injection",
            "severity": "high",
            "description": "Potential SQL injection via string formatting",
            "recommendation": "Use parameterized queries",
            "cwe": "CWE-89"
        })

    return {
        "task": "analyze_security",
        "type": "SecurityReport",
        "status": "success",
        "vulnerabilities": vulnerabilities,
        "vulnerability_count": len(vulnerabilities),
        "severity_breakdown": {
            "critical": sum(1 for v in vulnerabilities if v["severity"] == "critical"),
            "high": sum(1 for v in vulnerabilities if v["severity"] == "high"),
            "medium": sum(1 for v in vulnerabilities if v["severity"] == "medium"),
            "low": sum(1 for v in vulnerabilities if v["severity"] == "low")
        },
        "execution_time": 0.6,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# Step 2: Additional Analyzers (Performance + Coverage)
# ============================================================================

async def analyze_performance(input_data: Any = None) -> Dict[str, Any]:
    """
    Analyze code for performance bottlenecks and optimization opportunities.

    Type: CodeDiff -> PerformanceReport

    Simulates AI-powered performance analysis with realistic latency (0.55s).
    In production, this would call performance analysis model.

    Args:
        input_data: CodeDiff from get_code_diff

    Returns:
        PerformanceReport with bottlenecks and optimization suggestions
    """
    # Simulate AI model analysis latency
    await asyncio.sleep(0.55)

    # Extract diff content
    diff_content = input_data.get("diff_content", "") if isinstance(input_data, dict) else str(input_data)

    # Mock performance analysis (production would use AI model)
    issues = []

    if "for" in diff_content and "for" in diff_content[diff_content.find("for")+3:]:
        issues.append({
            "type": "nested-loops",
            "severity": "medium",
            "description": "Nested loops detected - potential O(n²) complexity",
            "recommendation": "Consider using hash maps or optimized algorithms",
            "impact": "high"
        })

    if ".append(" in diff_content and "for" in diff_content:
        issues.append({
            "type": "inefficient-append",
            "severity": "low",
            "description": "List append in loop - consider list comprehension",
            "recommendation": "Use list comprehension for better performance",
            "impact": "medium"
        })

    if "SELECT *" in diff_content.upper():
        issues.append({
            "type": "inefficient-query",
            "severity": "medium",
            "description": "SELECT * detected - retrieve only needed columns",
            "recommendation": "Specify exact columns needed",
            "impact": "high"
        })

    return {
        "task": "analyze_performance",
        "type": "PerformanceReport",
        "status": "success",
        "issues": issues,
        "issue_count": len(issues),
        "categories": {
            "algorithmic": sum(1 for i in issues if i["type"] in ["nested-loops", "inefficient-algorithm"]),
            "database": sum(1 for i in issues if i["type"] in ["inefficient-query", "n+1-query"]),
            "memory": sum(1 for i in issues if i["type"] in ["memory-leak", "large-allocation"])
        },
        "execution_time": 0.55,
        "timestamp": datetime.now().isoformat()
    }


async def analyze_coverage(input_data: Any = None) -> Dict[str, Any]:
    """
    Analyze test coverage gaps for changed code.

    Type: CodeDiff -> CoverageReport

    Simulates AI-powered test coverage analysis with realistic latency (0.45s).
    In production, this would call test analysis model.

    Args:
        input_data: CodeDiff from get_code_diff

    Returns:
        CoverageReport with coverage gaps and test recommendations
    """
    # Simulate AI model analysis latency
    await asyncio.sleep(0.45)

    # Extract diff content and changed files
    if isinstance(input_data, dict):
        diff_content = input_data.get("diff_content", "")
        changed_files = input_data.get("changed_files", [])
    else:
        diff_content = str(input_data)
        changed_files = []

    # Mock coverage analysis (production would use AI model)
    gaps = []

    # Check if new functions added without tests
    if "def " in diff_content and "+" in diff_content:
        gaps.append({
            "type": "untested-function",
            "severity": "high",
            "description": "New functions added without corresponding tests",
            "recommendation": "Add unit tests for new functions",
            "files_affected": [f for f in changed_files if not f.startswith("test_")]
        })

    # Check if logic changed in non-test files
    if changed_files and not any("test" in f for f in changed_files):
        gaps.append({
            "type": "missing-integration-tests",
            "severity": "medium",
            "description": "Logic changes without integration test updates",
            "recommendation": "Add integration tests for changed workflows",
            "files_affected": changed_files
        })

    # Check for edge cases
    if "if " in diff_content or "else" in diff_content:
        gaps.append({
            "type": "uncovered-branches",
            "severity": "medium",
            "description": "Conditional logic added - ensure all branches tested",
            "recommendation": "Add tests for both if/else branches",
            "files_affected": changed_files
        })

    estimated_coverage = max(0, 85 - (len(gaps) * 10))

    return {
        "task": "analyze_coverage",
        "type": "CoverageReport",
        "status": "success",
        "gaps": gaps,
        "gap_count": len(gaps),
        "estimated_coverage_pct": estimated_coverage,
        "recommendations": [g["recommendation"] for g in gaps],
        "files_needing_tests": list(set(f for gap in gaps for f in gap.get("files_affected", []))),
        "execution_time": 0.45,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# Step 3: Merge and Format Tasks (Report Generation)
# ============================================================================

async def merge_compliance(input_data: Any = None) -> Dict[str, Any]:
    """
    Merge SOLID and Security reports into compliance report.

    Type: (SOLIDReport × SecurityReport) -> ComplianceReport

    Args:
        input_data: Tuple of (SOLIDReport, SecurityReport) from parallel analyzers

    Returns:
        ComplianceReport combining both analyses
    """
    # Unpack tuple from product morphism
    if isinstance(input_data, tuple) and len(input_data) == 2:
        solid_report, security_report = input_data
    else:
        raise ValueError(f"Expected tuple of (SOLIDReport, SecurityReport), got {type(input_data)}")

    # Extract data from reports
    solid_violations = solid_report.get("violations", []) if isinstance(solid_report, dict) else []
    security_vulns = security_report.get("vulnerabilities", []) if isinstance(security_report, dict) else []

    # Calculate compliance score (0-100)
    total_issues = len(solid_violations) + len(security_vulns)
    compliance_score = max(0, 100 - (total_issues * 10))

    return {
        "task": "merge_compliance",
        "type": "ComplianceReport",
        "status": "success",
        "compliance_score": compliance_score,
        "solid_violations": solid_violations,
        "security_vulnerabilities": security_vulns,
        "total_issues": total_issues,
        "pass_threshold": compliance_score >= 70,
        "timestamp": datetime.now().isoformat()
    }


async def merge_quality(input_data: Any = None) -> Dict[str, Any]:
    """
    Merge Performance and Coverage reports into quality report.

    Type: (PerformanceReport × CoverageReport) -> QualityReport

    Args:
        input_data: Tuple of (PerformanceReport, CoverageReport) from parallel analyzers

    Returns:
        QualityReport combining both analyses
    """
    # Unpack tuple from product morphism
    if isinstance(input_data, tuple) and len(input_data) == 2:
        perf_report, coverage_report = input_data
    else:
        raise ValueError(f"Expected tuple of (PerformanceReport, CoverageReport), got {type(input_data)}")

    # Extract data from reports
    perf_issues = perf_report.get("issues", []) if isinstance(perf_report, dict) else []
    coverage_gaps = coverage_report.get("gaps", []) if isinstance(coverage_report, dict) else []
    coverage_pct = coverage_report.get("estimated_coverage_pct", 0) if isinstance(coverage_report, dict) else 0

    # Calculate quality score (0-100)
    perf_score = max(0, 100 - (len(perf_issues) * 15))
    quality_score = int((perf_score + coverage_pct) / 2)

    return {
        "task": "merge_quality",
        "type": "QualityReport",
        "status": "success",
        "quality_score": quality_score,
        "performance_issues": perf_issues,
        "coverage_gaps": coverage_gaps,
        "coverage_percentage": coverage_pct,
        "total_issues": len(perf_issues) + len(coverage_gaps),
        "pass_threshold": quality_score >= 70,
        "timestamp": datetime.now().isoformat()
    }


async def format_compliance(input_data: Any = None) -> Dict[str, Any]:
    """
    Format compliance report as markdown.

    Type: ComplianceReport -> MarkdownReport

    Args:
        input_data: ComplianceReport from merge_compliance

    Returns:
        MarkdownReport with formatted compliance analysis
    """
    if not isinstance(input_data, dict):
        raise ValueError(f"Expected ComplianceReport dict, got {type(input_data)}")

    score = input_data.get("compliance_score", 0)
    solid_violations = input_data.get("solid_violations", [])
    security_vulns = input_data.get("security_vulnerabilities", [])
    passed = input_data.get("pass_threshold", False)

    # Build markdown report
    lines = [
        "# Code Compliance Report",
        "",
        f"**Compliance Score:** {score}/100 {'✓ PASS' if passed else '✗ FAIL'}",
        "",
        "## SOLID Principles Analysis",
        ""
    ]

    if solid_violations:
        for v in solid_violations:
            lines.append(f"- **{v['principle']}** ({v['severity']}): {v['description']}")
            lines.append(f"  - *Recommendation:* {v['recommendation']}")
    else:
        lines.append("✓ No SOLID violations detected")

    lines.extend([
        "",
        "## Security Analysis",
        ""
    ])

    if security_vulns:
        for v in security_vulns:
            lines.append(f"- **{v['type']}** ({v['severity']}): {v['description']}")
            lines.append(f"  - *CWE:* {v.get('cwe', 'N/A')}")
            lines.append(f"  - *Recommendation:* {v['recommendation']}")
    else:
        lines.append("✓ No security vulnerabilities detected")

    markdown_content = "\n".join(lines)

    return {
        "task": "format_compliance",
        "type": "MarkdownReport",
        "status": "success",
        "content": markdown_content,
        "report_type": "compliance",
        "timestamp": datetime.now().isoformat()
    }


async def format_quality(input_data: Any = None) -> Dict[str, Any]:
    """
    Format quality report as markdown.

    Type: QualityReport -> MarkdownReport

    Args:
        input_data: QualityReport from merge_quality

    Returns:
        MarkdownReport with formatted quality analysis
    """
    if not isinstance(input_data, dict):
        raise ValueError(f"Expected QualityReport dict, got {type(input_data)}")

    score = input_data.get("quality_score", 0)
    perf_issues = input_data.get("performance_issues", [])
    coverage_gaps = input_data.get("coverage_gaps", [])
    coverage_pct = input_data.get("coverage_percentage", 0)
    passed = input_data.get("pass_threshold", False)

    # Build markdown report
    lines = [
        "# Code Quality Report",
        "",
        f"**Quality Score:** {score}/100 {'✓ PASS' if passed else '✗ FAIL'}",
        f"**Test Coverage:** {coverage_pct}%",
        "",
        "## Performance Analysis",
        ""
    ]

    if perf_issues:
        for issue in perf_issues:
            lines.append(f"- **{issue['type']}** ({issue['severity']}): {issue['description']}")
            lines.append(f"  - *Impact:* {issue.get('impact', 'unknown')}")
            lines.append(f"  - *Recommendation:* {issue['recommendation']}")
    else:
        lines.append("✓ No performance issues detected")

    lines.extend([
        "",
        "## Test Coverage Analysis",
        ""
    ])

    if coverage_gaps:
        for gap in coverage_gaps:
            lines.append(f"- **{gap['type']}** ({gap['severity']}): {gap['description']}")
            lines.append(f"  - *Recommendation:* {gap['recommendation']}")
    else:
        lines.append("✓ No coverage gaps detected")

    markdown_content = "\n".join(lines)

    return {
        "task": "format_quality",
        "type": "MarkdownReport",
        "status": "success",
        "content": markdown_content,
        "report_type": "quality",
        "timestamp": datetime.now().isoformat()
    }


async def display_report(input_data: Any = None) -> Dict[str, Any]:
    """
    Display markdown report to console.

    Type: MarkdownReport -> ()

    Args:
        input_data: MarkdownReport from format_compliance or format_quality

    Returns:
        Unit type (empty dict indicating completion)
    """
    if isinstance(input_data, dict):
        content = input_data.get("content", "")
        report_type = input_data.get("report_type", "unknown")
    else:
        content = str(input_data)
        report_type = "unknown"

    # Print to console
    print("\n" + "="*80)
    print(content)
    print("="*80 + "\n")

    return {
        "task": "display_report",
        "type": "Unit",
        "status": "success",
        "report_type": report_type,
        "displayed": True,
        "timestamp": datetime.now().isoformat()
    }
