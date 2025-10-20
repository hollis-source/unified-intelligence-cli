#!/usr/bin/env python3
"""
Agent Metrics Dashboard

Visualizes agent performance metrics over time:
- Completion rate trends
- Quality score improvements
- Latency optimization
- Cost tracking
- Week-over-week comparisons

Usage:
    python agent_metrics_dashboard.py
    python agent_metrics_dashboard.py --agent python-engineer
    python agent_metrics_dashboard.py --export report.html
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


class AgentMetricsDashboard:
    """Dashboard for visualizing agent performance metrics"""
    
    def __init__(self, data_dir: str = "data/agent_performance"):
        self.data_dir = Path(data_dir)
        self.metrics_history = self._load_all_metrics()
    
    def _load_all_metrics(self) -> List[Dict]:
        """Load all metric files from data directory"""
        if not self.data_dir.exists():
            return []
        
        all_metrics = []
        for file_path in sorted(self.data_dir.glob("*.json")):
            try:
                with open(file_path) as f:
                    data = json.load(f)
                    # Add filename for reference
                    for metric in data.get("metrics", []):
                        metric["source_file"] = file_path.name
                        metric["timestamp"] = data.get("timestamp", metric.get("timestamp"))
                    all_metrics.extend(data.get("metrics", []))
            except Exception as e:
                print(f"⚠️  Failed to load {file_path}: {e}")
        
        return all_metrics
    
    def get_agent_history(self, agent_role: str) -> List[Dict]:
        """Get historical metrics for specific agent"""
        return [m for m in self.metrics_history if m["agent_role"] == agent_role]
    
    def get_latest_metrics(self) -> Dict[str, Dict]:
        """Get most recent metrics for each agent"""
        latest = {}
        for metric in sorted(self.metrics_history, key=lambda m: m.get("timestamp", "")):
            latest[metric["agent_role"]] = metric
        return latest
    
    def calculate_improvement(self, agent_role: str) -> Optional[Dict]:
        """Calculate week-over-week improvement for agent"""
        history = self.get_agent_history(agent_role)
        if len(history) < 2:
            return None
        
        # Sort by timestamp
        history = sorted(history, key=lambda m: m.get("timestamp", ""))
        baseline = history[0]
        current = history[-1]
        
        return {
            "agent_role": agent_role,
            "baseline_date": baseline.get("timestamp", "unknown"),
            "current_date": current.get("timestamp", "unknown"),
            "completion_rate_delta": current["completion_rate"] - baseline["completion_rate"],
            "quality_score_delta": current["avg_quality_score"] - baseline["avg_quality_score"],
            "specificity_delta": current["avg_specificity"] - baseline["avg_specificity"],
            "latency_p95_delta": current["avg_latency_p95"] - baseline["avg_latency_p95"],
            "cost_delta": current["cost_per_task"] - baseline["cost_per_task"],
            "weeks_elapsed": self._calculate_weeks(baseline.get("timestamp"), current.get("timestamp"))
        }
    
    def _calculate_weeks(self, start: str, end: str) -> float:
        """Calculate weeks between two timestamps"""
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            delta = end_dt - start_dt
            return delta.days / 7.0
        except:
            return 0.0
    
    def identify_optimization_targets(self) -> List[Dict]:
        """
        Identify next optimization targets (highest impact/lowest effort).
        
        Impact = potential improvement * weight
        Effort = estimated complexity (heuristic)
        
        Returns list sorted by impact/effort ratio
        """
        latest = self.get_latest_metrics()
        targets = []
        
        for agent_role, metrics in latest.items():
            # Calculate gaps from target (80%)
            completion_gap = max(0, 80 - metrics["completion_rate"])
            quality_gap = max(0, 8.0 - metrics["avg_quality_score"]) * 10  # Scale to %
            specificity_gap = max(0, 80 - metrics["avg_specificity"])
            
            # Estimate impact (weighted)
            impact = (
                completion_gap * 0.4 +  # Completion most important
                quality_gap * 0.35 +     # Quality second
                specificity_gap * 0.25   # Specificity third
            )
            
            # Estimate effort (heuristic based on current performance)
            # Lower performance = easier to improve (low-hanging fruit)
            effort = (
                metrics["completion_rate"] * 0.4 +
                (metrics["avg_quality_score"] / 10 * 100) * 0.35 +
                metrics["avg_specificity"] * 0.25
            )
            
            # Avoid division by zero
            ratio = impact / max(effort, 1.0)
            
            targets.append({
                "agent_role": agent_role,
                "impact": impact,
                "effort": effort,
                "ratio": ratio,
                "completion_gap": completion_gap,
                "quality_gap": quality_gap / 10,  # Back to 1-10 scale
                "specificity_gap": specificity_gap,
                "recommendation": self._generate_recommendation(
                    agent_role, completion_gap, quality_gap / 10, specificity_gap
                )
            })
        
        return sorted(targets, key=lambda t: t["ratio"], reverse=True)
    
    def _generate_recommendation(
        self, agent_role: str, completion_gap: float, quality_gap: float, specificity_gap: float
    ) -> str:
        """Generate actionable recommendation based on gaps"""
        recommendations = []
        
        if completion_gap > 20:
            recommendations.append(f"Improve task completion rate (+{completion_gap:.0f}% needed)")
        if quality_gap > 2.0:
            recommendations.append(f"Enhance output quality (+{quality_gap:.1f} points needed)")
        if specificity_gap > 20:
            recommendations.append(f"Add more code references (+{specificity_gap:.0f}% needed)")
        
        if not recommendations:
            return "✅ Meeting targets - focus on consistency"
        
        return " | ".join(recommendations)
    
    def print_dashboard(self, agent_filter: Optional[str] = None):
        """Print dashboard to console"""
        print("\n" + "="*100)
        print("AGENT PERFORMANCE DASHBOARD")
        print("="*100 + "\n")
        
        # Current state
        print("📊 CURRENT STATE")
        print("─"*100)
        
        latest = self.get_latest_metrics()
        agents_to_show = [agent_filter] if agent_filter else sorted(latest.keys())
        
        for agent_role in agents_to_show:
            if agent_role not in latest:
                print(f"⚠️  No data for {agent_role}")
                continue
            
            m = latest[agent_role]
            print(f"\n{agent_role.upper()}")
            print(f"  Completion Rate:  {m['completion_rate']:>6.1f}%  {'✅' if m['completion_rate'] >= 80 else '⚠️'}")
            print(f"  Quality Score:    {m['avg_quality_score']:>6.1f}/10 {'✅' if m['avg_quality_score'] >= 8.0 else '⚠️'}")
            print(f"  Specificity:      {m['avg_specificity']:>6.1f}%  {'✅' if m['avg_specificity'] >= 80 else '⚠️'}")
            print(f"  Latency P95:      {m['avg_latency_p95']:>6.2f}s")
            print(f"  Cost per Task:    ${m['cost_per_task']:>6.4f}")
        
        # Improvement trajectory
        print("\n\n📈 IMPROVEMENT TRAJECTORY (Week-over-Week)")
        print("─"*100)
        
        for agent_role in agents_to_show:
            if agent_role not in latest:
                continue
            
            improvement = self.calculate_improvement(agent_role)
            if not improvement:
                print(f"\n{agent_role.upper()}: No historical data")
                continue
            
            print(f"\n{agent_role.upper()} ({improvement['weeks_elapsed']:.1f} weeks)")
            
            def format_delta(value, suffix="", reverse=False):
                if value == 0:
                    return f"  {value:+.1f}{suffix} →"
                arrow = "↑" if (value > 0) != reverse else "↓"
                emoji = "✅" if (value > 0) != reverse else "⚠️"
                return f"{emoji} {value:+.1f}{suffix} {arrow}"
            
            print(f"  Completion Rate:  {format_delta(improvement['completion_rate_delta'], '%')}")
            print(f"  Quality Score:    {format_delta(improvement['quality_score_delta'])}")
            print(f"  Specificity:      {format_delta(improvement['specificity_delta'], '%')}")
            print(f"  Latency P95:      {format_delta(improvement['latency_p95_delta'], 's', reverse=True)}")
            print(f"  Cost per Task:    {format_delta(improvement['cost_delta'], '', reverse=True)}")
        
        # Optimization targets
        print("\n\n🎯 NEXT OPTIMIZATION TARGETS (Highest Impact/Lowest Effort)")
        print("─"*100)
        
        targets = self.identify_optimization_targets()
        if agent_filter:
            targets = [t for t in targets if t["agent_role"] == agent_filter]
        
        for i, target in enumerate(targets[:5], 1):  # Top 5
            print(f"\n{i}. {target['agent_role'].upper()}")
            print(f"   Impact/Effort Ratio: {target['ratio']:.2f}")
            print(f"   Recommendation: {target['recommendation']}")
        
        print("\n" + "="*100 + "\n")
    
    def export_html(self, output_file: str):
        """Export dashboard as HTML report"""
        html = self._generate_html()
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            f.write(html)
        
        print(f"✅ Dashboard exported to {output_path}")
    
    def _generate_html(self) -> str:
        """Generate HTML dashboard"""
        latest = self.get_latest_metrics()
        targets = self.identify_optimization_targets()
        
        # Build HTML
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Agent Performance Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background: #f5f5f5; }
        h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        .agent-card { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric { display: inline-block; margin: 10px 20px 10px 0; }
        .metric-label { font-weight: bold; color: #666; }
        .metric-value { font-size: 1.2em; color: #333; }
        .good { color: #4CAF50; }
        .warning { color: #FF9800; }
        .target { background: #E3F2FD; padding: 15px; margin: 10px 0; border-left: 4px solid #2196F3; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; background: white; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #4CAF50; color: white; }
        tr:hover { background: #f5f5f5; }
    </style>
</head>
<body>
    <h1>🎯 Agent Performance Dashboard</h1>
    <p>Generated: {timestamp}</p>
    
    <h2>📊 Current Performance</h2>
""".format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # Agent cards
        for agent_role in sorted(latest.keys()):
            m = latest[agent_role]
            completion_class = "good" if m["completion_rate"] >= 80 else "warning"
            quality_class = "good" if m["avg_quality_score"] >= 8.0 else "warning"
            specificity_class = "good" if m["avg_specificity"] >= 80 else "warning"
            
            html += f"""
    <div class="agent-card">
        <h3>{agent_role.upper()}</h3>
        <div class="metric">
            <span class="metric-label">Completion Rate:</span>
            <span class="metric-value {completion_class}">{m['completion_rate']:.1f}%</span>
        </div>
        <div class="metric">
            <span class="metric-label">Quality Score:</span>
            <span class="metric-value {quality_class}">{m['avg_quality_score']:.1f}/10</span>
        </div>
        <div class="metric">
            <span class="metric-label">Specificity:</span>
            <span class="metric-value {specificity_class}">{m['avg_specificity']:.1f}%</span>
        </div>
        <div class="metric">
            <span class="metric-label">Latency P95:</span>
            <span class="metric-value">{m['avg_latency_p95']:.2f}s</span>
        </div>
        <div class="metric">
            <span class="metric-label">Cost/Task:</span>
            <span class="metric-value">${m['cost_per_task']:.4f}</span>
        </div>
    </div>
"""
        
        # Optimization targets
        html += """
    <h2>🎯 Optimization Targets</h2>
    <table>
        <tr>
            <th>Rank</th>
            <th>Agent</th>
            <th>Impact/Effort</th>
            <th>Recommendation</th>
        </tr>
"""
        
        for i, target in enumerate(targets, 1):
            html += f"""
        <tr>
            <td>{i}</td>
            <td>{target['agent_role']}</td>
            <td>{target['ratio']:.2f}</td>
            <td>{target['recommendation']}</td>
        </tr>
"""
        
        html += """
    </table>
</body>
</html>
"""
        
        return html


def main():
    parser = argparse.ArgumentParser(description="Agent Metrics Dashboard")
    parser.add_argument("--agent", help="Filter by specific agent")
    parser.add_argument("--export", help="Export to HTML file")
    parser.add_argument("--data-dir", default="data/agent_performance", help="Metrics data directory")
    
    args = parser.parse_args()
    
    dashboard = AgentMetricsDashboard(args.data_dir)
    
    if args.export:
        dashboard.export_html(args.export)
    else:
        dashboard.print_dashboard(args.agent)


if __name__ == "__main__":
    main()

