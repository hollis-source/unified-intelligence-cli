#!/usr/bin/env python3
"""
Self-Improvement Runner
- Runs the autonomous self-improvement loop
- Generates weekly improvement reports

Usage:
  python scripts/self_improvement_runner.py --cycles 5 --max-tasks 3
  python scripts/self_improvement_runner.py --continuous --max-cycles 100
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def run_cycles(args) -> int:
    """Run self-improvement cycles."""
    try:
        # Import dependencies
        from src.claude_orchestrator.orchestrators.self_improvement_orchestrator import SelfImprovementOrchestrator
        from src.claude_orchestrator.adapters.single_worker_pool import SingleWorkerPool
        from src.claude_orchestrator.entities.worker import WorkerPoolConfig
        
        # Initialize worker pool
        config = WorkerPoolConfig(
            pool_type="local",  # Use local worker pool for dogfooding
            max_workers=1,
            working_dir=os.getenv("WORKER_WORKSPACE", "."),
        )
        
        # Use LocalWorkerPool for dogfooding
        from src.claude_orchestrator.adapters.local_worker_pool import LocalWorkerPool
        pool = LocalWorkerPool(config)
        
        # Initialize LLM provider (optional)
        llm_provider = None
        if args.use_llm:
            try:
                from src.adapters.llm.qwen_agent_adapter import QwenAgentAdapter
                llm_provider = QwenAgentAdapter()
                logger.info("LLM provider initialized: Qwen")
            except Exception as e:
                logger.warning(f"Could not initialize LLM provider: {e}")
        
        # Initialize orchestrator
        orchestrator = SelfImprovementOrchestrator(
            worker_pool=pool,
            llm_provider=llm_provider,
            project_path=args.project_path,
            coverage_file=args.coverage_file,
            db_store=None,  # TODO: wire DB store
        )
        
        # Run cycles
        cycle_results = []
        
        if args.continuous:
            logger.info(f"Starting continuous self-improvement (max {args.max_cycles} cycles)")
            
            for i in range(args.max_cycles):
                logger.info(f"\n{'='*70}")
                logger.info(f"CYCLE {i+1}/{args.max_cycles}")
                logger.info(f"{'='*70}\n")
                
                result = await orchestrator.run_cycle(
                    max_tasks=args.max_tasks,
                    analysis_days=args.analysis_days,
                )
                
                cycle_results.append(result)
                
                # Check for stagnation
                if len(orchestrator.health_history) >= 3:
                    recent = orchestrator.health_history[-3:]
                    if max(recent) - min(recent) < 1.0:
                        logger.info("Health score stable, stopping continuous mode")
                        break
                
                # Delay between cycles
                if i < args.max_cycles - 1:
                    logger.info(f"Waiting {args.delay_seconds}s before next cycle...")
                    await asyncio.sleep(args.delay_seconds)
        
        else:
            logger.info(f"Running {args.cycles} self-improvement cycles")
            
            for i in range(args.cycles):
                result = await orchestrator.run_cycle(
                    max_tasks=args.max_tasks,
                    analysis_days=args.analysis_days,
                )
                
                cycle_results.append(result)
                
                if i < args.cycles - 1:
                    await asyncio.sleep(args.delay_seconds)
        
        # Generate report
        stats = orchestrator.get_statistics()
        
        logger.info(f"\n{'='*70}")
        logger.info("SELF-IMPROVEMENT SUMMARY")
        logger.info(f"{'='*70}")
        logger.info(f"Cycles completed: {stats['cycles_completed']}")
        logger.info(f"Tasks generated: {stats['tasks_generated']}")
        logger.info(f"Tasks executed: {stats['tasks_executed']}")
        logger.info(f"Success rate: {stats['success_rate']*100:.1f}%")
        logger.info(f"Health trend: {stats['health_trend']}")
        logger.info(f"Current health: {stats['current_health']:.1f}/100")
        logger.info(f"{'='*70}\n")
        
        # Write report
        report_path = _write_report(stats, cycle_results)
        logger.info(f"Report written to: {report_path}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Self-improvement runner failed: {e}", exc_info=True)
        return 1


def _write_report(stats: dict, cycle_results: list) -> Path:
    """Write improvement report to logs/."""
    outdir = Path("logs")
    outdir.mkdir(parents=True, exist_ok=True)
    
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    
    # JSON report
    json_path = outdir / f"self_improvement_report_{ts}.json"
    json_path.write_text(json.dumps({
        "statistics": stats,
        "cycles": cycle_results,
    }, indent=2), encoding="utf-8")
    
    # Markdown report
    md_path = outdir / f"self_improvement_report_{ts}.md"
    
    lines = [
        "# Self-Improvement Report",
        f"Generated: {ts}",
        "",
        "## Summary",
        f"- Cycles completed: {stats['cycles_completed']}",
        f"- Tasks generated: {stats['tasks_generated']}",
        f"- Tasks executed: {stats['tasks_executed']}",
        f"- Success rate: {stats['success_rate']*100:.1f}%",
        f"- Health trend: {stats['health_trend']}",
        f"- Current health: {stats['current_health']:.1f}/100",
        "",
        "## Health History",
    ]
    
    for i, score in enumerate(stats['health_history'], 1):
        lines.append(f"- Cycle {i}: {score:.1f}/100")
    
    lines.extend([
        "",
        "## Cycle Details",
    ])
    
    for i, cycle in enumerate(cycle_results, 1):
        lines.extend([
            f"### Cycle {i}",
            f"- Timestamp: {cycle.get('timestamp')}",
            f"- Health score: {cycle.get('health_score', 0):.1f}/100",
            f"- Tasks generated: {cycle.get('tasks_generated', 0)}",
            f"- Tasks executed: {cycle.get('tasks_executed', 0)}",
            f"- Tasks succeeded: {cycle.get('tasks_succeeded', 0)}",
            f"- Tasks failed: {cycle.get('tasks_failed', 0)}",
            "",
        ])
    
    md_path.write_text("\n".join(lines), encoding="utf-8")
    
    return md_path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=1, help="Number of cycles to run")
    ap.add_argument("--continuous", action="store_true", help="Run continuously until stagnation")
    ap.add_argument("--max-cycles", type=int, default=100, help="Max cycles in continuous mode")
    ap.add_argument("--max-tasks", type=int, default=5, help="Max tasks per cycle")
    ap.add_argument("--analysis-days", type=int, default=30, help="Days of history to analyze")
    ap.add_argument("--delay-seconds", type=int, default=60, help="Delay between cycles")
    ap.add_argument("--project-path", default=".", help="Project root path")
    ap.add_argument("--coverage-file", default="coverage.xml", help="Coverage report path")
    ap.add_argument("--use-llm", action="store_true", help="Use LLM for task generation")
    ap.add_argument("--no-llm", dest="use_llm", action="store_false")
    ap.set_defaults(use_llm=True)
    
    args = ap.parse_args(argv)
    
    return asyncio.run(run_cycles(args))


if __name__ == "__main__":
    raise SystemExit(main())

