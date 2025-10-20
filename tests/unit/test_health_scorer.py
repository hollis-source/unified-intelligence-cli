import pytest

from src.analysis.health_scorer import HealthScorer, HealthScore
from src.analysis.git_analyzer import GitAnalysis, CommitPattern, FileChurn
from src.analysis.coverage_analyzer import CoverageAnalysis, ModuleCoverage
from src.analysis.metrics_analyzer import MetricsAnalysis, MetricTrend


@pytest.fixture
def sample_git_analysis():
    """Create sample git analysis."""
    return GitAnalysis(
        total_commits=100,
        commit_patterns={
            'bug_fix': CommitPattern('bug_fix', 20, ['fix: bug 1', 'fix: bug 2']),
            'feature': CommitPattern('feature', 50, ['feat: new feature']),
            'refactor': CommitPattern('refactor', 30, ['refactor: cleanup'])
        },
        high_churn_files=[
            FileChurn('src/routing/router.py', 15, 500, '2025-10-19'),
            FileChurn('src/execution/executor.py', 12, 400, '2025-10-18')
        ],
        issue_themes=[('routing', 10), ('execution', 8)],
        analysis_period_days=30,
        timestamp='2025-10-19T12:00:00Z'
    )


@pytest.fixture
def sample_coverage_analysis():
    """Create sample coverage analysis."""
    return CoverageAnalysis(
        overall_coverage=0.75,
        low_coverage_modules=[
            ModuleCoverage('src/new_module.py', 0.45, 0.50, 45, 100, 10, 20),
            ModuleCoverage('src/old_module.py', 0.60, 0.65, 60, 100, 13, 20)
        ],
        uncovered_files=['src/unused.py'],
        critical_uncovered=['src/routing/critical.py'],
        priority_list=[
            ('src/routing/critical.py', 0.0, 'Critical path, no tests'),
            ('src/new_module.py', 0.45, 'Low coverage (45%)')
        ],
        total_modules=20,
        timestamp='2025-10-19T12:00:00Z'
    )


@pytest.fixture
def sample_metrics_analysis():
    """Create sample metrics analysis."""
    return MetricsAnalysis(
        degrading_metrics=[
            MetricTrend('routing_accuracy', 0.72, 0.78, -7.7, 'degrading', 'warning', 'Review pattern quality')
        ],
        improving_metrics=[
            MetricTrend('p95_latency_ms', 450, 550, -18.2, 'improving', 'info', 'Latency improved')
        ],
        anomalies=[],
        correlations={},
        recommendations=['Review pattern quality and collect more training data'],
        analysis_period_days=30,
        timestamp='2025-10-19T12:00:00Z'
    )


def test_health_scorer_initialization():
    """Test HealthScorer initialization."""
    scorer = HealthScorer()
    assert scorer is not None
    assert scorer.WEIGHTS['coverage'] == 0.30


def test_compute_health_with_all_data(sample_git_analysis, sample_coverage_analysis, sample_metrics_analysis):
    """Test health score computation with all data."""
    scorer = HealthScorer()
    
    health = scorer.compute_health(
        git_analysis=sample_git_analysis,
        coverage_analysis=sample_coverage_analysis,
        metrics_analysis=sample_metrics_analysis,
        test_pass_rate=0.95
    )
    
    assert isinstance(health, HealthScore)
    assert 0 <= health.overall_score <= 100
    assert health.grade in ['A', 'B', 'C', 'D', 'F']
    assert len(health.factors) == 5
    assert len(health.top_opportunities) > 0


def test_compute_health_with_no_data():
    """Test health score computation with no data."""
    scorer = HealthScorer()
    
    health = scorer.compute_health()
    
    assert isinstance(health, HealthScore)
    assert 0 <= health.overall_score <= 100
    assert len(health.factors) == 5


def test_coverage_factor_scoring(sample_coverage_analysis):
    """Test coverage factor scoring."""
    scorer = HealthScorer()
    
    factor = scorer._compute_coverage_factor(sample_coverage_analysis)
    
    assert factor.name == "Coverage"
    assert 0 <= factor.score <= 100
    assert factor.weight == 0.30
    assert factor.status in ['excellent', 'good', 'fair', 'poor', 'critical', 'unknown']


def test_metrics_factor_scoring(sample_metrics_analysis):
    """Test metrics factor scoring."""
    scorer = HealthScorer()
    
    factor = scorer._compute_metrics_factor(sample_metrics_analysis)
    
    assert factor.name == "Metrics"
    assert 0 <= factor.score <= 100
    assert factor.weight == 0.10


def test_improvement_opportunities_identified(sample_git_analysis, sample_coverage_analysis, sample_metrics_analysis):
    """Test that improvement opportunities are identified."""
    scorer = HealthScorer()
    
    health = scorer.compute_health(
        git_analysis=sample_git_analysis,
        coverage_analysis=sample_coverage_analysis,
        metrics_analysis=sample_metrics_analysis
    )
    
    assert len(health.top_opportunities) > 0
    
    # Check opportunity structure
    opp = health.top_opportunities[0]
    assert opp.priority >= 1
    assert opp.category in ['coverage', 'metrics', 'code_quality', 'technical_debt']
    assert opp.impact in ['high', 'medium', 'low']
    assert opp.effort in ['high', 'medium', 'low']
    assert opp.estimated_score_gain > 0


def test_score_to_grade():
    """Test score to grade conversion."""
    scorer = HealthScorer()
    
    assert scorer._score_to_grade(95) == 'A'
    assert scorer._score_to_grade(85) == 'B'
    assert scorer._score_to_grade(75) == 'C'
    assert scorer._score_to_grade(65) == 'D'
    assert scorer._score_to_grade(55) == 'F'


def test_score_to_status():
    """Test score to status conversion."""
    scorer = HealthScorer()
    
    assert scorer._score_to_status(95) == 'excellent'
    assert scorer._score_to_status(80) == 'good'
    assert scorer._score_to_status(65) == 'fair'
    assert scorer._score_to_status(50) == 'poor'
    assert scorer._score_to_status(30) == 'critical'

