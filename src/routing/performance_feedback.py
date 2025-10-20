"""Performance feedback loop for continuous improvement.

This module tracks agent performance over time and uses it to improve
routing decisions through continuous feedback.
"""

import asyncio
from typing import Dict, List, Any, Optional
from collections import defaultdict
import statistics
from datetime import datetime


class PerformanceFeedback:
    """Continuous performance tracking and feedback loop."""
    
    def __init__(self, db_store, update_interval: int = 10):
        """Initialize performance feedback.
        
        Args:
            db_store: SurrealDBStore instance
            update_interval: Number of tasks before updating performance metrics
        """
        self.db_store = db_store
        self.update_interval = update_interval
        self.task_counter = 0
        self.pending_updates = defaultdict(lambda: {
            "total": 0,
            "success": 0,
            "failure": 0,
            "latencies": []
        })
        
    async def record_task_execution(
        self,
        agent_role: str,
        success: bool,
        latency_ms: float
    ) -> None:
        """Record a task execution for an agent.
        
        Args:
            agent_role: Role of the agent that executed the task
            success: Whether the task succeeded
            latency_ms: Task execution latency in milliseconds
        """
        # Update pending metrics
        self.pending_updates[agent_role]["total"] += 1
        if success:
            self.pending_updates[agent_role]["success"] += 1
        else:
            self.pending_updates[agent_role]["failure"] += 1
        self.pending_updates[agent_role]["latencies"].append(latency_ms)
        
        self.task_counter += 1
        
        # Update performance metrics if interval reached
        if self.task_counter >= self.update_interval:
            await self.update_performance_metrics()
            self.task_counter = 0
    
    async def update_performance_metrics(self) -> None:
        """Update agent performance metrics in database."""
        if not self.pending_updates:
            return
        
        for agent_role, metrics in self.pending_updates.items():
            total = metrics["total"]
            success = metrics["success"]
            failure = metrics["failure"]
            latencies = metrics["latencies"]
            
            if total == 0:
                continue
            
            avg_latency = statistics.mean(latencies) if latencies else 0.0
            
            # Update in database
            await self.db_store.update_agent_performance(
                agent_role=agent_role,
                total_tasks=total,
                successful_tasks=success,
                failed_tasks=failure,
                avg_latency_ms=avg_latency
            )
        
        # Clear pending updates
        self.pending_updates.clear()
    
    async def get_agent_performance(self, agent_role: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for an agent.
        
        Args:
            agent_role: Role of the agent
            
        Returns:
            Dictionary with performance metrics or None
        """
        sql = "SELECT * FROM agent_performance WHERE agent_role = $agent_role LIMIT 1;"
        result = await self.db_store.query(sql, {"agent_role": agent_role})
        
        if result and isinstance(result, list) and len(result) > 0:
            return result[0]
        
        return None
    
    async def get_all_agent_performance(self) -> List[Dict[str, Any]]:
        """Get performance metrics for all agents.
        
        Returns:
            List of performance metrics
        """
        sql = "SELECT * FROM agent_performance;"
        result = await self.db_store.query(sql)
        
        if result and isinstance(result, list):
            return result
        
        return []
    
    async def get_top_performers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top performing agents by success rate.
        
        Args:
            limit: Maximum number of agents to return
            
        Returns:
            List of top performing agents
        """
        all_performance = await self.get_all_agent_performance()
        
        # Sort by success rate
        sorted_performance = sorted(
            all_performance,
            key=lambda x: x.get("success_rate", 0),
            reverse=True
        )
        
        return sorted_performance[:limit]
    
    async def get_low_performers(self, threshold: float = 50.0, limit: int = 10) -> List[Dict[str, Any]]:
        """Get low performing agents below threshold.
        
        Args:
            threshold: Success rate threshold (percentage)
            limit: Maximum number of agents to return
            
        Returns:
            List of low performing agents
        """
        all_performance = await self.get_all_agent_performance()
        
        # Filter by threshold
        low_performers = [
            p for p in all_performance
            if p.get("success_rate", 100) < threshold
        ]
        
        # Sort by success rate (lowest first)
        sorted_performance = sorted(
            low_performers,
            key=lambda x: x.get("success_rate", 0)
        )
        
        return sorted_performance[:limit]
    
    async def calculate_performance_score(self, agent_role: str) -> float:
        """Calculate overall performance score for an agent.
        
        Args:
            agent_role: Role of the agent
            
        Returns:
            Performance score (0.0-1.0)
        """
        performance = await self.get_agent_performance(agent_role)
        
        if not performance:
            return 0.5  # Neutral score for unknown agents
        
        success_rate = performance.get("success_rate", 0) / 100.0
        
        # Normalize latency (assume 1000ms is baseline)
        avg_latency = performance.get("avg_latency_ms", 1000)
        latency_score = max(0.0, min(1.0, 1000 / max(avg_latency, 100)))
        
        # Weighted combination (70% success rate, 30% latency)
        score = (success_rate * 0.7) + (latency_score * 0.3)
        
        return score
    
    async def get_routing_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for routing based on performance.
        
        Returns:
            Dictionary with routing recommendations
        """
        top_performers = await self.get_top_performers(limit=5)
        low_performers = await self.get_low_performers(threshold=50.0, limit=5)
        
        recommendations = {
            "top_performers": [
                {
                    "agent": p.get("agent_role"),
                    "success_rate": p.get("success_rate"),
                    "total_tasks": p.get("total_tasks"),
                    "recommendation": "Prefer this agent for similar tasks"
                }
                for p in top_performers
            ],
            "low_performers": [
                {
                    "agent": p.get("agent_role"),
                    "success_rate": p.get("success_rate"),
                    "total_tasks": p.get("total_tasks"),
                    "recommendation": "Avoid or retrain this agent"
                }
                for p in low_performers
            ],
            "overall_recommendation": (
                f"Route to top {len(top_performers)} performers when possible. "
                f"Investigate {len(low_performers)} low performers."
            )
        }
        
        return recommendations
    
    async def apply_performance_boost(
        self,
        base_score: float,
        agent_role: str
    ) -> float:
        """Apply performance-based boost to routing score.
        
        Args:
            base_score: Base routing score
            agent_role: Agent role
            
        Returns:
            Boosted score
        """
        performance_score = await self.calculate_performance_score(agent_role)
        
        # Apply boost (performance_score acts as multiplier 0.0-1.0)
        # Convert to range 0.5-1.5 for reasonable boost
        multiplier = 0.5 + performance_score
        
        return base_score * multiplier
    
    async def run_feedback_cycle(self) -> Dict[str, Any]:
        """Run a complete feedback cycle.
        
        Returns:
            Dictionary with feedback cycle results
        """
        # Update any pending metrics
        await self.update_performance_metrics()
        
        # Get performance data
        all_performance = await self.get_all_agent_performance()
        top_performers = await self.get_top_performers(limit=5)
        low_performers = await self.get_low_performers(threshold=50.0, limit=5)
        recommendations = await self.get_routing_recommendations()
        
        # Calculate statistics
        if all_performance:
            success_rates = [p.get("success_rate", 0) for p in all_performance]
            avg_success_rate = statistics.mean(success_rates)
            median_success_rate = statistics.median(success_rates)
        else:
            avg_success_rate = 0.0
            median_success_rate = 0.0
        
        return {
            "total_agents": len(all_performance),
            "avg_success_rate": avg_success_rate,
            "median_success_rate": median_success_rate,
            "top_performers": len(top_performers),
            "low_performers": len(low_performers),
            "recommendations": recommendations,
            "feedback_applied": True
        }

