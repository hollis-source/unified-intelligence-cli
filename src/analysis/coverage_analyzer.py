"""
Test Coverage Analyzer for ATADO

Analyzes test coverage reports to identify uncovered code paths and low-coverage modules.
"""
from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ModuleCoverage:
    """Coverage metrics for a module."""
    module_path: str
    line_coverage: float  # 0.0-1.0
    branch_coverage: float  # 0.0-1.0
    lines_covered: int
    lines_total: int
    branches_covered: int
    branches_total: int
    uncovered_lines: List[int] = field(default_factory=list)


@dataclass
class CoverageAnalysis:
    """Results of coverage analysis."""
    overall_coverage: float  # 0.0-1.0
    low_coverage_modules: List[ModuleCoverage]  # <70% coverage
    uncovered_files: List[str]  # 0% coverage
    critical_uncovered: List[str]  # Critical paths without tests
    priority_list: List[Tuple[str, float, str]]  # (module, coverage, reason)
    total_modules: int
    timestamp: str


class CoverageAnalyzer:
    """
    Analyzes test coverage to identify improvement opportunities.
    
    Features:
    - Parse coverage reports (coverage.xml, .coverage)
    - Identify uncovered code paths
    - Detect low-coverage modules (<70%)
    - Prioritize critical paths without tests
    - Generate improvement recommendations
    """
    
    # Critical path patterns (should have high coverage)
    CRITICAL_PATTERNS = [
        'routing',
        'execution',
        'safety',
        'security',
        'auth',
        'payment',
        'database',
        'api',
    ]
    
    def __init__(self, coverage_threshold: float = 0.70):
        """
        Initialize coverage analyzer.
        
        Args:
            coverage_threshold: Minimum acceptable coverage (default: 0.70)
        """
        self.coverage_threshold = coverage_threshold
    
    def analyze(self, coverage_file: str = "coverage.xml") -> CoverageAnalysis:
        """
        Analyze coverage report.
        
        Args:
            coverage_file: Path to coverage report (XML format)
            
        Returns:
            CoverageAnalysis with uncovered files, low-coverage modules, priorities
        """
        coverage_path = Path(coverage_file)
        
        if not coverage_path.exists():
            logger.warning(f"Coverage file not found: {coverage_file}")
            return self._empty_analysis()
        
        # Parse coverage report
        modules = self._parse_coverage_xml(coverage_path)
        
        if not modules:
            logger.warning("No coverage data found")
            return self._empty_analysis()
        
        # Calculate overall coverage
        total_lines = sum(m.lines_total for m in modules)
        covered_lines = sum(m.lines_covered for m in modules)
        overall_coverage = covered_lines / total_lines if total_lines > 0 else 0.0
        
        # Identify low-coverage modules
        low_coverage = [
            m for m in modules
            if m.line_coverage < self.coverage_threshold
        ]
        
        # Identify uncovered files
        uncovered = [
            m.module_path for m in modules
            if m.line_coverage == 0.0
        ]
        
        # Identify critical uncovered paths
        critical_uncovered = self._identify_critical_uncovered(modules)
        
        # Generate priority list
        priority_list = self._prioritize_modules(modules)
        
        return CoverageAnalysis(
            overall_coverage=overall_coverage,
            low_coverage_modules=low_coverage,
            uncovered_files=uncovered,
            critical_uncovered=critical_uncovered,
            priority_list=priority_list,
            total_modules=len(modules),
            timestamp=datetime.now(UTC).isoformat()
        )
    
    def _parse_coverage_xml(self, coverage_path: Path) -> List[ModuleCoverage]:
        """Parse coverage.xml file."""
        try:
            tree = ET.parse(coverage_path)
            root = tree.getroot()
            
            modules = []
            
            # Find all class elements (representing modules/files)
            for package in root.findall('.//package'):
                for cls in package.findall('classes/class'):
                    filename = cls.get('filename', '')
                    
                    # Get line coverage
                    lines = cls.findall('lines/line')
                    lines_total = len(lines)
                    lines_covered = sum(1 for line in lines if int(line.get('hits', 0)) > 0)
                    
                    # Get uncovered line numbers
                    uncovered_lines = [
                        int(line.get('number', 0))
                        for line in lines
                        if int(line.get('hits', 0)) == 0
                    ]
                    
                    # Calculate coverage
                    line_coverage = lines_covered / lines_total if lines_total > 0 else 0.0
                    
                    # Branch coverage (if available)
                    branches_total = 0
                    branches_covered = 0
                    for line in lines:
                        if line.get('branch') == 'true':
                            branches_total += 1
                            if int(line.get('hits', 0)) > 0:
                                branches_covered += 1
                    
                    branch_coverage = branches_covered / branches_total if branches_total > 0 else 1.0
                    
                    modules.append(ModuleCoverage(
                        module_path=filename,
                        line_coverage=line_coverage,
                        branch_coverage=branch_coverage,
                        lines_covered=lines_covered,
                        lines_total=lines_total,
                        branches_covered=branches_covered,
                        branches_total=branches_total,
                        uncovered_lines=uncovered_lines
                    ))
            
            return modules
            
        except Exception as e:
            logger.error(f"Failed to parse coverage XML: {e}")
            return []
    
    def _identify_critical_uncovered(self, modules: List[ModuleCoverage]) -> List[str]:
        """Identify critical paths without adequate coverage."""
        critical = []
        
        for module in modules:
            # Check if module is critical
            is_critical = any(
                pattern in module.module_path.lower()
                for pattern in self.CRITICAL_PATTERNS
            )
            
            if is_critical and module.line_coverage < self.coverage_threshold:
                critical.append(module.module_path)
        
        return critical
    
    def _prioritize_modules(self, modules: List[ModuleCoverage]) -> List[Tuple[str, float, str]]:
        """
        Prioritize modules for test improvement.
        
        Returns:
            List of (module_path, coverage, reason) tuples, sorted by priority
        """
        priorities = []
        
        for module in modules:
            if module.line_coverage >= self.coverage_threshold:
                continue  # Already has good coverage
            
            # Calculate priority score
            coverage_gap = self.coverage_threshold - module.line_coverage
            
            # Check if critical
            is_critical = any(
                pattern in module.module_path.lower()
                for pattern in self.CRITICAL_PATTERNS
            )
            
            # Priority score: coverage_gap * (2 if critical else 1) * lines_total
            priority_score = coverage_gap * (2.0 if is_critical else 1.0) * module.lines_total
            
            # Determine reason
            if module.line_coverage == 0.0:
                reason = "No tests"
            elif is_critical:
                reason = f"Critical path, {module.line_coverage:.1%} coverage"
            else:
                reason = f"Low coverage ({module.line_coverage:.1%})"
            
            priorities.append((
                module.module_path,
                module.line_coverage,
                reason,
                priority_score
            ))
        
        # Sort by priority score (descending)
        priorities.sort(key=lambda x: x[3], reverse=True)
        
        # Return top 20 without priority score
        return [(path, cov, reason) for path, cov, reason, _ in priorities[:20]]
    
    def _empty_analysis(self) -> CoverageAnalysis:
        """Return empty analysis when no coverage data available."""
        return CoverageAnalysis(
            overall_coverage=0.0,
            low_coverage_modules=[],
            uncovered_files=[],
            critical_uncovered=[],
            priority_list=[],
            total_modules=0,
            timestamp=datetime.now(UTC).isoformat()
        )

