"""Weight optimizer for adaptive routing.

This module analyzes historical routing decisions and optimizes weights
to improve routing accuracy over time.
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import statistics


class WeightOptimizer:
    """Optimize routing weights based on historical success rates."""
    
    def __init__(self, db_store, min_samples: int = 10):
        """Initialize weight optimizer.
        
        Args:
            db_store: SurrealDBStore instance for accessing routing decisions
            min_samples: Minimum number of samples required for optimization
        """
        self.db_store = db_store
        self.min_samples = min_samples
        self.weights = {}  # domain -> weight multiplier
        
    async def analyze_routing_performance(self) -> Dict[str, Any]:
        """Analyze routing performance by domain and agent.
        
        Returns:
            Dictionary with performance metrics by domain and agent
        """
        # Get all routing decisions
        decisions = await self.db_store.get_recent_routing_decisions(limit=1000)
        
        if not decisions:
            return {
                "total_decisions": 0,
                "by_domain": {},
                "by_agent": {},
                "by_strategy": {}
            }
        
        # Analyze by domain
        domain_stats = defaultdict(lambda: {"total": 0, "success": 0, "failure": 0})
        agent_stats = defaultdict(lambda: {"total": 0, "success": 0, "failure": 0})
        strategy_stats = defaultdict(lambda: {"total": 0, "success": 0, "failure": 0})
        
        for decision in decisions:
            domain = decision.get("task_domain", "unknown")
            agent = decision.get("selected_agent", "unknown")
            strategy = decision.get("routing_strategy", "unknown")
            success = decision.get("success")
            
            # Skip if success is None (not yet completed)
            if success is None:
                continue
            
            # Update domain stats
            domain_stats[domain]["total"] += 1
            if success:
                domain_stats[domain]["success"] += 1
            else:
                domain_stats[domain]["failure"] += 1
            
            # Update agent stats
            agent_stats[agent]["total"] += 1
            if success:
                agent_stats[agent]["success"] += 1
            else:
                agent_stats[agent]["failure"] += 1
            
            # Update strategy stats
            strategy_stats[strategy]["total"] += 1
            if success:
                strategy_stats[strategy]["success"] += 1
            else:
                strategy_stats[strategy]["failure"] += 1
        
        # Calculate success rates
        for stats in [domain_stats, agent_stats, strategy_stats]:
            for key, data in stats.items():
                if data["total"] > 0:
                    data["success_rate"] = (data["success"] / data["total"]) * 100
                else:
                    data["success_rate"] = 0.0
        
        return {
            "total_decisions": len([d for d in decisions if d.get("success") is not None]),
            "by_domain": dict(domain_stats),
            "by_agent": dict(agent_stats),
            "by_strategy": dict(strategy_stats)
        }
    
    async def optimize_domain_weights(self) -> Dict[str, float]:
        """Optimize domain weights based on success rates.
        
        Returns:
            Dictionary mapping domain to weight multiplier
        """
        performance = await self.analyze_routing_performance()
        
        if performance["total_decisions"] < self.min_samples:
            return {}
        
        domain_stats = performance["by_domain"]
        weights = {}
        
        # Calculate average success rate
        success_rates = [
            stats["success_rate"] 
            for stats in domain_stats.values() 
            if stats["total"] >= self.min_samples
        ]
        
        if not success_rates:
            return {}
        
        avg_success_rate = statistics.mean(success_rates)
        
        # Calculate weight multipliers
        # Domains with higher success rates get higher weights
        for domain, stats in domain_stats.items():
            if stats["total"] < self.min_samples:
                continue
            
            success_rate = stats["success_rate"]
            
            # Weight multiplier: 1.0 for average, higher for better, lower for worse
            if avg_success_rate > 0:
                multiplier = success_rate / avg_success_rate
            else:
                multiplier = 1.0
            
            # Clamp between 0.5 and 2.0
            multiplier = max(0.5, min(2.0, multiplier))
            
            weights[domain] = multiplier
        
        self.weights = weights
        return weights
    
    async def optimize_agent_weights(self) -> Dict[str, float]:
        """Optimize agent weights based on success rates.
        
        Returns:
            Dictionary mapping agent to weight multiplier
        """
        performance = await self.analyze_routing_performance()
        
        if performance["total_decisions"] < self.min_samples:
            return {}
        
        agent_stats = performance["by_agent"]
        weights = {}
        
        # Calculate average success rate
        success_rates = [
            stats["success_rate"] 
            for stats in agent_stats.values() 
            if stats["total"] >= self.min_samples
        ]
        
        if not success_rates:
            return {}
        
        avg_success_rate = statistics.mean(success_rates)
        
        # Calculate weight multipliers
        for agent, stats in agent_stats.items():
            if stats["total"] < self.min_samples:
                continue
            
            success_rate = stats["success_rate"]
            
            # Weight multiplier
            if avg_success_rate > 0:
                multiplier = success_rate / avg_success_rate
            else:
                multiplier = 1.0
            
            # Clamp between 0.5 and 2.0
            multiplier = max(0.5, min(2.0, multiplier))
            
            weights[agent] = multiplier
        
        return weights
    
    async def get_optimization_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for improving routing accuracy.
        
        Returns:
            Dictionary with optimization recommendations
        """
        performance = await self.analyze_routing_performance()
        
        recommendations = {
            "total_decisions": performance["total_decisions"],
            "recommendations": []
        }
        
        if performance["total_decisions"] < self.min_samples:
            recommendations["recommendations"].append({
                "type": "insufficient_data",
                "message": f"Need at least {self.min_samples} completed routing decisions for optimization",
                "current": performance["total_decisions"],
                "needed": self.min_samples
            })
            return recommendations
        
        # Analyze domain performance
        domain_stats = performance["by_domain"]
        for domain, stats in domain_stats.items():
            if stats["total"] < self.min_samples:
                continue
            
            if stats["success_rate"] < 50:
                recommendations["recommendations"].append({
                    "type": "low_domain_success",
                    "domain": domain,
                    "success_rate": stats["success_rate"],
                    "message": f"Domain '{domain}' has low success rate ({stats['success_rate']:.1f}%)",
                    "suggestion": "Review domain keywords and routing logic"
                })
        
        # Analyze agent performance
        agent_stats = performance["by_agent"]
        for agent, stats in agent_stats.items():
            if stats["total"] < self.min_samples:
                continue
            
            if stats["success_rate"] < 50:
                recommendations["recommendations"].append({
                    "type": "low_agent_success",
                    "agent": agent,
                    "success_rate": stats["success_rate"],
                    "message": f"Agent '{agent}' has low success rate ({stats['success_rate']:.1f}%)",
                    "suggestion": "Review agent capabilities and prompts"
                })
        
        # Analyze strategy performance
        strategy_stats = performance["by_strategy"]
        if "rag" in strategy_stats and "base" in strategy_stats:
            rag_rate = strategy_stats["rag"]["success_rate"]
            base_rate = strategy_stats["base"]["success_rate"]
            
            if rag_rate < base_rate:
                recommendations["recommendations"].append({
                    "type": "rag_underperforming",
                    "rag_success_rate": rag_rate,
                    "base_success_rate": base_rate,
                    "message": f"RAG routing ({rag_rate:.1f}%) underperforming baseline ({base_rate:.1f}%)",
                    "suggestion": "Review pattern quality and similarity thresholds"
                })
            elif rag_rate > base_rate + 10:
                recommendations["recommendations"].append({
                    "type": "rag_success",
                    "rag_success_rate": rag_rate,
                    "base_success_rate": base_rate,
                    "improvement": rag_rate - base_rate,
                    "message": f"RAG routing achieving +{rag_rate - base_rate:.1f}% improvement over baseline",
                    "suggestion": "Consider using RAG routing by default"
                })
        
        return recommendations
    
    def apply_weights(self, base_score: float, domain: str, agent: str) -> float:
        """Apply optimized weights to a routing score.
        
        Args:
            base_score: Base routing score
            domain: Task domain
            agent: Agent role
            
        Returns:
            Weighted score
        """
        score = base_score
        
        # Apply domain weight
        if domain in self.weights:
            score *= self.weights[domain]
        
        return score
    
    async def run_optimization_cycle(self) -> Dict[str, Any]:
        """Run a complete optimization cycle.
        
        Returns:
            Dictionary with optimization results
        """
        # Analyze performance
        performance = await self.analyze_routing_performance()
        
        # Optimize weights
        domain_weights = await self.optimize_domain_weights()
        agent_weights = await self.optimize_agent_weights()
        
        # Get recommendations
        recommendations = await self.get_optimization_recommendations()
        
        return {
            "performance": performance,
            "domain_weights": domain_weights,
            "agent_weights": agent_weights,
            "recommendations": recommendations
        }

