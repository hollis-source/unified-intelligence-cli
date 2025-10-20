"""A/B testing framework for routing strategies.

This module implements A/B testing to compare RAG routing vs baseline
routing with statistical significance testing.
"""

import asyncio
import random
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import statistics
import math


class ABTest:
    """A/B testing framework for routing strategies."""
    
    def __init__(
        self,
        db_store,
        test_name: str = "rag_vs_baseline",
        control_strategy: str = "base",
        treatment_strategy: str = "rag",
        split_ratio: float = 0.5
    ):
        """Initialize A/B test.
        
        Args:
            db_store: SurrealDBStore instance
            test_name: Name of the A/B test
            control_strategy: Control group strategy (baseline)
            treatment_strategy: Treatment group strategy (RAG)
            split_ratio: Ratio of traffic to treatment (0.0-1.0)
        """
        self.db_store = db_store
        self.test_name = test_name
        self.control_strategy = control_strategy
        self.treatment_strategy = treatment_strategy
        self.split_ratio = split_ratio
        
    def assign_to_group(self, task_id: str) -> str:
        """Assign a task to control or treatment group.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Strategy name (control or treatment)
        """
        # Use hash of task_id for consistent assignment
        hash_value = hash(task_id)
        random.seed(hash_value)
        
        if random.random() < self.split_ratio:
            return self.treatment_strategy
        else:
            return self.control_strategy
    
    async def get_test_results(self) -> Dict[str, Any]:
        """Get results for both groups.
        
        Returns:
            Dictionary with test results
        """
        # Get routing decisions for both strategies
        sql = """
        SELECT routing_strategy, success, confidence 
        FROM routing_decisions 
        WHERE success IS NOT NULL;
        """
        
        result = await self.db_store.query(sql)
        
        control_results = []
        treatment_results = []
        
        if result and isinstance(result, list):
            for item in result:
                strategy = item.get("routing_strategy")
                success = item.get("success")

                # Skip if success is None
                if success is None:
                    continue

                if strategy == self.control_strategy:
                    control_results.append(success)
                elif strategy == self.treatment_strategy:
                    treatment_results.append(success)
        
        return {
            "control": {
                "strategy": self.control_strategy,
                "total": len(control_results),
                "successes": sum(control_results),
                "failures": len(control_results) - sum(control_results),
                "success_rate": (sum(control_results) / len(control_results) * 100) if control_results else 0.0
            },
            "treatment": {
                "strategy": self.treatment_strategy,
                "total": len(treatment_results),
                "successes": sum(treatment_results),
                "failures": len(treatment_results) - sum(treatment_results),
                "success_rate": (sum(treatment_results) / len(treatment_results) * 100) if treatment_results else 0.0
            }
        }
    
    def calculate_statistical_significance(
        self,
        control_successes: int,
        control_total: int,
        treatment_successes: int,
        treatment_total: int
    ) -> Dict[str, Any]:
        """Calculate statistical significance using z-test for proportions.
        
        Args:
            control_successes: Number of successes in control group
            control_total: Total samples in control group
            treatment_successes: Number of successes in treatment group
            treatment_total: Total samples in treatment group
            
        Returns:
            Dictionary with statistical test results
        """
        if control_total == 0 or treatment_total == 0:
            return {
                "significant": False,
                "reason": "insufficient_data",
                "message": "Need data in both groups"
            }
        
        # Calculate proportions
        p1 = control_successes / control_total
        p2 = treatment_successes / treatment_total
        
        # Pooled proportion
        p_pool = (control_successes + treatment_successes) / (control_total + treatment_total)
        
        # Standard error
        se = math.sqrt(p_pool * (1 - p_pool) * (1/control_total + 1/treatment_total))
        
        if se == 0:
            return {
                "significant": False,
                "reason": "zero_variance",
                "message": "No variance in results"
            }
        
        # Z-score
        z_score = (p2 - p1) / se
        
        # P-value (two-tailed test, approximate)
        # For |z| > 1.96, p < 0.05 (95% confidence)
        # For |z| > 2.58, p < 0.01 (99% confidence)
        
        abs_z = abs(z_score)
        
        if abs_z > 2.58:
            p_value = 0.01
            confidence = 99
        elif abs_z > 1.96:
            p_value = 0.05
            confidence = 95
        elif abs_z > 1.645:
            p_value = 0.10
            confidence = 90
        else:
            p_value = 0.20
            confidence = 80
        
        significant = abs_z > 1.96  # 95% confidence threshold
        
        return {
            "significant": significant,
            "z_score": z_score,
            "p_value": p_value,
            "confidence": confidence,
            "control_rate": p1 * 100,
            "treatment_rate": p2 * 100,
            "absolute_difference": (p2 - p1) * 100,
            "relative_improvement": ((p2 - p1) / p1 * 100) if p1 > 0 else 0,
            "message": (
                f"Treatment is {'better' if z_score > 0 else 'worse'} than control "
                f"with {confidence}% confidence"
                if significant
                else "No significant difference detected"
            )
        }
    
    async def run_ab_test(self) -> Dict[str, Any]:
        """Run complete A/B test analysis.
        
        Returns:
            Dictionary with complete test results
        """
        # Get results for both groups
        results = await self.get_test_results()
        
        control = results["control"]
        treatment = results["treatment"]
        
        # Calculate statistical significance
        stats = self.calculate_statistical_significance(
            control_successes=control["successes"],
            control_total=control["total"],
            treatment_successes=treatment["successes"],
            treatment_total=treatment["total"]
        )
        
        # Determine recommendation
        if stats.get("significant"):
            if stats["z_score"] > 0:
                recommendation = f"Deploy {self.treatment_strategy} - significantly better than {self.control_strategy}"
            else:
                recommendation = f"Keep {self.control_strategy} - significantly better than {self.treatment_strategy}"
        else:
            recommendation = "Continue testing - no significant difference yet"
        
        return {
            "test_name": self.test_name,
            "control": control,
            "treatment": treatment,
            "statistics": stats,
            "recommendation": recommendation,
            "sample_size_adequate": control["total"] >= 30 and treatment["total"] >= 30
        }
    
    async def get_test_report(self) -> str:
        """Generate human-readable test report.
        
        Returns:
            Formatted test report string
        """
        results = await self.run_ab_test()
        
        report = []
        report.append("=" * 80)
        report.append(f"A/B TEST REPORT: {results['test_name']}")
        report.append("=" * 80)
        report.append("")
        
        # Control group
        control = results["control"]
        report.append(f"CONTROL GROUP ({control['strategy']}):")
        report.append(f"  • Total samples: {control['total']}")
        report.append(f"  • Successes: {control['successes']}")
        report.append(f"  • Failures: {control['failures']}")
        report.append(f"  • Success rate: {control['success_rate']:.1f}%")
        report.append("")
        
        # Treatment group
        treatment = results["treatment"]
        report.append(f"TREATMENT GROUP ({treatment['strategy']}):")
        report.append(f"  • Total samples: {treatment['total']}")
        report.append(f"  • Successes: {treatment['successes']}")
        report.append(f"  • Failures: {treatment['failures']}")
        report.append(f"  • Success rate: {treatment['success_rate']:.1f}%")
        report.append("")
        
        # Statistics
        stats = results["statistics"]
        if stats.get("significant") is not None:
            report.append("STATISTICAL ANALYSIS:")
            report.append(f"  • Significant: {stats['significant']}")
            if "z_score" in stats:
                report.append(f"  • Z-score: {stats['z_score']:.2f}")
                report.append(f"  • P-value: {stats['p_value']:.3f}")
                report.append(f"  • Confidence: {stats['confidence']}%")
                report.append(f"  • Absolute difference: {stats['absolute_difference']:+.1f}%")
                report.append(f"  • Relative improvement: {stats['relative_improvement']:+.1f}%")
            report.append(f"  • {stats['message']}")
        else:
            report.append(f"STATISTICAL ANALYSIS: {stats.get('message', 'N/A')}")
        report.append("")
        
        # Recommendation
        report.append("RECOMMENDATION:")
        report.append(f"  • {results['recommendation']}")
        report.append("")
        
        # Sample size
        if not results["sample_size_adequate"]:
            report.append("⚠️  WARNING: Sample size may be too small (< 30 per group)")
            report.append("   Continue testing to reach statistical power")
            report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)

