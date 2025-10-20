#!/usr/bin/env python3
"""
Impact Analyzer - Analyzes the impact of naming refactoring on the codebase.

This script performs comprehensive impact analysis for high/critical priority
naming violations to understand dependencies, test coverage, and documentation
references that will be affected by refactoring.

Usage:
    python impact_analyzer.py [--violations naming_violations_report.json] [--phase-goals phase_2_goals.json phase_3_goals.json]

Outputs:
    - impact_analysis_report.json: Detailed impact analysis
    - breaking_changes_forecast.md: Human-readable breaking changes forecast
    - test_update_requirements.md: Test update requirements
"""

import ast
import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, asdict
import subprocess


@dataclass
class DependencyInfo:
    """Information about a dependency relationship."""
    source_file: str
    target_file: str
    import_type: str  # "import", "from_import", "function_call", "class_usage"
    line_number: int
    context: str


@dataclass
class TestCoverage:
    """Test coverage information for a violation."""
    violation_file: str
    violation_name: str
    test_files: List[str]
    coverage_percentage: Optional[float]
    missing_tests: List[str]


@dataclass
class DocumentationReference:
    """Documentation reference to a violated name."""
    doc_file: str
    line_number: int
    context: str
    reference_type: str  # "example", "api_doc", "readme", "comment"


@dataclass
class ImpactAnalysis:
    """Complete impact analysis for a violation."""
    violation: Dict[str, Any]
    dependencies: List[DependencyInfo]
    test_coverage: TestCoverage
    documentation_refs: List[DocumentationReference]
    breaking_change_risk: str  # "low", "medium", "high", "critical"
    estimated_update_time: float  # hours


class ImpactAnalyzer:
    """Analyzes the impact of naming violations on the codebase."""
    
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.python_files = list(root_path.rglob("*.py"))
        self.doc_files = list(root_path.rglob("*.md")) + list(root_path.rglob("*.rst"))
        
        # Cache for parsed ASTs
        self.ast_cache: Dict[str, ast.AST] = {}
        
        # Cache for file contents
        self.content_cache: Dict[str, str] = {}

    def analyze_violations(self, violations: List[Dict[str, Any]]) -> List[ImpactAnalysis]:
        """Analyze impact for a list of violations."""
        analyses = []
        
        print(f"Analyzing impact for {len(violations)} violations...")
        
        for i, violation in enumerate(violations):
            if i % 10 == 0:
                print(f"Progress: {i}/{len(violations)}")
            
            analysis = self._analyze_single_violation(violation)
            analyses.append(analysis)
        
        return analyses

    def _analyze_single_violation(self, violation: Dict[str, Any]) -> ImpactAnalysis:
        """Analyze impact for a single violation."""
        
        # Find dependencies
        dependencies = self._find_dependencies(violation)
        
        # Analyze test coverage
        test_coverage = self._analyze_test_coverage(violation)
        
        # Find documentation references
        doc_refs = self._find_documentation_references(violation)
        
        # Assess breaking change risk
        risk = self._assess_breaking_change_risk(violation, dependencies)
        
        # Estimate update time
        update_time = self._estimate_update_time(violation, dependencies, doc_refs)
        
        return ImpactAnalysis(
            violation=violation,
            dependencies=dependencies,
            test_coverage=test_coverage,
            documentation_refs=doc_refs,
            breaking_change_risk=risk,
            estimated_update_time=update_time
        )

    def _find_dependencies(self, violation: Dict[str, Any]) -> List[DependencyInfo]:
        """Find files that depend on the violated name."""
        dependencies = []
        file_path = violation["file_path"]
        current_name = violation["current_name"]
        violation_type = violation["violation_type"]
        
        if violation_type.startswith("directory_"):
            # For directory violations, find imports
            dependencies.extend(self._find_directory_dependencies(file_path, current_name))
        elif violation_type.startswith("file_"):
            # For file violations, find imports
            dependencies.extend(self._find_file_dependencies(file_path, current_name))
        elif violation_type.startswith("function_"):
            # For function violations, find function calls
            dependencies.extend(self._find_function_dependencies(file_path, current_name))
        elif violation_type.startswith("variable_"):
            # For variable violations, find variable usage
            dependencies.extend(self._find_variable_dependencies(file_path, current_name))
        
        return dependencies

    def _find_directory_dependencies(self, dir_path: str, dir_name: str) -> List[DependencyInfo]:
        """Find dependencies on a directory (import statements)."""
        dependencies = []
        
        # Search for imports that reference this directory
        import_patterns = [
            rf"from\s+{re.escape(dir_path.replace('/', '.'))}\s+import",
            rf"import\s+{re.escape(dir_path.replace('/', '.'))}"
        ]
        
        for py_file in self.python_files:
            content = self._get_file_content(py_file)
            if not content:
                continue
            
            lines = content.splitlines()
            for line_num, line in enumerate(lines, 1):
                for pattern in import_patterns:
                    if re.search(pattern, line):
                        dependencies.append(DependencyInfo(
                            source_file=str(py_file.relative_to(self.root_path)),
                            target_file=dir_path,
                            import_type="from_import" if "from" in line else "import",
                            line_number=line_num,
                            context=line.strip()
                        ))
        
        return dependencies

    def _find_file_dependencies(self, file_path: str, file_name: str) -> List[DependencyInfo]:
        """Find dependencies on a file (import statements)."""
        dependencies = []
        
        # Convert file path to module path
        module_path = file_path.replace("/", ".").replace(".py", "")
        
        import_patterns = [
            rf"from\s+{re.escape(module_path)}\s+import",
            rf"import\s+{re.escape(module_path)}"
        ]
        
        for py_file in self.python_files:
            if str(py_file.relative_to(self.root_path)) == file_path:
                continue  # Skip the file itself
            
            content = self._get_file_content(py_file)
            if not content:
                continue
            
            lines = content.splitlines()
            for line_num, line in enumerate(lines, 1):
                for pattern in import_patterns:
                    if re.search(pattern, line):
                        dependencies.append(DependencyInfo(
                            source_file=str(py_file.relative_to(self.root_path)),
                            target_file=file_path,
                            import_type="from_import" if "from" in line else "import",
                            line_number=line_num,
                            context=line.strip()
                        ))
        
        return dependencies

    def _find_function_dependencies(self, file_path: str, func_name: str) -> List[DependencyInfo]:
        """Find dependencies on a function (function calls)."""
        dependencies = []
        
        # Search for function calls
        call_pattern = rf"\b{re.escape(func_name)}\s*\("
        
        for py_file in self.python_files:
            content = self._get_file_content(py_file)
            if not content:
                continue
            
            lines = content.splitlines()
            for line_num, line in enumerate(lines, 1):
                if re.search(call_pattern, line):
                    dependencies.append(DependencyInfo(
                        source_file=str(py_file.relative_to(self.root_path)),
                        target_file=file_path,
                        import_type="function_call",
                        line_number=line_num,
                        context=line.strip()
                    ))
        
        return dependencies

    def _find_variable_dependencies(self, file_path: str, var_name: str) -> List[DependencyInfo]:
        """Find dependencies on a variable (variable usage)."""
        dependencies = []
        
        # For variables, we only look within the same file
        target_file = self.root_path / file_path
        if not target_file.exists():
            return dependencies
        
        content = self._get_file_content(target_file)
        if not content:
            return dependencies
        
        # Search for variable usage
        var_pattern = rf"\b{re.escape(var_name)}\b"
        lines = content.splitlines()
        
        for line_num, line in enumerate(lines, 1):
            if re.search(var_pattern, line):
                dependencies.append(DependencyInfo(
                    source_file=file_path,
                    target_file=file_path,
                    import_type="variable_usage",
                    line_number=line_num,
                    context=line.strip()
                ))
        
        return dependencies

    def _analyze_test_coverage(self, violation: Dict[str, Any]) -> TestCoverage:
        """Analyze test coverage for a violation."""
        file_path = violation["file_path"]
        current_name = violation["current_name"]
        
        # Find test files that might test this violation
        test_files = []
        
        # Look for test files with similar names
        test_patterns = [
            f"test_{current_name}",
            f"test_{file_path.replace('/', '_').replace('.py', '')}",
            f"{current_name}_test"
        ]
        
        for test_file in self.python_files:
            if "test" in str(test_file):
                test_content = self._get_file_content(test_file)
                if test_content and current_name in test_content:
                    test_files.append(str(test_file.relative_to(self.root_path)))
        
        return TestCoverage(
            violation_file=file_path,
            violation_name=current_name,
            test_files=test_files,
            coverage_percentage=None,  # Would need coverage tool integration
            missing_tests=[]  # Would need deeper analysis
        )

    def _find_documentation_references(self, violation: Dict[str, Any]) -> List[DocumentationReference]:
        """Find documentation references to the violated name."""
        references = []
        current_name = violation["current_name"]
        
        # Search in documentation files
        for doc_file in self.doc_files:
            content = self._get_file_content(doc_file)
            if not content:
                continue
            
            lines = content.splitlines()
            for line_num, line in enumerate(lines, 1):
                if current_name in line:
                    references.append(DocumentationReference(
                        doc_file=str(doc_file.relative_to(self.root_path)),
                        line_number=line_num,
                        context=line.strip(),
                        reference_type="readme" if "readme" in doc_file.name.lower() else "documentation"
                    ))
        
        return references

    def _assess_breaking_change_risk(self, violation: Dict[str, Any], dependencies: List[DependencyInfo]) -> str:
        """Assess the risk level of breaking changes."""
        file_path = violation["file_path"]
        violation_type = violation["violation_type"]
        
        # High risk factors
        if "interface" in file_path.lower() or "main.py" in file_path:
            return "critical"
        
        if violation_type.startswith("directory_") and len(dependencies) > 10:
            return "high"
        
        if violation_type.startswith("function_") and len(dependencies) > 5:
            return "high"
        
        # Medium risk factors
        if len(dependencies) > 3:
            return "medium"
        
        if "src/" in file_path and not "test" in file_path:
            return "medium"
        
        # Low risk
        return "low"

    def _estimate_update_time(self, violation: Dict[str, Any], dependencies: List[DependencyInfo], 
                            doc_refs: List[DocumentationReference]) -> float:
        """Estimate time needed to update all dependencies."""
        base_time = 0.5  # Base time for the violation itself
        
        # Add time for each dependency
        dependency_time = len(dependencies) * 0.1
        
        # Add time for documentation updates
        doc_time = len(doc_refs) * 0.2
        
        # Add complexity multiplier based on violation type
        complexity_multipliers = {
            "directory_plural": 2.0,  # Requires import updates
            "directory_ambiguous": 3.0,  # Requires analysis + updates
            "function_boolean_flag": 2.5,  # Requires function splitting
            "function_no_verb_noun": 1.0,  # Simple rename
        }
        
        violation_type = violation["violation_type"]
        multiplier = complexity_multipliers.get(violation_type, 1.0)
        
        return round((base_time + dependency_time + doc_time) * multiplier, 1)

    def _get_file_content(self, file_path: Path) -> Optional[str]:
        """Get file content with caching."""
        file_key = str(file_path)
        
        if file_key in self.content_cache:
            return self.content_cache[file_key]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.content_cache[file_key] = content
                return content
        except (UnicodeDecodeError, FileNotFoundError):
            self.content_cache[file_key] = None
            return None


def generate_reports(analyses: List[ImpactAnalysis], output_dir: Path):
    """Generate impact analysis reports."""
    
    # Generate JSON report
    json_report = {
        "summary": {
            "total_violations_analyzed": len(analyses),
            "breaking_change_risk": {
                "critical": len([a for a in analyses if a.breaking_change_risk == "critical"]),
                "high": len([a for a in analyses if a.breaking_change_risk == "high"]),
                "medium": len([a for a in analyses if a.breaking_change_risk == "medium"]),
                "low": len([a for a in analyses if a.breaking_change_risk == "low"])
            },
            "total_dependencies": sum(len(a.dependencies) for a in analyses),
            "total_test_files_affected": sum(len(a.test_coverage.test_files) for a in analyses),
            "total_doc_references": sum(len(a.documentation_refs) for a in analyses),
            "estimated_total_update_time": sum(a.estimated_update_time for a in analyses)
        },
        "analyses": [asdict(analysis) for analysis in analyses]
    }
    
    # Write JSON report
    json_path = output_dir / "impact_analysis_report.json"
    with open(json_path, 'w') as f:
        json.dump(json_report, f, indent=2)
    
    # Generate breaking changes forecast
    breaking_changes_md = generate_breaking_changes_forecast(analyses)
    breaking_path = output_dir / "breaking_changes_forecast.md"
    with open(breaking_path, 'w') as f:
        f.write(breaking_changes_md)
    
    # Generate test update requirements
    test_requirements_md = generate_test_update_requirements(analyses)
    test_path = output_dir / "test_update_requirements.md"
    with open(test_path, 'w') as f:
        f.write(test_requirements_md)
    
    print(f"Impact analysis reports generated:")
    print(f"  JSON: {json_path}")
    print(f"  Breaking changes: {breaking_path}")
    print(f"  Test requirements: {test_path}")


def generate_breaking_changes_forecast(analyses: List[ImpactAnalysis]) -> str:
    """Generate breaking changes forecast markdown."""
    md = "# Breaking Changes Forecast\n\n"
    md += f"**Total Violations Analyzed:** {len(analyses)}\n"
    md += f"**Total Dependencies:** {sum(len(a.dependencies) for a in analyses)}\n"
    md += f"**Estimated Update Time:** {sum(a.estimated_update_time for a in analyses):.1f} hours\n\n"
    
    # Group by risk level
    for risk_level in ["critical", "high", "medium", "low"]:
        risk_analyses = [a for a in analyses if a.breaking_change_risk == risk_level]
        if not risk_analyses:
            continue
        
        md += f"## {risk_level.title()} Risk Changes\n\n"
        md += f"**Count:** {len(risk_analyses)}\n"
        md += f"**Estimated Time:** {sum(a.estimated_update_time for a in risk_analyses):.1f} hours\n\n"
        
        for analysis in risk_analyses[:5]:  # Show top 5
            violation = analysis.violation
            md += f"### {violation['current_name']}\n"
            md += f"- **File:** `{violation['file_path']}`\n"
            md += f"- **Type:** {violation['violation_type']}\n"
            md += f"- **Dependencies:** {len(analysis.dependencies)}\n"
            md += f"- **Update Time:** {analysis.estimated_update_time}h\n\n"
        
        if len(risk_analyses) > 5:
            md += f"*... and {len(risk_analyses) - 5} more {risk_level} risk changes*\n\n"
    
    return md


def generate_test_update_requirements(analyses: List[ImpactAnalysis]) -> str:
    """Generate test update requirements markdown."""
    md = "# Test Update Requirements\n\n"
    
    # Collect all test files that need updates
    test_files_affected = set()
    for analysis in analyses:
        test_files_affected.update(analysis.test_coverage.test_files)
    
    md += f"**Test Files Requiring Updates:** {len(test_files_affected)}\n\n"
    
    if test_files_affected:
        md += "## Test Files to Update\n\n"
        for test_file in sorted(test_files_affected):
            md += f"- `{test_file}`\n"
        md += "\n"
    
    # Group violations by test impact
    md += "## Violations Requiring Test Updates\n\n"
    
    for analysis in analyses:
        if analysis.test_coverage.test_files:
            violation = analysis.violation
            md += f"### {violation['current_name']}\n"
            md += f"- **File:** `{violation['file_path']}`\n"
            md += f"- **Test Files:** {len(analysis.test_coverage.test_files)}\n"
            for test_file in analysis.test_coverage.test_files:
                md += f"  - `{test_file}`\n"
            md += "\n"
    
    return md


def main():
    """Main entry point for impact analysis."""
    parser = argparse.ArgumentParser(description="Analyze impact of naming violations")
    parser.add_argument("--violations", type=Path, default="naming_violations_report.json",
                       help="Violations report JSON file")
    parser.add_argument("--phase-goals", nargs="+", type=Path,
                       default=["phase_2_goals.json", "phase_3_goals.json"],
                       help="Phase goal files to analyze")
    
    args = parser.parse_args()
    
    # Load violations to analyze (high/critical priority only)
    violations_to_analyze = []
    
    for phase_file in args.phase_goals:
        phase_path = Path(phase_file)
        if phase_path.exists():
            with open(phase_path) as f:
                phase_data = json.load(f)
            
            # Extract violations from phase data
            for file_path, file_violations in phase_data["files_to_refactor"].items():
                violations_to_analyze.extend(file_violations)
    
    if not violations_to_analyze:
        print("No violations found to analyze")
        return 1
    
    # Perform impact analysis
    analyzer = ImpactAnalyzer(Path("."))
    analyses = analyzer.analyze_violations(violations_to_analyze)
    
    # Generate reports
    generate_reports(analyses, Path("."))
    
    print(f"\nImpact analysis complete!")
    print(f"Analyzed {len(violations_to_analyze)} high/critical priority violations")


if __name__ == "__main__":
    main()
