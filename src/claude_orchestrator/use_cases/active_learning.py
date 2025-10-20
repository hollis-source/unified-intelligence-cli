"""ActiveLearning - Identify weak domains and prioritize pattern collection.

Detects domains with low accuracy or insufficient patterns.
Prioritizes pattern collection for maximum improvement.

Clean Architecture: Use Case layer
SOLID: SRP - Single responsibility for active learning
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class WeakDomain:
    """A domain identified as weak (low accuracy or few patterns)."""
    domain: str
    accuracy: float  # 0-1
    pattern_count: int
    weakness_score: float  # Higher = weaker
    priority: int  # 1-5 (1=highest)
    recommendation: str


class ActiveLearning:
    """
    Identifies weak domains and prioritizes pattern collection.
    
    Weakness score formula:
    - weakness = (1 - accuracy) * (1 / max(1, pattern_count))
    - Higher score = higher priority for collection
    
    Thresholds:
    - Accuracy < 70% → weak
    - Pattern count < 20 → insufficient
    
    Usage:
        active_learning = ActiveLearning(db_store=db)
        weak_domains = active_learning.identify_weak_domains()
        priorities = active_learning.prioritize_collection(weak_domains)
    """
    
    # Thresholds
    MIN_ACCURACY = 0.70
    MIN_PATTERNS = 20
    
    def __init__(self, db_store: Optional[Any] = None):
        """
        Initialize active learning.
        
        Args:
            db_store: Database store for metrics and patterns
        """
        self.db_store = db_store
    
    def identify_weak_domains(
        self,
        min_accuracy: float = MIN_ACCURACY,
        min_patterns: int = MIN_PATTERNS,
    ) -> List[WeakDomain]:
        """
        Identify weak domains.
        
        Args:
            min_accuracy: Minimum acceptable accuracy
            min_patterns: Minimum acceptable pattern count
            
        Returns:
            List of WeakDomain objects sorted by weakness_score
        """
        # Get domain statistics
        domain_stats = self._get_domain_stats()
        
        weak_domains = []
        
        for domain, stats in domain_stats.items():
            accuracy = stats.get("accuracy", 0.0)
            pattern_count = stats.get("pattern_count", 0)
            
            # Check if weak
            is_weak = accuracy < min_accuracy or pattern_count < min_patterns
            
            if is_weak:
                # Calculate weakness score
                weakness_score = (1.0 - accuracy) * (1.0 / max(1, pattern_count))
                
                # Determine priority
                priority = self._calculate_priority(accuracy, pattern_count)
                
                # Generate recommendation
                recommendation = self._generate_recommendation(domain, accuracy, pattern_count)
                
                weak_domain = WeakDomain(
                    domain=domain,
                    accuracy=accuracy,
                    pattern_count=pattern_count,
                    weakness_score=weakness_score,
                    priority=priority,
                    recommendation=recommendation,
                )
                
                weak_domains.append(weak_domain)
        
        # Sort by weakness score (descending)
        weak_domains.sort(key=lambda d: d.weakness_score, reverse=True)
        
        logger.info(f"Identified {len(weak_domains)} weak domains")
        
        return weak_domains
    
    def prioritize_collection(
        self,
        weak_domains: List[WeakDomain],
        max_domains: int = 5,
    ) -> List[Tuple[str, int]]:
        """
        Prioritize domains for pattern collection.
        
        Args:
            weak_domains: List of WeakDomain objects
            max_domains: Maximum domains to prioritize
            
        Returns:
            List of (domain, target_pattern_count) tuples
        """
        priorities = []
        
        for domain in weak_domains[:max_domains]:
            # Calculate target pattern count
            target_count = max(self.MIN_PATTERNS, domain.pattern_count * 2)
            
            priorities.append((domain.domain, target_count))
        
        return priorities
    
    def auto_trigger_collection(
        self,
        weak_domains: List[WeakDomain],
        max_domains: int = 3,
    ) -> List[str]:
        """
        Auto-trigger pattern collection jobs for weak domains.
        
        Args:
            weak_domains: List of WeakDomain objects
            max_domains: Maximum domains to trigger
            
        Returns:
            List of triggered domain names
        """
        triggered = []
        
        for domain in weak_domains[:max_domains]:
            logger.info(f"Auto-triggering pattern collection for domain: {domain.domain}")
            
            # Trigger collection (placeholder - integrate with build_rag_patterns.py)
            success = self._trigger_collection_job(domain.domain)
            
            if success:
                triggered.append(domain.domain)
        
        return triggered
    
    def balance_pattern_distribution(
        self,
        domain_stats: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, int]:
        """
        Balance pattern distribution across domains.
        
        Ensures all domains have >= mean * 0.8 patterns.
        
        Args:
            domain_stats: Optional domain statistics
            
        Returns:
            Dict of {domain: target_count} for under-represented domains
        """
        if domain_stats is None:
            domain_stats = self._get_domain_stats()
        
        # Calculate mean pattern count
        pattern_counts = [stats.get("pattern_count", 0) for stats in domain_stats.values()]
        mean_count = sum(pattern_counts) / max(1, len(pattern_counts))
        
        threshold = mean_count * 0.8
        
        # Identify under-represented domains
        targets = {}
        
        for domain, stats in domain_stats.items():
            count = stats.get("pattern_count", 0)
            
            if count < threshold:
                target = int(mean_count)
                targets[domain] = target
                logger.info(f"Domain '{domain}' under-represented: {count} < {threshold:.1f}, target: {target}")
        
        return targets
    
    def _get_domain_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get domain statistics from DB or fallback."""
        if self.db_store:
            try:
                # Query DB for domain stats
                # Placeholder - implement actual DB query
                return self._query_domain_stats_from_db()
            except Exception as e:
                logger.error(f"Failed to query domain stats from DB: {e}")
        
        # Fallback: scan patterns directory
        return self._scan_patterns_directory()
    
    def _query_domain_stats_from_db(self) -> Dict[str, Dict[str, Any]]:
        """Query domain statistics from database."""
        # Placeholder - implement actual DB query
        # Example:
        # SELECT domain, AVG(success) as accuracy, COUNT(*) as pattern_count
        # FROM execution_log
        # GROUP BY domain
        
        logger.warning("DB query not implemented, using fallback")
        return {}
    
    def _scan_patterns_directory(self) -> Dict[str, Dict[str, Any]]:
        """Scan patterns directory for domain statistics."""
        patterns_dir = Path("patterns")
        
        if not patterns_dir.exists():
            logger.warning(f"Patterns directory not found: {patterns_dir}")
            return {}
        
        domain_stats = {}
        
        for pattern_file in patterns_dir.glob("*.json"):
            try:
                import json
                with open(pattern_file, 'r') as f:
                    patterns = json.load(f)
                
                for pattern in patterns:
                    domain = pattern.get("domain", "unknown")
                    
                    if domain not in domain_stats:
                        domain_stats[domain] = {
                            "pattern_count": 0,
                            "accuracy": 0.85,  # Default assumption
                        }
                    
                    domain_stats[domain]["pattern_count"] += 1
            
            except Exception as e:
                logger.error(f"Failed to scan pattern file {pattern_file}: {e}")
        
        return domain_stats
    
    def _calculate_priority(self, accuracy: float, pattern_count: int) -> int:
        """Calculate priority (1-5, 1=highest)."""
        # Critical: accuracy < 50% or patterns < 10
        if accuracy < 0.50 or pattern_count < 10:
            return 1
        
        # High: accuracy < 70% or patterns < 20
        if accuracy < 0.70 or pattern_count < 20:
            return 2
        
        # Medium: accuracy < 80% or patterns < 30
        if accuracy < 0.80 or pattern_count < 30:
            return 3
        
        # Low: accuracy < 90% or patterns < 50
        if accuracy < 0.90 or pattern_count < 50:
            return 4
        
        return 5
    
    def _generate_recommendation(self, domain: str, accuracy: float, pattern_count: int) -> str:
        """Generate recommendation for weak domain."""
        if accuracy < 0.50:
            return f"CRITICAL: Accuracy {accuracy:.1%} is very low. Collect 50+ high-quality patterns."
        
        if pattern_count < 10:
            return f"CRITICAL: Only {pattern_count} patterns. Collect at least 20 patterns."
        
        if accuracy < 0.70:
            return f"Accuracy {accuracy:.1%} is below target. Collect 20+ patterns and review quality."
        
        if pattern_count < 20:
            return f"Only {pattern_count} patterns. Collect at least {20 - pattern_count} more."
        
        return f"Accuracy {accuracy:.1%} or pattern count {pattern_count} below optimal. Collect more patterns."
    
    def _trigger_collection_job(self, domain: str) -> bool:
        """Trigger pattern collection job for domain."""
        # Placeholder - integrate with build_rag_patterns.py or CI
        logger.info(f"Would trigger collection job for domain: {domain}")
        
        # Example: subprocess.run(["python", "scripts/build_rag_patterns.py", "--domain", domain])
        
        return True

