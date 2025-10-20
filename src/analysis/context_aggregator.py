"""
Context Aggregator for ATADO

Combines all analyzer outputs into a unified system context for task generation.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Dict, List, Optional

from src.analysis.git_analyzer import GitAnalyzer, GitAnalysis
from src.analysis.coverage_analyzer import CoverageAnalyzer, CoverageAnalysis
from src.analysis.metrics_analyzer import MetricsAnalyzer, MetricsAnalysis
from src.analysis.health_scorer import HealthScorer, HealthScore, ImprovementOpportunity

logger = logging.getLogger(__name__)


@dataclass
class SystemContext:
    """Unified system context for task generation."""
    health_score: HealthScore
    git_analysis: Optional[GitAnalysis]
    coverage_analysis: Optional[CoverageAnalysis]
    metrics_analysis: Optional[MetricsAnalysis]
    ranked_opportunities: List[ImprovementOpportunity]
    summary: str
    timestamp: str


class ContextAggregator:
    """
    Aggregates all analyzer outputs into unified system context.
    
    Features:
    - Run all analyzers
    - Compute health score
    - Rank improvement opportunities
    - Generate context summary
    """
    
    def __init__(
        self,
        repo_path: str = ".",
        coverage_file: str = "coverage.xml",
        db_store: Optional[any] = None
    ):
        """
        Initialize context aggregator.
        
        Args:
            repo_path: Path to git repository
            coverage_file: Path to coverage report
            db_store: Database store for metrics
        """
        self.repo_path = repo_path
        self.coverage_file = coverage_file
        self.db_store = db_store
        
        # Initialize analyzers
        try:
            self.git_analyzer = GitAnalyzer(repo_path=repo_path)
        except ValueError:
            logger.warning(f"Not a git repository: {repo_path}")
            self.git_analyzer = None
        
        self.coverage_analyzer = CoverageAnalyzer()
        self.metrics_analyzer = MetricsAnalyzer(db_store=db_store)
        self.health_scorer = HealthScorer()
    
    async def aggregate(
        self,
        analysis_days: int = 30,
        test_pass_rate: float = 1.0
    ) -> SystemContext:
        """
        Run all analyzers and aggregate results.
        
        Args:
            analysis_days: Number of days to analyze
            test_pass_rate: Current test pass rate (0-1)
            
        Returns:
            SystemContext with all analyses and ranked opportunities
        """
        logger.info("Starting context aggregation...")
        
        # Run git analysis
        git_analysis = None
        if self.git_analyzer:
            try:
                git_analysis = self.git_analyzer.analyze(days=analysis_days)
                logger.info(f"Git analysis: {git_analysis.total_commits} commits, {len(git_analysis.high_churn_files)} high-churn files")
            except Exception as e:
                logger.error(f"Git analysis failed: {e}")
        
        # Run coverage analysis
        coverage_analysis = None
        try:
            coverage_analysis = self.coverage_analyzer.analyze(coverage_file=self.coverage_file)
            logger.info(f"Coverage analysis: {coverage_analysis.overall_coverage:.1%} overall, {len(coverage_analysis.low_coverage_modules)} low-coverage modules")
        except Exception as e:
            logger.error(f"Coverage analysis failed: {e}")
        
        # Run metrics analysis
        metrics_analysis = None
        try:
            metrics_analysis = await self.metrics_analyzer.analyze(days=analysis_days)
            logger.info(f"Metrics analysis: {len(metrics_analysis.degrading_metrics)} degrading, {len(metrics_analysis.anomalies)} anomalies")
        except Exception as e:
            logger.error(f"Metrics analysis failed: {e}")
        
        # Compute health score
        health_score = self.health_scorer.compute_health(
            git_analysis=git_analysis,
            coverage_analysis=coverage_analysis,
            metrics_analysis=metrics_analysis,
            test_pass_rate=test_pass_rate
        )
        
        logger.info(f"Health score: {health_score.overall_score:.1f}/100 (Grade: {health_score.grade})")
        
        # Rank opportunities (already done in health scorer)
        ranked_opportunities = health_score.top_opportunities
        
        # Generate summary
        summary = self._generate_summary(health_score, git_analysis, coverage_analysis, metrics_analysis)
        
        return SystemContext(
            health_score=health_score,
            git_analysis=git_analysis,
            coverage_analysis=coverage_analysis,
            metrics_analysis=metrics_analysis,
            ranked_opportunities=ranked_opportunities,
            summary=summary,
            timestamp=datetime.now(UTC).isoformat()
        )
    
    def _generate_summary(
        self,
        health_score: HealthScore,
        git_analysis: Optional[GitAnalysis],
        coverage_analysis: Optional[CoverageAnalysis],
        metrics_analysis: Optional[MetricsAnalysis]
    ) -> str:
        """Generate human-readable summary of system context."""
        lines = []
        
        # Overall health
        lines.append(f"System Health: {health_score.overall_score:.1f}/100 (Grade: {health_score.grade})")
        lines.append("")
        
        # Factor breakdown
        lines.append("Health Factors:")
        for factor in health_score.factors:
            lines.append(f"  - {factor.name}: {factor.score:.1f}/100 ({factor.status}) - {factor.details}")
        lines.append("")
        
        # Git insights
        if git_analysis:
            lines.append(f"Git Activity ({git_analysis.analysis_period_days} days):")
            lines.append(f"  - {git_analysis.total_commits} commits")
            lines.append(f"  - {len(git_analysis.high_churn_files)} high-churn files")
            
            if git_analysis.commit_patterns:
                patterns_str = ", ".join([f"{p.count} {p.pattern_type}" for p in git_analysis.commit_patterns.values()])
                lines.append(f"  - Patterns: {patterns_str}")
            lines.append("")
        
        # Coverage insights
        if coverage_analysis:
            lines.append("Test Coverage:")
            lines.append(f"  - Overall: {coverage_analysis.overall_coverage:.1%}")
            lines.append(f"  - Low-coverage modules: {len(coverage_analysis.low_coverage_modules)}")
            lines.append(f"  - Critical uncovered: {len(coverage_analysis.critical_uncovered)}")
            lines.append("")
        
        # Metrics insights
        if metrics_analysis:
            lines.append("Metrics Trends:")
            lines.append(f"  - Degrading: {len(metrics_analysis.degrading_metrics)}")
            lines.append(f"  - Improving: {len(metrics_analysis.improving_metrics)}")
            lines.append(f"  - Anomalies: {len(metrics_analysis.anomalies)}")
            
            if metrics_analysis.degrading_metrics:
                lines.append("  - Critical issues:")
                for metric in metrics_analysis.degrading_metrics[:3]:
                    if metric.severity in ['critical', 'warning']:
                        lines.append(f"    • {metric.metric_name}: {metric.change_percent:+.1f}%")
            lines.append("")
        
        # Top opportunities
        lines.append("Top Improvement Opportunities:")
        for i, opp in enumerate(health_score.top_opportunities[:5], 1):
            lines.append(f"  {i}. [{opp.category}] {opp.description}")
            lines.append(f"     Impact: {opp.impact}, Effort: {opp.effort}, Score gain: +{opp.estimated_score_gain:.1f}")
        
        return "\n".join(lines)

