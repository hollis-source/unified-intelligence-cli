"""
Pattern Quality Management for RAG Routing

Implements deduplication, scoring, and filtering of execution patterns
to improve RAG routing precision.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PatternScore:
    """Quality score for an execution pattern."""
    pattern_id: str
    success_rate: float  # 0.0-1.0
    latency_score: float  # 0.0-1.0 (lower latency = higher score)
    domain_match_score: float  # 0.0-1.0
    recency_score: float  # 0.0-1.0 (more recent = higher score)
    overall_score: float  # weighted combination
    
    @staticmethod
    def compute(
        pattern: Dict[str, Any],
        target_domain: Optional[str] = None,
        max_age_days: float = 30.0
    ) -> 'PatternScore':
        """
        Compute quality score for a pattern.
        
        Args:
            pattern: Pattern dict with success, latency_seconds, task_domain, timestamp
            target_domain: Target domain for domain match scoring
            max_age_days: Maximum age for recency scoring
            
        Returns:
            PatternScore
        """
        # Success rate (binary for single pattern, could aggregate if multiple executions)
        success_rate = 1.0 if pattern.get('success', False) else 0.0
        
        # Latency score (normalize: assume 60s is baseline, <10s is excellent)
        latency = float(pattern.get('latency_seconds', 60.0))
        latency_score = max(0.0, min(1.0, (60.0 - latency) / 50.0))
        
        # Domain match score
        pattern_domain = pattern.get('task_domain', '')
        if target_domain and pattern_domain:
            domain_match_score = 1.0 if pattern_domain == target_domain else 0.5
        else:
            domain_match_score = 0.5  # neutral if no domain info
        
        # Recency score (exponential decay)
        # Note: timestamp parsing would be needed in production
        # For now, use a placeholder
        recency_score = 0.8  # placeholder
        
        # Weighted combination (success 40%, latency 30%, domain 20%, recency 10%)
        overall_score = (
            success_rate * 0.4 +
            latency_score * 0.3 +
            domain_match_score * 0.2 +
            recency_score * 0.1
        )
        
        return PatternScore(
            pattern_id=pattern.get('execution_id', 'unknown'),
            success_rate=success_rate,
            latency_score=latency_score,
            domain_match_score=domain_match_score,
            recency_score=recency_score,
            overall_score=overall_score
        )


class PatternQualityManager:
    """
    Manages pattern quality: deduplication, scoring, and filtering.
    
    Features:
    - Detect near-duplicate patterns via embedding similarity
    - Score patterns by success, latency, domain match, recency
    - Filter low-quality patterns
    - Select top-K high-signal patterns
    """
    
    def __init__(
        self,
        dedup_threshold: float = 0.95,
        min_confidence: float = 0.5,
        top_k: int = 10
    ):
        """
        Initialize pattern quality manager.
        
        Args:
            dedup_threshold: Embedding similarity threshold for deduplication (0.95)
            min_confidence: Minimum overall score to keep pattern (0.5)
            top_k: Number of top patterns to return (10)
        """
        self.dedup_threshold = dedup_threshold
        self.min_confidence = min_confidence
        self.top_k = top_k
    
    def deduplicate(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove near-duplicate patterns based on embedding similarity.
        
        Args:
            patterns: List of patterns with 'embedding' field
            
        Returns:
            Deduplicated list of patterns
        """
        if not patterns:
            return []
        
        # Extract embeddings
        embeddings = []
        for p in patterns:
            emb = p.get('embedding')
            if emb is None:
                continue
            if isinstance(emb, list):
                embeddings.append(np.array(emb))
            elif isinstance(emb, np.ndarray):
                embeddings.append(emb)
            else:
                embeddings.append(None)
        
        # Track which patterns to keep
        keep_indices = []
        seen_embeddings = []
        
        for i, emb in enumerate(embeddings):
            if emb is None:
                keep_indices.append(i)  # keep patterns without embeddings
                continue
            
            # Check similarity with already-kept patterns
            is_duplicate = False
            for seen_emb in seen_embeddings:
                similarity = self._cosine_similarity(emb, seen_emb)
                if similarity >= self.dedup_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                keep_indices.append(i)
                seen_embeddings.append(emb)
        
        deduplicated = [patterns[i] for i in keep_indices]
        
        if len(deduplicated) < len(patterns):
            logger.info(f"Deduplicated {len(patterns)} patterns to {len(deduplicated)}")
        
        return deduplicated
    
    def score_patterns(
        self,
        patterns: List[Dict[str, Any]],
        target_domain: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Score patterns and add 'quality_score' field.
        
        Args:
            patterns: List of patterns
            target_domain: Target domain for domain match scoring
            
        Returns:
            Patterns with added 'quality_score' field
        """
        scored = []
        for pattern in patterns:
            score = PatternScore.compute(pattern, target_domain=target_domain)
            pattern_copy = pattern.copy()
            pattern_copy['quality_score'] = score.overall_score
            pattern_copy['score_breakdown'] = {
                'success_rate': score.success_rate,
                'latency_score': score.latency_score,
                'domain_match_score': score.domain_match_score,
                'recency_score': score.recency_score
            }
            scored.append(pattern_copy)
        
        return scored
    
    def filter_low_quality(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out patterns below minimum confidence threshold.
        
        Args:
            patterns: List of patterns with 'quality_score' field
            
        Returns:
            Filtered patterns
        """
        filtered = [p for p in patterns if p.get('quality_score', 0.0) >= self.min_confidence]
        
        if len(filtered) < len(patterns):
            logger.info(f"Filtered {len(patterns)} patterns to {len(filtered)} (min_confidence={self.min_confidence})")
        
        return filtered
    
    def select_top_k(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Select top-K patterns by quality score.
        
        Args:
            patterns: List of patterns with 'quality_score' field
            
        Returns:
            Top-K patterns sorted by score (descending)
        """
        sorted_patterns = sorted(
            patterns,
            key=lambda p: p.get('quality_score', 0.0),
            reverse=True
        )
        
        return sorted_patterns[:self.top_k]
    
    def process(
        self,
        patterns: List[Dict[str, Any]],
        target_domain: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Full pipeline: deduplicate → score → filter → select top-K.
        
        Args:
            patterns: Raw patterns from retrieval
            target_domain: Target domain for scoring
            
        Returns:
            High-quality, deduplicated, top-K patterns
        """
        if not patterns:
            return []
        
        # Step 1: Deduplicate
        deduped = self.deduplicate(patterns)
        
        # Step 2: Score
        scored = self.score_patterns(deduped, target_domain=target_domain)
        
        # Step 3: Filter low quality
        filtered = self.filter_low_quality(scored)
        
        # Step 4: Select top-K
        top_k = self.select_top_k(filtered)
        
        logger.info(
            f"Pattern quality pipeline: {len(patterns)} → "
            f"dedup:{len(deduped)} → score:{len(scored)} → "
            f"filter:{len(filtered)} → top-K:{len(top_k)}"
        )
        
        return top_k
    
    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot / (norm_a * norm_b)
    
    @staticmethod
    def canonicalize_description(description: str) -> str:
        """
        Canonicalize task description for better deduplication.
        
        Args:
            description: Raw task description
            
        Returns:
            Canonicalized description (lowercase, stopwords removed)
        """
        # Simple canonicalization: lowercase and basic cleanup
        # In production, could use NLP stopword removal
        canonical = description.lower().strip()
        
        # Remove common stopwords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        words = canonical.split()
        filtered = [w for w in words if w not in stopwords]
        
        return ' '.join(filtered)

