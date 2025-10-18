"""Drift detector for pattern distribution monitoring.

This module detects when task patterns change significantly (concept drift)
and triggers re-embedding when needed.
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
import statistics


class DriftDetector:
    """Detect concept drift in task patterns."""
    
    def __init__(
        self,
        db_store,
        drift_threshold: float = 0.3,
        window_size: int = 50,
        min_samples: int = 20
    ):
        """Initialize drift detector.
        
        Args:
            db_store: SurrealDBStore instance
            drift_threshold: Threshold for detecting significant drift (0.0-1.0)
            window_size: Number of recent tasks to analyze
            min_samples: Minimum samples needed for drift detection
        """
        self.db_store = db_store
        self.drift_threshold = drift_threshold
        self.window_size = window_size
        self.min_samples = min_samples
        self.baseline_distribution = None
        
    async def get_task_distribution(self, limit: int = None) -> Dict[str, int]:
        """Get distribution of tasks by domain.
        
        Args:
            limit: Maximum number of recent tasks to analyze
            
        Returns:
            Dictionary mapping domain to task count
        """
        # Get recent execution logs
        sql = "SELECT task_domain FROM execution_log ORDER BY id DESC"
        if limit:
            sql += f" LIMIT {limit};"
        else:
            sql += ";"
        
        result = await self.db_store.query(sql)
        
        distribution = defaultdict(int)
        
        if result and isinstance(result, list):
            for item in result:
                domain = item.get("task_domain", "unknown")
                distribution[domain] += 1
        
        return dict(distribution)
    
    async def calculate_distribution_similarity(
        self,
        dist1: Dict[str, int],
        dist2: Dict[str, int]
    ) -> float:
        """Calculate similarity between two distributions using cosine similarity.
        
        Args:
            dist1: First distribution
            dist2: Second distribution
            
        Returns:
            Similarity score (0.0-1.0)
        """
        # Get all domains
        all_domains = set(dist1.keys()) | set(dist2.keys())
        
        if not all_domains:
            return 1.0
        
        # Convert to vectors
        vec1 = [dist1.get(domain, 0) for domain in all_domains]
        vec2 = [dist2.get(domain, 0) for domain in all_domains]
        
        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        similarity = dot_product / (magnitude1 * magnitude2)
        return max(0.0, min(1.0, similarity))
    
    async def detect_drift(self) -> Dict[str, Any]:
        """Detect concept drift in task patterns.
        
        Returns:
            Dictionary with drift detection results
        """
        # Get current distribution (recent window)
        current_dist = await self.get_task_distribution(limit=self.window_size)
        
        # Get baseline distribution (all historical data)
        baseline_dist = await self.get_task_distribution()
        
        # Check if we have enough data
        total_current = sum(current_dist.values())
        total_baseline = sum(baseline_dist.values())
        
        if total_current < self.min_samples:
            return {
                "drift_detected": False,
                "reason": "insufficient_data",
                "current_samples": total_current,
                "min_samples": self.min_samples,
                "message": f"Need at least {self.min_samples} samples for drift detection"
            }
        
        # Calculate similarity
        similarity = await self.calculate_distribution_similarity(
            current_dist,
            baseline_dist
        )
        
        # Detect drift (low similarity = high drift)
        drift_score = 1.0 - similarity
        drift_detected = drift_score > self.drift_threshold
        
        # Analyze changes
        changes = []
        all_domains = set(current_dist.keys()) | set(baseline_dist.keys())
        
        for domain in all_domains:
            current_count = current_dist.get(domain, 0)
            baseline_count = baseline_dist.get(domain, 0)
            
            current_pct = (current_count / total_current * 100) if total_current > 0 else 0
            baseline_pct = (baseline_count / total_baseline * 100) if total_baseline > 0 else 0
            
            change_pct = current_pct - baseline_pct
            
            if abs(change_pct) > 10:  # Significant change
                changes.append({
                    "domain": domain,
                    "current_percentage": current_pct,
                    "baseline_percentage": baseline_pct,
                    "change": change_pct
                })
        
        return {
            "drift_detected": drift_detected,
            "drift_score": drift_score,
            "similarity": similarity,
            "threshold": self.drift_threshold,
            "current_distribution": current_dist,
            "baseline_distribution": baseline_dist,
            "significant_changes": changes,
            "recommendation": "Re-embed patterns" if drift_detected else "No action needed",
            "message": f"Drift score: {drift_score:.2f} (threshold: {self.drift_threshold})"
        }
    
    async def monitor_domain_shifts(self) -> Dict[str, Any]:
        """Monitor shifts in domain distribution over time.
        
        Returns:
            Dictionary with domain shift analysis
        """
        # Get recent distribution
        recent_dist = await self.get_task_distribution(limit=self.window_size)
        
        # Get older distribution (previous window)
        sql = f"""
        SELECT task_domain FROM execution_log 
        ORDER BY id DESC 
        LIMIT {self.window_size} 
        OFFSET {self.window_size};
        """
        
        result = await self.db_store.query(sql)
        
        older_dist = defaultdict(int)
        if result and isinstance(result, list):
            for item in result:
                domain = item.get("task_domain", "unknown")
                older_dist[domain] += 1
        
        older_dist = dict(older_dist)
        
        # Calculate shift
        total_recent = sum(recent_dist.values())
        total_older = sum(older_dist.values())
        
        if total_recent < self.min_samples or total_older < self.min_samples:
            return {
                "shift_detected": False,
                "reason": "insufficient_data",
                "message": "Need more historical data for shift detection"
            }
        
        # Analyze shifts
        shifts = []
        all_domains = set(recent_dist.keys()) | set(older_dist.keys())
        
        for domain in all_domains:
            recent_count = recent_dist.get(domain, 0)
            older_count = older_dist.get(domain, 0)
            
            recent_pct = (recent_count / total_recent * 100) if total_recent > 0 else 0
            older_pct = (older_count / total_older * 100) if total_older > 0 else 0
            
            shift_pct = recent_pct - older_pct
            
            if abs(shift_pct) > 15:  # Significant shift
                shifts.append({
                    "domain": domain,
                    "recent_percentage": recent_pct,
                    "older_percentage": older_pct,
                    "shift": shift_pct,
                    "trend": "increasing" if shift_pct > 0 else "decreasing"
                })
        
        shift_detected = len(shifts) > 0
        
        return {
            "shift_detected": shift_detected,
            "shifts": shifts,
            "recent_distribution": recent_dist,
            "older_distribution": older_dist,
            "message": f"Found {len(shifts)} significant domain shifts"
        }
    
    async def check_pattern_staleness(self, max_age_days: int = 30) -> Dict[str, Any]:
        """Check if patterns are becoming stale.
        
        Args:
            max_age_days: Maximum age in days before patterns are considered stale
            
        Returns:
            Dictionary with staleness analysis
        """
        # Get pattern count and age
        sql = "SELECT count() as total FROM execution_log GROUP ALL;"
        result = await self.db_store.query(sql)
        
        total_patterns = 0
        if result and isinstance(result, list) and len(result) > 0:
            if isinstance(result[0], dict) and "total" in result[0]:
                total_patterns = result[0]["total"]
        
        # Note: SurrealDB doesn't have built-in timestamp by default
        # This is a simplified check
        
        return {
            "total_patterns": total_patterns,
            "staleness_check": "simplified",
            "recommendation": "Consider periodic re-embedding" if total_patterns > 100 else "Pattern count acceptable",
            "message": f"Total patterns: {total_patterns}"
        }
    
    async def get_drift_report(self) -> Dict[str, Any]:
        """Generate comprehensive drift detection report.
        
        Returns:
            Dictionary with complete drift analysis
        """
        # Run all drift checks
        drift_result = await self.detect_drift()
        shift_result = await self.monitor_domain_shifts()
        staleness_result = await self.check_pattern_staleness()
        
        # Determine overall recommendation
        needs_reembedding = (
            drift_result.get("drift_detected", False) or
            shift_result.get("shift_detected", False)
        )
        
        return {
            "drift_detection": drift_result,
            "domain_shifts": shift_result,
            "pattern_staleness": staleness_result,
            "needs_reembedding": needs_reembedding,
            "overall_recommendation": (
                "Re-embed patterns to adapt to distribution changes"
                if needs_reembedding
                else "Pattern distribution is stable"
            )
        }

