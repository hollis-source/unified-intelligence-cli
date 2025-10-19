import numpy as np

from src.routing.pattern_quality import PatternQualityManager, PatternScore


def test_pattern_score_computation():
    pattern = {
        'execution_id': 'exec_123',
        'success': True,
        'latency_seconds': 15.0,
        'task_domain': 'backend'
    }
    
    score = PatternScore.compute(pattern, target_domain='backend')
    
    assert score.success_rate == 1.0
    assert score.latency_score > 0.5  # 15s is better than 60s baseline
    assert score.domain_match_score == 1.0  # exact match
    assert 0.0 <= score.overall_score <= 1.0


def test_deduplication():
    manager = PatternQualityManager(dedup_threshold=0.95)
    
    # Create patterns with similar embeddings
    emb1 = np.array([1.0, 0.0, 0.0])
    emb2 = np.array([0.99, 0.01, 0.0])  # very similar
    emb3 = np.array([0.0, 1.0, 0.0])  # different
    
    patterns = [
        {'id': 'p1', 'embedding': emb1.tolist()},
        {'id': 'p2', 'embedding': emb2.tolist()},
        {'id': 'p3', 'embedding': emb3.tolist()},
    ]
    
    deduped = manager.deduplicate(patterns)
    
    # Should keep p1 and p3, drop p2 (duplicate of p1)
    assert len(deduped) == 2
    ids = [p['id'] for p in deduped]
    assert 'p1' in ids
    assert 'p3' in ids


def test_score_and_filter():
    manager = PatternQualityManager(min_confidence=0.5)
    
    patterns = [
        {'id': 'p1', 'success': True, 'latency_seconds': 10.0, 'task_domain': 'backend'},
        {'id': 'p2', 'success': False, 'latency_seconds': 80.0, 'task_domain': 'frontend'},
        {'id': 'p3', 'success': True, 'latency_seconds': 20.0, 'task_domain': 'backend'},
    ]
    
    scored = manager.score_patterns(patterns, target_domain='backend')
    
    assert all('quality_score' in p for p in scored)
    assert scored[0]['quality_score'] > scored[1]['quality_score']  # p1 better than p2
    
    filtered = manager.filter_low_quality(scored)
    
    # p2 should be filtered out (failed + high latency)
    assert len(filtered) <= len(scored)


def test_top_k_selection():
    manager = PatternQualityManager(top_k=2)
    
    patterns = [
        {'id': 'p1', 'quality_score': 0.9},
        {'id': 'p2', 'quality_score': 0.7},
        {'id': 'p3', 'quality_score': 0.8},
        {'id': 'p4', 'quality_score': 0.6},
    ]
    
    top_k = manager.select_top_k(patterns)
    
    assert len(top_k) == 2
    assert top_k[0]['id'] == 'p1'
    assert top_k[1]['id'] == 'p3'


def test_full_pipeline():
    manager = PatternQualityManager(dedup_threshold=0.95, min_confidence=0.4, top_k=2)
    
    emb1 = np.array([1.0, 0.0, 0.0])
    emb2 = np.array([0.99, 0.01, 0.0])  # duplicate
    emb3 = np.array([0.0, 1.0, 0.0])
    
    patterns = [
        {'id': 'p1', 'embedding': emb1.tolist(), 'success': True, 'latency_seconds': 10.0, 'task_domain': 'backend'},
        {'id': 'p2', 'embedding': emb2.tolist(), 'success': True, 'latency_seconds': 12.0, 'task_domain': 'backend'},
        {'id': 'p3', 'embedding': emb3.tolist(), 'success': False, 'latency_seconds': 90.0, 'task_domain': 'frontend'},
    ]
    
    result = manager.process(patterns, target_domain='backend')
    
    # Should deduplicate p1/p2, filter p3 (low quality), return top-K
    assert len(result) <= 2
    assert all('quality_score' in p for p in result)

