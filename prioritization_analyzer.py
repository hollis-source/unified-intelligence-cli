#!/usr/bin/env python3
"""
Prioritization Analyzer - Creates refactoring priority matrix from naming violations.

This script analyzes the naming violations report and categorizes violations by
priority based on their impact and visibility in the codebase.

Usage:
    python prioritization_analyzer.py [--input naming_violations_report.json]

Outputs:
    - refactoring_priority_matrix.md: Human-readable prioritization matrix
    - phase_2_goals.json: Critical priority violations for Phase 2
    - phase_3_goals.json: High priority violations for Phase 3
    - phase_4_goals.json: Medium priority violations for Phase 4
    - phase_5_goals.json: Low priority violations for Phase 5
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class PriorityCategory:
    """Represents a priority category for refactoring."""
    name: str
    description: str
    phase: int
    violations: List[Dict[str, Any]]
    estimated_hours: float


class PrioritizationAnalyzer:
    """Analyzes violations and creates prioritization matrix."""
    
    def __init__(self, violations_data: Dict[str, Any]):
        self.violations_data = violations_data
        self.violations = violations_data["violations"]
        
        # Define critical paths and patterns
        self.critical_patterns = {
            # Core entities and domain models
            "src/entities/",
            "src/core/",
            # Public interfaces
            "src/interfaces/",
            # Main entry points
            "src/main.py",
            "src/composition.py"
        }
        
        self.high_priority_patterns = {
            # Use cases (business logic)
            "src/use_cases/",
            # Adapters (external integrations)
            "src/adapters/",
            # Orchestration
            "src/claude_orchestrator/",
            # Routing
            "src/routing/",
            # Factories
            "src/factories/"
        }
        
        self.medium_priority_patterns = {
            # Utilities and helpers
            "src/utils/",
            # Monitoring and observability
            "src/monitoring/",
            "src/observability/",
            # Validators
            "src/validators/",
            # DSL components
            "src/dsl/",
            # Project builder
            "src/project_builder/"
        }

    def analyze_and_categorize(self) -> List[PriorityCategory]:
        """Analyze violations and categorize by priority."""
        
        # Initialize categories
        critical = PriorityCategory(
            name="Critical Priority",
            description="Public API functions, core entity names, architectural layer misalignments",
            phase=2,
            violations=[],
            estimated_hours=0.0
        )
        
        high = PriorityCategory(
            name="High Priority", 
            description="Service/use case function names, adapter method names, frequently used utilities",
            phase=3,
            violations=[],
            estimated_hours=0.0
        )
        
        medium = PriorityCategory(
            name="Medium Priority",
            description="Internal helper functions, private methods, test function names",
            phase=4,
            violations=[],
            estimated_hours=0.0
        )
        
        low = PriorityCategory(
            name="Low Priority",
            description="Variable names in small scopes, local helper variables, temporary variables",
            phase=5,
            violations=[],
            estimated_hours=0.0
        )
        
        # Categorize each violation
        for violation in self.violations:
            category = self._determine_priority_category(violation)
            
            if category == "critical":
                critical.violations.append(violation)
            elif category == "high":
                high.violations.append(violation)
            elif category == "medium":
                medium.violations.append(violation)
            else:
                low.violations.append(violation)
        
        # Calculate estimated hours
        critical.estimated_hours = self._estimate_hours(critical.violations)
        high.estimated_hours = self._estimate_hours(high.violations)
        medium.estimated_hours = self._estimate_hours(medium.violations)
        low.estimated_hours = self._estimate_hours(low.violations)
        
        return [critical, high, medium, low]

    def _determine_priority_category(self, violation: Dict[str, Any]) -> str:
        """Determine priority category for a violation."""
        file_path = violation["file_path"]
        violation_type = violation["violation_type"]
        severity = violation["severity"]
        
        # Critical priority conditions
        if any(pattern in file_path for pattern in self.critical_patterns):
            return "critical"
        
        # Function naming in public interfaces is critical
        if (violation_type in ["function_no_verb_noun", "function_boolean_flag"] and
            ("interface" in file_path.lower() or "main.py" in file_path)):
            return "critical"
        
        # Directory structure issues in core areas are critical
        if (violation_type.startswith("directory_") and 
            any(pattern.rstrip("/") in file_path for pattern in self.critical_patterns)):
            return "critical"
        
        # High priority conditions
        if any(pattern in file_path for pattern in self.high_priority_patterns):
            return "high"
        
        # Function naming violations in service layers
        if (violation_type in ["function_no_verb_noun", "function_boolean_flag"] and
            any(pattern in file_path for pattern in self.high_priority_patterns)):
            return "high"
        
        # High severity violations are generally high priority
        if severity == "high":
            return "high"
        
        # Medium priority conditions
        if any(pattern in file_path for pattern in self.medium_priority_patterns):
            return "medium"
        
        # Test files are medium priority
        if "test" in file_path.lower():
            return "medium"
        
        # Function naming in internal code
        if violation_type in ["function_no_verb_noun", "function_boolean_flag"]:
            return "medium"
        
        # Everything else is low priority
        return "low"

    def _estimate_hours(self, violations: List[Dict[str, Any]]) -> float:
        """Estimate hours needed to fix violations in this category."""
        if not violations:
            return 0.0
        
        # Time estimates per violation type (in hours)
        time_estimates = {
            "directory_plural": 0.5,  # Rename directory + update imports
            "directory_ambiguous": 1.0,  # Analyze contents + rename + update imports
            "directory_deep_nesting": 2.0,  # Restructure + update all imports
            "file_not_snake_case": 0.3,  # Rename file + update imports
            "file_cryptic_name": 0.5,  # Analyze purpose + rename + update imports
            "function_no_verb_noun": 0.2,  # Rename function + update calls
            "function_boolean_flag": 1.0,  # Split function + update all calls
            "variable_single_letter": 0.1,  # Rename variable in local scope
            "variable_hungarian_notation": 0.1,  # Remove prefix from variable
        }
        
        total_hours = 0.0
        for violation in violations:
            violation_type = violation["violation_type"]
            base_time = time_estimates.get(violation_type, 0.2)
            
            # Adjust based on severity
            severity_multiplier = {
                "critical": 1.5,
                "high": 1.2,
                "medium": 1.0,
                "low": 0.8
            }
            
            multiplier = severity_multiplier.get(violation["severity"], 1.0)
            total_hours += base_time * multiplier
        
        return round(total_hours, 1)

    def generate_priority_matrix_md(self, categories: List[PriorityCategory]) -> str:
        """Generate Markdown priority matrix."""
        md = "# Refactoring Priority Matrix\n\n"
        md += "**Generated from:** naming_violations_report.json\n"
        md += f"**Total Violations:** {len(self.violations)}\n\n"
        
        md += "## Overview\n\n"
        md += "This matrix categorizes naming violations by priority for systematic refactoring.\n"
        md += "Each phase should be completed before moving to the next.\n\n"
        
        # Summary table
        md += "| Phase | Priority | Violations | Est. Hours | Description |\n"
        md += "|-------|----------|------------|------------|-------------|\n"
        
        for category in categories:
            md += f"| {category.phase} | {category.name} | {len(category.violations)} | {category.estimated_hours}h | {category.description} |\n"
        
        md += "\n"
        
        # Detailed breakdown for each category
        for category in categories:
            if not category.violations:
                continue
                
            md += f"## Phase {category.phase}: {category.name}\n\n"
            md += f"**Estimated Time:** {category.estimated_hours} hours\n"
            md += f"**Total Violations:** {len(category.violations)}\n\n"
            md += f"{category.description}\n\n"
            
            # Group by violation type
            violations_by_type = {}
            for violation in category.violations:
                vtype = violation["violation_type"]
                if vtype not in violations_by_type:
                    violations_by_type[vtype] = []
                violations_by_type[vtype].append(violation)
            
            md += "### Breakdown by Type\n\n"
            for vtype, violations in violations_by_type.items():
                md += f"- **{vtype.replace('_', ' ').title()}:** {len(violations)} violations\n"
            
            md += "\n### Key Files to Refactor\n\n"
            
            # Show top 10 files with most violations
            file_counts = {}
            for violation in category.violations:
                file_path = violation["file_path"]
                file_counts[file_path] = file_counts.get(file_path, 0) + 1
            
            sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
            for file_path, count in sorted_files[:10]:
                md += f"- `{file_path}` ({count} violations)\n"
            
            if len(sorted_files) > 10:
                md += f"- *... and {len(sorted_files) - 10} more files*\n"
            
            md += "\n"
        
        return md

    def generate_phase_goals(self, categories: List[PriorityCategory]) -> Dict[str, Dict]:
        """Generate phase-specific goal files."""
        phase_goals = {}
        
        for category in categories:
            if not category.violations:
                continue
                
            phase_key = f"phase_{category.phase}_goals"
            
            # Group violations by file for easier processing
            files_with_violations = {}
            for violation in category.violations:
                file_path = violation["file_path"]
                if file_path not in files_with_violations:
                    files_with_violations[file_path] = []
                files_with_violations[file_path].append(violation)
            
            phase_goals[phase_key] = {
                "phase": category.phase,
                "priority": category.name,
                "description": category.description,
                "estimated_hours": category.estimated_hours,
                "total_violations": len(category.violations),
                "files_to_refactor": files_with_violations,
                "summary": {
                    "by_type": {},
                    "by_severity": {}
                }
            }
            
            # Add summary statistics
            for violation in category.violations:
                vtype = violation["violation_type"]
                severity = violation["severity"]
                
                phase_goals[phase_key]["summary"]["by_type"][vtype] = \
                    phase_goals[phase_key]["summary"]["by_type"].get(vtype, 0) + 1
                    
                phase_goals[phase_key]["summary"]["by_severity"][severity] = \
                    phase_goals[phase_key]["summary"]["by_severity"].get(severity, 0) + 1
        
        return phase_goals


def main():
    """Main entry point for prioritization analysis."""
    parser = argparse.ArgumentParser(description="Analyze violations and create priority matrix")
    parser.add_argument("--input", type=Path, default="naming_violations_report.json",
                       help="Input violations report JSON file")
    
    args = parser.parse_args()
    
    # Load violations data
    if not args.input.exists():
        print(f"Error: Input file {args.input} not found")
        return 1
    
    with open(args.input) as f:
        violations_data = json.load(f)
    
    # Analyze and categorize
    analyzer = PrioritizationAnalyzer(violations_data)
    categories = analyzer.analyze_and_categorize()
    
    # Generate priority matrix
    matrix_md = analyzer.generate_priority_matrix_md(categories)
    with open("refactoring_priority_matrix.md", "w") as f:
        f.write(matrix_md)
    
    # Generate phase goal files
    phase_goals = analyzer.generate_phase_goals(categories)
    for phase_key, goals in phase_goals.items():
        filename = f"{phase_key}.json"
        with open(filename, "w") as f:
            json.dump(goals, f, indent=2)
    
    print("Prioritization analysis complete!")
    print(f"Generated files:")
    print(f"  - refactoring_priority_matrix.md")
    for phase_key in phase_goals.keys():
        print(f"  - {phase_key}.json")
    
    # Print summary
    print(f"\nSummary:")
    for category in categories:
        print(f"  Phase {category.phase} ({category.name}): {len(category.violations)} violations, {category.estimated_hours}h")


if __name__ == "__main__":
    main()
