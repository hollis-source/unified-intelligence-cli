"""
Template Anomaly Report Script

Scans tasks/**/*.yaml for domain/tag inconsistencies and exports JSON report.

Usage:
    python scripts/template_anomaly_report.py [--output report.json] [--verbose]

Output:
    JSON report with:
    - summary: Total templates, anomaly count, anomaly rate
    - anomalies: List of templates with issues
    - domain_distribution: Breakdown by domain
    - recommendations: Actionable fixes
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import yaml
import argparse

# Import TaskTemplate and normalize_domain
try:
    from scripts.build_rag_patterns import TaskTemplate
    from scripts.ab_routing_eval import normalize_domain
except ImportError:
    print("Error: Unable to import TaskTemplate or normalize_domain", file=sys.stderr)
    print("Ensure you run this script from the project root directory", file=sys.stderr)
    sys.exit(1)


# Canonical allowed domains (from test_template_domain_consistency.py)
ALLOWED_DOMAINS = {
    "testing", "qa", "frontend", "backend", "devops", "research",
    "documentation", "security", "performance", "category-theory",
    "dsl", "architecture", "general", "unknown",
}


def scan_all_templates() -> List[Tuple[Path, TaskTemplate, Dict[str, Any]]]:
    """
    Scan all task YAML files and create TaskTemplate objects.
    
    Returns:
        List of (file_path, template, raw_data) tuples
    """
    tasks_dir = Path("tasks")
    if not tasks_dir.exists():
        print(f"Error: tasks/ directory not found at {tasks_dir.absolute()}", file=sys.stderr)
        sys.exit(1)
    
    templates = []
    for yaml_file in sorted(tasks_dir.glob("**/*.yaml")):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if data:
                template = TaskTemplate(yaml_file, data)
                templates.append((yaml_file, template, data))
        except Exception as e:
            print(f"Warning: Failed to parse {yaml_file}: {e}", file=sys.stderr)
    
    return templates


def detect_anomalies(templates: List[Tuple[Path, TaskTemplate, Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Detect domain/tag inconsistencies in templates.
    
    Returns:
        Report dictionary with summary, anomalies, and recommendations
    """
    anomalies = []
    domain_distribution = {}
    total_templates = len(templates)
    
    for file_path, template, raw_data in templates:
        inferred_domain = template.domain
        normalized_domain = normalize_domain(inferred_domain)
        
        # Track domain distribution
        domain_distribution[normalized_domain] = domain_distribution.get(normalized_domain, 0) + 1
        
        issues = []
        severity = "info"
        
        # Check 1: Domain not in allowed list
        if normalized_domain not in ALLOWED_DOMAINS:
            issues.append(f"Invalid domain: '{normalized_domain}' not in allowed domains")
            severity = "error"
        
        # Check 2: Unnormalized domain (e.g., 'test' instead of 'testing')
        if inferred_domain != normalized_domain:
            issues.append(
                f"Unnormalized domain: '{inferred_domain}' normalizes to '{normalized_domain}' "
                f"(consider renaming directory or fixing tags)"
            )
            severity = max(severity, "warning", key=lambda s: ["info", "warning", "error"].index(s))
        
        # Check 3: Unknown domain (might need better categorization)
        if normalized_domain == "unknown":
            metadata = raw_data.get("metadata", {})
            tags = metadata.get("tags", [])
            issues.append(
                f"Unknown domain: Could not infer domain from path '{file_path.parent}' "
                f"or tags {tags}. Consider adding domain-specific tags."
            )
            severity = max(severity, "warning", key=lambda s: ["info", "warning", "error"].index(s))
        
        # Check 4: Missing metadata
        if "metadata" not in raw_data:
            issues.append("Missing metadata section")
            severity = max(severity, "warning", key=lambda s: ["info", "warning", "error"].index(s))
        elif "tags" not in raw_data.get("metadata", {}):
            issues.append("Missing metadata.tags (consider adding for better routing)")
            severity = "info"
        
        # Check 5: Empty prompt
        if not raw_data.get("prompt", "").strip():
            issues.append("Empty prompt field")
            severity = max(severity, "error", key=lambda s: ["info", "warning", "error"].index(s))
        
        # Record anomaly if any issues found
        if issues:
            anomalies.append({
                "file": str(file_path),
                "inferred_domain": inferred_domain,
                "normalized_domain": normalized_domain,
                "severity": severity,
                "issues": issues,
                "tags": raw_data.get("metadata", {}).get("tags", []),
            })
    
    # Generate recommendations
    recommendations = []
    
    # Check for high unknown percentage
    unknown_count = domain_distribution.get("unknown", 0)
    unknown_pct = (unknown_count / total_templates * 100) if total_templates > 0 else 0
    if unknown_pct > 20:
        recommendations.append({
            "priority": "medium",
            "issue": f"High unknown domain percentage: {unknown_pct:.1f}% ({unknown_count}/{total_templates})",
            "action": "Review 'unknown' domain templates and add domain-specific tags or move to appropriate directories"
        })
    
    # Check for unnormalized domains
    unnormalized = [a for a in anomalies if "Unnormalized domain" in str(a.get("issues", []))]
    if unnormalized:
        recommendations.append({
            "priority": "high",
            "issue": f"Found {len(unnormalized)} templates with unnormalized domains",
            "action": "Run: pytest tests/unit/test_domain_normalization.py -v to identify specific cases"
        })
    
    # Check for invalid domains
    invalid = [a for a in anomalies if "Invalid domain" in str(a.get("issues", []))]
    if invalid:
        recommendations.append({
            "priority": "critical",
            "issue": f"Found {len(invalid)} templates with invalid domains",
            "action": "Fix immediately - these will cause routing failures"
        })
    
    # Check for missing metadata
    missing_meta = [a for a in anomalies if "Missing metadata" in str(a.get("issues", []))]
    if missing_meta:
        recommendations.append({
            "priority": "low",
            "issue": f"Found {len(missing_meta)} templates missing metadata sections",
            "action": "Add metadata sections with appropriate tags for better routing"
        })
    
    return {
        "summary": {
            "total_templates": total_templates,
            "anomaly_count": len(anomalies),
            "anomaly_rate_pct": (len(anomalies) / total_templates * 100) if total_templates > 0 else 0,
            "error_count": len([a for a in anomalies if a["severity"] == "error"]),
            "warning_count": len([a for a in anomalies if a["severity"] == "warning"]),
            "info_count": len([a for a in anomalies if a["severity"] == "info"]),
        },
        "domain_distribution": {
            domain: {
                "count": count,
                "percentage": (count / total_templates * 100) if total_templates > 0 else 0
            }
            for domain, count in sorted(domain_distribution.items(), key=lambda x: -x[1])
        },
        "anomalies": anomalies,
        "recommendations": recommendations,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Scan task templates for domain/tag inconsistencies"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="logs/template_anomaly_report.json",
        help="Output JSON file path (default: logs/template_anomaly_report.json)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed output to stdout"
    )
    args = parser.parse_args()
    
    print("Scanning task templates...", file=sys.stderr)
    templates = scan_all_templates()
    print(f"Found {len(templates)} templates", file=sys.stderr)
    
    print("Detecting anomalies...", file=sys.stderr)
    report = detect_anomalies(templates)
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write JSON report
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nReport written to: {output_path}", file=sys.stderr)
    
    # Print summary to stderr
    summary = report["summary"]
    print(f"\n=== Summary ===", file=sys.stderr)
    print(f"Total templates: {summary['total_templates']}", file=sys.stderr)
    print(f"Anomalies found: {summary['anomaly_count']} ({summary['anomaly_rate_pct']:.1f}%)", file=sys.stderr)
    print(f"  - Errors: {summary['error_count']}", file=sys.stderr)
    print(f"  - Warnings: {summary['warning_count']}", file=sys.stderr)
    print(f"  - Info: {summary['info_count']}", file=sys.stderr)
    
    if report["recommendations"]:
        print(f"\n=== Recommendations ({len(report['recommendations'])}) ===", file=sys.stderr)
        for rec in report["recommendations"]:
            print(f"[{rec['priority'].upper()}] {rec['issue']}", file=sys.stderr)
            print(f"  → {rec['action']}", file=sys.stderr)
    
    # Print detailed output if verbose
    if args.verbose:
        print(f"\n=== Domain Distribution ===")
        for domain, stats in report["domain_distribution"].items():
            print(f"{domain:20s}: {stats['count']:3d} ({stats['percentage']:5.1f}%)")
        
        if report["anomalies"]:
            print(f"\n=== Anomalies ({len(report['anomalies'])}) ===")
            for anomaly in report["anomalies"]:
                print(f"\n{anomaly['file']}")
                print(f"  Severity: {anomaly['severity'].upper()}")
                print(f"  Domain: {anomaly['inferred_domain']} → {anomaly['normalized_domain']}")
                for issue in anomaly['issues']:
                    print(f"  - {issue}")
    
    # Exit with non-zero if errors found
    if summary['error_count'] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
