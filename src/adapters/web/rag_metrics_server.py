"""RAG Metrics API Server.

This module provides HTTP endpoints for RAG metrics, integrated with the
existing aiohttp web server infrastructure.
"""

from __future__ import annotations

import os
from typing import Dict, Any, Optional
from aiohttp import web

from src.routing.weight_optimizer import WeightOptimizer
from src.routing.drift_detector import DriftDetector
from src.routing.performance_feedback import PerformanceFeedback
from src.routing.ab_testing import ABTest
from src.monitoring.rag_alerting import RAGAlerting
from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.llm.rag_config import RAGConfig


class RAGMetricsServer:
    """RAG metrics HTTP server."""
    
    def __init__(self, db_store: Optional[SurrealDBStore] = None):
        """Initialize RAG metrics server.
        
        Args:
            db_store: SurrealDBStore instance (will create if None)
        """
        self.db_store = db_store
        self._initialized = False
        
    async def _ensure_initialized(self) -> None:
        """Ensure database connection is initialized."""
        if self._initialized:
            return
            
        if self.db_store is None:
            config = RAGConfig()
            db_url = os.getenv("SURREALDB_URL", "ws://localhost:8000")
            
            self.db_store = SurrealDBStore(
                url=db_url,
                namespace=config.db_namespace,
                database=config.db_database,
                user=config.db_user,
                password=config.db_password
            )
            
            try:
                await self.db_store.connect()
                self._initialized = True
            except Exception as e:
                raise RuntimeError(f"Failed to connect to SurrealDB: {e}")
        else:
            self._initialized = True
    
    async def handle_metrics_overview(self, request: web.Request) -> web.Response:
        """GET /api/rag/metrics - Overview of all RAG metrics."""
        try:
            await self._ensure_initialized()
            
            # Get pattern count
            sql = "SELECT count() as total FROM execution_log GROUP ALL;"
            result = await self.db_store.query(sql)
            
            total_patterns = 0
            if result and isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], dict) and "total" in result[0]:
                    total_patterns = result[0]["total"]
            
            # Get routing decisions count
            sql = "SELECT count() as total FROM routing_decisions GROUP ALL;"
            result = await self.db_store.query(sql)
            
            total_decisions = 0
            if result and isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], dict) and "total" in result[0]:
                    total_decisions = result[0]["total"]
            
            # Get routing accuracy
            accuracy = await self.db_store.get_routing_accuracy(strategy="rag", limit=100)
            
            return web.json_response({
                "status": "ok",
                "metrics": {
                    "total_patterns": total_patterns,
                    "total_routing_decisions": total_decisions,
                    "rag_routing_accuracy": accuracy,
                    "rag_enabled": True
                }
            })
            
        except Exception as e:
            return web.json_response({
                "status": "error",
                "error": str(e)
            }, status=500)
    
    async def handle_pattern_metrics(self, request: web.Request) -> web.Response:
        """GET /api/rag/patterns - Pattern count metrics by domain."""
        try:
            await self._ensure_initialized()
            
            # Get patterns by domain
            sql = "SELECT task_domain, count() as count FROM execution_log GROUP BY task_domain;"
            result = await self.db_store.query(sql)
            
            patterns_by_domain = {}
            if result and isinstance(result, list):
                for item in result:
                    domain = item.get("task_domain", "unknown")
                    count = item.get("count", 0)
                    patterns_by_domain[domain] = count
            
            # Get total
            total = sum(patterns_by_domain.values())
            
            return web.json_response({
                "status": "ok",
                "patterns": {
                    "total": total,
                    "by_domain": patterns_by_domain
                }
            })
            
        except Exception as e:
            return web.json_response({
                "status": "error",
                "error": str(e)
            }, status=500)
    
    async def handle_routing_accuracy(self, request: web.Request) -> web.Response:
        """GET /api/rag/routing/accuracy - Routing accuracy metrics."""
        try:
            await self._ensure_initialized()
            
            # Get accuracy for both strategies
            rag_accuracy = await self.db_store.get_routing_accuracy(strategy="rag", limit=100)
            base_accuracy = await self.db_store.get_routing_accuracy(strategy="base", limit=100)
            
            # Get recent decisions
            recent_decisions = await self.db_store.get_recent_routing_decisions(limit=10)
            
            return web.json_response({
                "status": "ok",
                "accuracy": {
                    "rag": rag_accuracy,
                    "baseline": base_accuracy,
                    "improvement": rag_accuracy - base_accuracy
                },
                "recent_decisions": [
                    {
                        "task": d.get("task_description", "")[:50] + "...",
                        "strategy": d.get("routing_strategy"),
                        "agent": d.get("selected_agent"),
                        "success": d.get("success")
                    }
                    for d in recent_decisions
                ]
            })
            
        except Exception as e:
            return web.json_response({
                "status": "error",
                "error": str(e)
            }, status=500)
    
    async def handle_performance_metrics(self, request: web.Request) -> web.Response:
        """GET /api/rag/performance - Performance metrics."""
        try:
            await self._ensure_initialized()
            
            feedback = PerformanceFeedback(db_store=self.db_store)
            
            # Get all agent performance
            all_performance = await feedback.get_all_agent_performance()
            
            # Get top performers
            top_performers = await feedback.get_top_performers(limit=5)
            
            # Get low performers
            low_performers = await feedback.get_low_performers(threshold=50.0, limit=5)
            
            return web.json_response({
                "status": "ok",
                "performance": {
                    "total_agents": len(all_performance),
                    "top_performers": [
                        {
                            "agent": p.get("agent_role"),
                            "success_rate": p.get("success_rate"),
                            "total_tasks": p.get("total_tasks")
                        }
                        for p in top_performers
                    ],
                    "low_performers": [
                        {
                            "agent": p.get("agent_role"),
                            "success_rate": p.get("success_rate"),
                            "total_tasks": p.get("total_tasks")
                        }
                        for p in low_performers
                    ]
                }
            })
            
        except Exception as e:
            return web.json_response({
                "status": "error",
                "error": str(e)
            }, status=500)
    
    async def handle_drift_detection(self, request: web.Request) -> web.Response:
        """GET /api/rag/drift - Drift detection status."""
        try:
            await self._ensure_initialized()
            
            detector = DriftDetector(db_store=self.db_store)
            
            # Get drift report
            report = await detector.get_drift_report()
            
            return web.json_response({
                "status": "ok",
                "drift": {
                    "needs_reembedding": report.get("needs_reembedding", False),
                    "drift_detected": report.get("drift_detection", {}).get("drift_detected", False),
                    "drift_score": report.get("drift_detection", {}).get("drift_score", 0.0),
                    "recommendation": report.get("overall_recommendation", ""),
                    "details": report
                }
            })
            
        except Exception as e:
            return web.json_response({
                "status": "error",
                "error": str(e)
            }, status=500)
    
    async def handle_ab_test(self, request: web.Request) -> web.Response:
        """GET /api/rag/ab-test - A/B test results."""
        try:
            await self._ensure_initialized()
            
            ab_test = ABTest(db_store=self.db_store)
            
            # Run A/B test
            results = await ab_test.run_ab_test()
            
            return web.json_response({
                "status": "ok",
                "ab_test": {
                    "test_name": results.get("test_name"),
                    "control": results.get("control"),
                    "treatment": results.get("treatment"),
                    "significant": results.get("statistics", {}).get("significant", False),
                    "improvement": results.get("statistics", {}).get("relative_improvement", 0.0),
                    "recommendation": results.get("recommendation"),
                    "sample_size_adequate": results.get("sample_size_adequate", False)
                }
            })
            
        except Exception as e:
            return web.json_response({
                "status": "error",
                "error": str(e)
            }, status=500)
    
    async def handle_weight_optimization(self, request: web.Request) -> web.Response:
        """GET /api/rag/weights - Weight optimization status."""
        try:
            await self._ensure_initialized()

            optimizer = WeightOptimizer(db_store=self.db_store)

            # Run optimization cycle
            results = await optimizer.run_optimization_cycle()

            return web.json_response({
                "status": "ok",
                "optimization": {
                    "total_decisions": results.get("performance", {}).get("total_decisions", 0),
                    "domain_weights": results.get("domain_weights", {}),
                    "agent_weights": results.get("agent_weights", {}),
                    "recommendations": results.get("recommendations", {}).get("recommendations", [])
                }
            })

        except Exception as e:
            return web.json_response({
                "status": "error",
                "error": str(e)
            }, status=500)

    async def handle_alerts(self, request: web.Request) -> web.Response:
        """GET /api/rag/alerts - Get current alerts."""
        try:
            await self._ensure_initialized()

            alerting = RAGAlerting(db_store=self.db_store)

            # Get alert summary
            summary = await alerting.get_alert_summary()

            return web.json_response({
                "status": "ok",
                "alerts": summary
            })

        except Exception as e:
            return web.json_response({
                "status": "error",
                "error": str(e)
            }, status=500)


def add_rag_routes(app: web.Application, db_store: Optional[SurrealDBStore] = None) -> None:
    """Add RAG metrics routes to an existing aiohttp application.

    Args:
        app: aiohttp Application instance
        db_store: Optional SurrealDBStore instance
    """
    server = RAGMetricsServer(db_store=db_store)

    app.router.add_get("/api/rag/metrics", server.handle_metrics_overview)
    app.router.add_get("/api/rag/patterns", server.handle_pattern_metrics)
    app.router.add_get("/api/rag/routing/accuracy", server.handle_routing_accuracy)
    app.router.add_get("/api/rag/performance", server.handle_performance_metrics)
    app.router.add_get("/api/rag/drift", server.handle_drift_detection)
    app.router.add_get("/api/rag/ab-test", server.handle_ab_test)
    app.router.add_get("/api/rag/weights", server.handle_weight_optimization)
    app.router.add_get("/api/rag/alerts", server.handle_alerts)

