"""
Codebase Health Scorer for ATADO

Aggregates signals from all analyzers to compute overall system health score.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Dict, List, Optional, Tuple

from src.analysis.git_analyzer import GitAnalysis
from src.analysis.coverage_analyzer import CoverageAnalysis
from src.analysis.metrics_analyzer import MetricsAnalysis

logger = logging.getLogger(__name__)


@dataclass
class HealthFactor:
    """Individual health factor contribution."""
    name: str
    score: float  # 0-100
    weight: float  # 0-1
    weighted_score: float
    status: str  # excellent, good, fair, poor, critical
    details: str


@dataclass
class ImprovementOpportunity:
    """Identified improvement opportunity."""
    priority: int  # 1-5 (1=highest)
    category: str  # coverage, metrics, code_quality, technical_debt
    description: str
    impact: str  # high, medium, low
    effort: str  # high, medium, low
    estimated_score_gain: float


@dataclass
class HealthScore:
    """Overall system health score."""
    overall_score: float  # 0-100
    grade: str  # A, B, C, D, F
    factors: List[HealthFactor]
    top_opportunities: List[ImprovementOpportunity]
    trend: str  # improving, degrading, stable
    timestamp: str


class HealthScorer:
    """
    Computes overall system health score from multiple signals.
    
    Factors:
    - Coverage (30%): Test coverage percentage
    - Complexity (20%): Code churn and complexity metrics
    - Technical Debt (20%): High-churn files, refactor needs
    - Test Pass Rate (20%): Test success rate
    - Metrics (10%): Routing accuracy, latency, cost trends
    """
    
    # Factor weights
    WEIGHTS = {
        'coverage': 0.30,
        'complexity': 0.20,
        'technical_debt': 0.20,
        'test_pass_rate': 0.20,
        'metrics': 0.10,
    }
    
    def __init__(self):
        """Initialize health scorer."""
        pass
    
    def compute_health(
        self,
        git_analysis: Optional[GitAnalysis] = None,
        coverage_analysis: Optional[CoverageAnalysis] = None,
        metrics_analysis: Optional[MetricsAnalysis] = None,
        test_pass_rate: float = 1.0
    ) -> HealthScore:
        """
        Compute overall health score.
        
        Args:
            git_analysis: Git history analysis
            coverage_analysis: Test coverage analysis
            metrics_analysis: Metrics trend analysis
            test_pass_rate: Test pass rate (0-1)
            
        Returns:
            HealthScore with overall score, factors, and opportunities
        """
        factors = []
        
        # Factor 1: Coverage (30%)
        coverage_factor = self._compute_coverage_factor(coverage_analysis)
        factors.append(coverage_factor)
        
        # Factor 2: Complexity (20%)
        complexity_factor = self._compute_complexity_factor(git_analysis)
        factors.append(complexity_factor)
        
        # Factor 3: Technical Debt (20%)
        debt_factor = self._compute_debt_factor(git_analysis)
        factors.append(debt_factor)
        
        # Factor 4: Test Pass Rate (20%)
        test_factor = self._compute_test_factor(test_pass_rate)
        factors.append(test_factor)
        
        # Factor 5: Metrics (10%)
        metrics_factor = self._compute_metrics_factor(metrics_analysis)
        factors.append(metrics_factor)
        
        # Calculate overall score
        overall_score = sum(f.weighted_score for f in factors)
        
        # Determine grade
        grade = self._score_to_grade(overall_score)
        
        # Identify improvement opportunities
        opportunities = self._identify_opportunities(
            git_analysis,
            coverage_analysis,
            metrics_analysis,
            factors
        )
        
        # Determine trend (would need historical data in production)
        trend = "stable"
        
        return HealthScore(
            overall_score=overall_score,
            grade=grade,
            factors=factors,
            top_opportunities=opportunities[:10],
            trend=trend,
            timestamp=datetime.now(UTC).isoformat()
        )
    
    def _compute_coverage_factor(self, analysis: Optional[CoverageAnalysis]) -> HealthFactor:
        """Compute coverage health factor."""
        if not analysis or analysis.total_modules == 0:
            score = 50.0  # Neutral if no data
            status = "unknown"
            details = "No coverage data available"
        else:
            # Score based on overall coverage
            coverage_pct = analysis.overall_coverage * 100
            score = min(100, coverage_pct * 1.2)  # Scale up slightly
            
            # Penalize for critical uncovered paths
            if analysis.critical_uncovered:
                score -= len(analysis.critical_uncovered) * 5
                score = max(0, score)
            
            status = self._score_to_status(score)
            details = f"{coverage_pct:.1f}% coverage, {len(analysis.low_coverage_modules)} low-coverage modules"
        
        return HealthFactor(
            name="Coverage",
            score=score,
            weight=self.WEIGHTS['coverage'],
            weighted_score=score * self.WEIGHTS['coverage'],
            status=status,
            details=details
        )
    
    def _compute_complexity_factor(self, analysis: Optional[GitAnalysis]) -> HealthFactor:
        """Compute complexity health factor."""
        if not analysis or analysis.total_commits == 0:
            score = 70.0  # Assume decent if no data
            status = "unknown"
            details = "No git history available"
        else:
            # Score based on commit patterns
            # More refactors = better, more bug fixes = worse
            refactor_count = analysis.commit_patterns.get('refactor', type('', (), {'count': 0})).count
            bug_fix_count = analysis.commit_patterns.get('bug_fix', type('', (), {'count': 0})).count
            
            total = analysis.total_commits
            refactor_ratio = refactor_count / total if total > 0 else 0
            bug_ratio = bug_fix_count / total if total > 0 else 0
            
            # Base score
            score = 70.0
            
            # Bonus for refactors
            score += refactor_ratio * 30
            
            # Penalty for bug fixes
            score -= bug_ratio * 20
            
            score = max(0, min(100, score))
            status = self._score_to_status(score)
            details = f"{refactor_count} refactors, {bug_fix_count} bug fixes in {total} commits"
        
        return HealthFactor(
            name="Complexity",
            score=score,
            weight=self.WEIGHTS['complexity'],
            weighted_score=score * self.WEIGHTS['complexity'],
            status=status,
            details=details
        )
    
    def _compute_debt_factor(self, analysis: Optional[GitAnalysis]) -> HealthFactor:
        """Compute technical debt health factor."""
        if not analysis:
            score = 70.0
            status = "unknown"
            details = "No git history available"
        else:
            # Score based on high-churn files
            high_churn_count = len(analysis.high_churn_files)
            
            # Base score
            score = 90.0
            
            # Penalty for high-churn files (indicates instability)
            score -= high_churn_count * 3
            
            score = max(0, min(100, score))
            status = self._score_to_status(score)
            details = f"{high_churn_count} high-churn files"
        
        return HealthFactor(
            name="Technical Debt",
            score=score,
            weight=self.WEIGHTS['technical_debt'],
            weighted_score=score * self.WEIGHTS['technical_debt'],
            status=status,
            details=details
        )
    
    def _compute_test_factor(self, test_pass_rate: float) -> HealthFactor:
        """Compute test pass rate health factor."""
        score = test_pass_rate * 100
        status = self._score_to_status(score)
        details = f"{test_pass_rate:.1%} tests passing"
        
        return HealthFactor(
            name="Test Pass Rate",
            score=score,
            weight=self.WEIGHTS['test_pass_rate'],
            weighted_score=score * self.WEIGHTS['test_pass_rate'],
            status=status,
            details=details
        )
    
    def _compute_metrics_factor(self, analysis: Optional[MetricsAnalysis]) -> HealthFactor:
        """Compute metrics health factor."""
        if not analysis:
            score = 70.0
            status = "unknown"
            details = "No metrics data available"
        else:
            # Base score
            score = 80.0
            
            # Penalty for degrading metrics
            critical_degrading = [m for m in analysis.degrading_metrics if m.severity == 'critical']
            warning_degrading = [m for m in analysis.degrading_metrics if m.severity == 'warning']
            
            score -= len(critical_degrading) * 15
            score -= len(warning_degrading) * 5
            
            # Bonus for improving metrics
            score += len(analysis.improving_metrics) * 3
            
            score = max(0, min(100, score))
            status = self._score_to_status(score)
            details = f"{len(analysis.degrading_metrics)} degrading, {len(analysis.improving_metrics)} improving"
        
        return HealthFactor(
            name="Metrics",
            score=score,
            weight=self.WEIGHTS['metrics'],
            weighted_score=score * self.WEIGHTS['metrics'],
            status=status,
            details=details
        )
    
    def _identify_opportunities(
        self,
        git_analysis: Optional[GitAnalysis],
        coverage_analysis: Optional[CoverageAnalysis],
        metrics_analysis: Optional[MetricsAnalysis],
        factors: List[HealthFactor]
    ) -> List[ImprovementOpportunity]:
        """Identify top improvement opportunities."""
        opportunities = []
        
        # Coverage opportunities
        if coverage_analysis and coverage_analysis.priority_list:
            for i, (module, cov, reason) in enumerate(coverage_analysis.priority_list[:5]):
                opportunities.append(ImprovementOpportunity(
                    priority=1 if i == 0 else 2,
                    category="coverage",
                    description=f"Add tests for {module} - {reason}",
                    impact="high" if "critical" in reason.lower() else "medium",
                    effort="medium",
                    estimated_score_gain=5.0
                ))
        
        # Metrics opportunities
        if metrics_analysis:
            for metric in metrics_analysis.degrading_metrics:
                if metric.severity in ['critical', 'warning']:
                    opportunities.append(ImprovementOpportunity(
                        priority=1 if metric.severity == 'critical' else 2,
                        category="metrics",
                        description=metric.recommendation,
                        impact="high" if metric.severity == 'critical' else "medium",
                        effort="medium",
                        estimated_score_gain=3.0
                    ))
        
        # Technical debt opportunities
        if git_analysis and git_analysis.high_churn_files:
            for file_churn in git_analysis.high_churn_files[:3]:
                opportunities.append(ImprovementOpportunity(
                    priority=3,
                    category="technical_debt",
                    description=f"Refactor {file_churn.file_path} ({file_churn.commit_count} commits)",
                    impact="medium",
                    effort="high",
                    estimated_score_gain=2.0
                ))
        
        # Sort by priority and estimated gain
        opportunities.sort(key=lambda x: (x.priority, -x.estimated_score_gain))
        
        return opportunities
    
    @staticmethod
    def _score_to_status(score: float) -> str:
        """Convert score to status."""
        if score >= 90:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 60:
            return "fair"
        elif score >= 40:
            return "poor"
        else:
            return "critical"
    
    @staticmethod
    def _score_to_grade(score: float) -> str:
        """Convert score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

