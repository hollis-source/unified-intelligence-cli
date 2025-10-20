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
        """GET /api/rag/weights - Weight optimization status.
        Also records an audit entry (preview) with suggested weights and performance snapshot.
        """
        try:
            await self._ensure_initialized()

            optimizer = WeightOptimizer(db_store=self.db_store)

            # Run optimization cycle
            results = await optimizer.run_optimization_cycle()

            # Audit (preview only; does not apply weights)
            try:
                if self.db_store is not None:
                    await self.db_store.store_audit_log(
                        action="weight_optimization_preview",
                        actor=request.headers.get("X-Actor", "api"),
                        reason="GET /api/rag/weights",
                        before=None,
                        after={
                            "domain_weights": results.get("domain_weights", {}),
                            "agent_weights": results.get("agent_weights", {})
                        },
                        metadata={
                            "total_decisions": results.get("performance", {}).get("total_decisions", 0),
                            "recommendations": results.get("recommendations", {}).get("recommendations", [])
                        }
                    )
            except Exception:
                # Non-fatal if audit logging fails
                pass

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

    async def handle_audit_list(self, request: web.Request) -> web.Response:
        """GET /api/rag/audit - List audit entries (preview)."""
        try:
            await self._ensure_initialized()
            limit = int(request.query.get("limit", "20"))
            action = request.query.get("action")
            where = " WHERE action = $action" if action else ""
            params = {"action": action} if action else {}
            rows = await self.db_store.query(f"SELECT * FROM audit_log ORDER BY ts DESC LIMIT {limit}{where}", params)
            return web.json_response({"status": "ok", "audit": rows})
        except Exception as e:
            return web.json_response({"status": "error", "error": str(e)}, status=500)

    async def handle_weights_rollback(self, request: web.Request) -> web.Response:
        """POST /api/rag/weights/rollback - Rollback weights using an audit snapshot.
        Body: {"audit_id": "<id>", "dry_run": false}
        """
        try:
            await self._ensure_initialized()
            data = await request.json()
            audit_id = str(data.get("audit_id", "")).strip()
            dry_run = bool(data.get("dry_run", False))
            if not audit_id:
                return web.json_response({"status": "error", "error": "audit_id required"}, status=400)
            rows = await self.db_store.query("SELECT * FROM audit_log WHERE id = $id", {"id": audit_id})
            entry = rows[0] if rows else None
            if not entry:
                return web.json_response({"status": "error", "error": "audit entry not found"}, status=404)
            before_rows = (entry.get("before") or {}).get("rows") or []
            if not before_rows:
                return web.json_response({"status": "error", "error": "no before snapshot in audit entry"}, status=400)
            # Apply or preview set operations
            updated = 0
            for r in before_rows:
                dom = r.get("domain"); agent = r.get("agent"); w = float(r.get("weight", 1.0))
                if not dry_run:
                    await self.db_store.query(
                        "UPDATE routing_weight SET weight = $w, last_updated = time::now() WHERE domain = $d AND agent = $a",
                        {"w": w, "d": dom, "a": agent},
                    )
                updated += 1
            await self.db_store.store_audit_log(
                action="weights_rollback" + ("_dry_run" if dry_run else ""),
                actor=request.headers.get("X-Actor", "api"),
                reason=f"rollback from audit {audit_id}",
                before=None,
                after={"restored_from": audit_id},
                metadata={"updated": updated},
            )
            return web.json_response({"status": "ok", "updated": updated, "dry_run": dry_run})
        except Exception as e:
            return web.json_response({"status": "error", "error": str(e)}, status=500)

    async def handle_rag_ui(self, request: web.Request) -> web.Response:
        """GET /rag/ui - Minimal UI for audit view and rollback."""
        html = """
        <!doctype html><html><head><meta charset='utf-8'><title>RAG Admin</title></head>
        <body style="font-family: system-ui, sans-serif; margin: 24px;">
          <h1>RAG Admin</h1>
          <section>
            <h2>Rollback Weights</h2>
            <form id="rb">
              <label>Audit ID: <input name="audit_id" style="width: 360px"></label>
              <label><input type="checkbox" name="dry_run"> Dry run</label>
              <button type="submit">Rollback</button>
            </form>
            <pre id="out" style="background:#f5f5f5; padding:12px;"></pre>
          </section>
          <script>
            const f=document.getElementById('rb'); const out=document.getElementById('out');
            f.onsubmit=async (e)=>{e.preventDefault();
              const fd=new FormData(f); const body={audit_id:fd.get('audit_id'), dry_run:!!fd.get('dry_run')};
              out.textContent='Running...';
              const r=await fetch('/api/rag/weights/rollback', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify(body)});
              out.textContent=await r.text();
            };
          </script>
        </body></html>
        """
        return web.Response(text=html, content_type="text/html")


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
    app.router.add_get("/rag/ui", server.handle_rag_ui)
    app.router.add_get("/api/rag/audit", server.handle_audit_list)
    app.router.add_post("/api/rag/weights/rollback", server.handle_weights_rollback)

