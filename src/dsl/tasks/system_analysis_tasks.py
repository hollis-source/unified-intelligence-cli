"""
System Resource Analysis Tasks for DSL

Week 12+: System monitoring and optimization workflows.
Analyze processes, resource usage, and provide ROI recommendations.

Clean Architecture: Use Cases layer (system analysis business logic)
SOLID: SRP - each task has single responsibility
"""

import asyncio
import subprocess
from typing import Any, Dict, List
import psutil
import json


async def get_running_processes(input_data: Any = None) -> Dict[str, Any]:
    """
    Get all running processes with resource usage.

    Returns processes sorted by CPU usage.
    """
    processes = []

    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
        try:
            pinfo = proc.info
            if pinfo['cpu_percent'] > 0 or pinfo['memory_percent'] > 0.1:
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'user': pinfo['username'],
                    'cpu_percent': pinfo['cpu_percent'],
                    'memory_percent': pinfo['memory_percent'],
                    'status': pinfo['status']
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # Sort by CPU usage
    processes.sort(key=lambda x: x['cpu_percent'], reverse=True)

    return {
        "task": "get_running_processes",
        "status": "success",
        "total_processes": len(processes),
        "processes": processes[:50]  # Top 50
    }


async def get_system_resources(input_data: Any = None) -> Dict[str, Any]:
    """
    Get current system resource usage (CPU, RAM, disk, network).
    """
    cpu_percent = psutil.cpu_percent(interval=1, percpu=False)
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()

    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    disk = psutil.disk_usage('/')

    net_io = psutil.net_io_counters()

    return {
        "task": "get_system_resources",
        "status": "success",
        "cpu": {
            "percent_used": cpu_percent,
            "percent_available": 100 - cpu_percent,
            "count": cpu_count,
            "freq_current_mhz": cpu_freq.current if cpu_freq else None
        },
        "memory": {
            "total_gb": mem.total / (1024 ** 3),
            "available_gb": mem.available / (1024 ** 3),
            "used_gb": mem.used / (1024 ** 3),
            "percent_used": mem.percent,
            "percent_available": 100 - mem.percent
        },
        "swap": {
            "total_gb": swap.total / (1024 ** 3),
            "used_gb": swap.used / (1024 ** 3),
            "percent_used": swap.percent
        },
        "disk": {
            "total_gb": disk.total / (1024 ** 3),
            "used_gb": disk.used / (1024 ** 3),
            "free_gb": disk.free / (1024 ** 3),
            "percent_used": disk.percent
        },
        "network": {
            "bytes_sent_gb": net_io.bytes_sent / (1024 ** 3),
            "bytes_recv_gb": net_io.bytes_recv / (1024 ** 3)
        }
    }


async def identify_killable_processes(input_data: Any = None) -> Dict[str, Any]:
    """
    Identify processes that can be killed to free resources.

    Criteria:
    - High CPU/memory usage
    - Not system-critical
    - User-owned processes
    """
    if input_data and "processes" in input_data:
        processes = input_data["processes"]
    else:
        result = await get_running_processes()
        processes = result["processes"]

    killable = []
    critical_names = {'systemd', 'init', 'kernel', 'sshd', 'dockerd', 'containerd'}

    for proc in processes:
        # Skip system processes
        if proc['user'] in ['root', 'systemd']:
            if proc['name'].lower() in critical_names:
                continue

        # Identify resource hogs
        if proc['cpu_percent'] > 50 or proc['memory_percent'] > 10:
            killable.append({
                'pid': proc['pid'],
                'name': proc['name'],
                'cpu_percent': proc['cpu_percent'],
                'memory_percent': proc['memory_percent'],
                'reason': f"High resource usage: {proc['cpu_percent']:.1f}% CPU, {proc['memory_percent']:.1f}% RAM"
            })

    return {
        "task": "identify_killable_processes",
        "status": "success",
        "killable_count": len(killable),
        "killable_processes": killable
    }


async def analyze_cpu_bottlenecks(input_data: Any = None) -> Dict[str, Any]:
    """
    Analyze CPU bottlenecks and recommend optimizations.
    """
    resources = await get_system_resources()
    processes = await get_running_processes()

    cpu_data = resources["cpu"]
    cpu_percent = cpu_data["percent_used"]

    bottlenecks = []
    recommendations = []

    if cpu_percent > 80:
        bottlenecks.append({
            "type": "high_cpu_usage",
            "severity": "critical",
            "value": cpu_percent,
            "description": f"CPU usage at {cpu_percent:.1f}% - system overloaded"
        })
        recommendations.append("Kill non-essential processes or scale to more cores")

    # Identify top CPU consumers
    top_processes = processes["processes"][:5]
    if top_processes and top_processes[0]['cpu_percent'] > 200:
        bottlenecks.append({
            "type": "single_process_hog",
            "severity": "high",
            "process": top_processes[0]['name'],
            "pid": top_processes[0]['pid'],
            "cpu_percent": top_processes[0]['cpu_percent'],
            "description": f"Process '{top_processes[0]['name']}' consuming {top_processes[0]['cpu_percent']:.1f}% CPU"
        })
        recommendations.append(f"Consider killing PID {top_processes[0]['pid']} ({top_processes[0]['name']}) or optimizing its workload")

    return {
        "task": "analyze_cpu_bottlenecks",
        "status": "success",
        "bottlenecks": bottlenecks,
        "recommendations": recommendations,
        "top_cpu_processes": top_processes
    }


async def calculate_gpu_roi(input_data: Any = None) -> Dict[str, Any]:
    """
    Calculate ROI for GPU deployment vs local CPU execution.

    Compares cost and time for different execution strategies.
    """
    # Assumptions
    cpu_time_per_example = 592  # seconds (from previous eval)
    gpu_time_per_example = 20   # seconds (baseline)

    examples_count = input_data.get("examples_count", 31) if input_data else 31
    developer_hourly_rate = input_data.get("dev_rate", 100) if input_data else 100  # $/hr

    # CPU execution
    cpu_total_time_hours = (cpu_time_per_example * examples_count) / 3600
    cpu_compute_cost = 0  # Local machine
    cpu_developer_cost = cpu_total_time_hours * developer_hourly_rate  # Waiting time
    cpu_total_cost = cpu_compute_cost + cpu_developer_cost

    # GPU execution options
    gpu_options = {
        "modal_t4": {
            "name": "Modal T4",
            "gpu_cost_per_hour": 0.59,
            "time_per_example": 20,
            "setup_time_hours": 0.5
        },
        "lambda_h100": {
            "name": "Lambda Labs H100",
            "gpu_cost_per_hour": 1.99,
            "time_per_example": 8,  # Faster than T4
            "setup_time_hours": 0.5
        },
        "together_h100": {
            "name": "Together.ai H100",
            "gpu_cost_per_hour": 1.76,
            "time_per_example": 8,
            "setup_time_hours": 0.25  # API-based, faster setup
        }
    }

    gpu_analysis = {}
    for key, option in gpu_options.items():
        total_time_hours = (option["time_per_example"] * examples_count) / 3600 + option["setup_time_hours"]
        gpu_compute_cost = total_time_hours * option["gpu_cost_per_hour"]
        gpu_developer_cost = total_time_hours * developer_hourly_rate
        gpu_total_cost = gpu_compute_cost + gpu_developer_cost

        time_saved_hours = cpu_total_time_hours - total_time_hours
        cost_saved = cpu_total_cost - gpu_total_cost
        roi_multiplier = cost_saved / gpu_compute_cost if gpu_compute_cost > 0 else 0

        gpu_analysis[key] = {
            "name": option["name"],
            "total_time_hours": round(total_time_hours, 2),
            "gpu_compute_cost": round(gpu_compute_cost, 2),
            "developer_cost": round(gpu_developer_cost, 2),
            "total_cost": round(gpu_total_cost, 2),
            "time_saved_hours": round(time_saved_hours, 2),
            "cost_saved": round(cost_saved, 2),
            "roi_multiplier": round(roi_multiplier, 2),
            "speedup": round(cpu_total_time_hours / total_time_hours, 1)
        }

    # Find best option
    best_option = max(gpu_analysis.items(), key=lambda x: x[1]["cost_saved"])

    return {
        "task": "calculate_gpu_roi",
        "status": "success",
        "examples_count": examples_count,
        "developer_rate": developer_hourly_rate,
        "cpu_execution": {
            "total_time_hours": round(cpu_total_time_hours, 2),
            "compute_cost": cpu_compute_cost,
            "developer_cost": round(cpu_developer_cost, 2),
            "total_cost": round(cpu_total_cost, 2)
        },
        "gpu_options": gpu_analysis,
        "recommendation": {
            "provider": best_option[1]["name"],
            "key": best_option[0],
            "savings": best_option[1]["cost_saved"],
            "speedup": best_option[1]["speedup"],
            "reason": f"Saves ${best_option[1]['cost_saved']:.2f} and {best_option[1]['time_saved_hours']:.1f} hours ({best_option[1]['speedup']}x faster)"
        }
    }


async def generate_optimization_report(input_data: Any = None) -> Dict[str, Any]:
    """
    Generate comprehensive system optimization report.

    Aggregates all analysis results and provides actionable recommendations.
    """
    # Gather all analysis data
    if input_data and isinstance(input_data, dict):
        resources = input_data.get("resources") or (await get_system_resources())
        processes = input_data.get("processes") or (await get_running_processes())
        killable = input_data.get("killable") or (await identify_killable_processes(processes))
        bottlenecks = input_data.get("bottlenecks") or (await analyze_cpu_bottlenecks())
        gpu_roi = input_data.get("gpu_roi") or (await calculate_gpu_roi())
    else:
        resources = await get_system_resources()
        processes = await get_running_processes()
        killable = await identify_killable_processes(processes)
        bottlenecks = await analyze_cpu_bottlenecks()
        gpu_roi = await calculate_gpu_roi()

    # Build report
    report_lines = [
        "# System Optimization Report",
        "",
        f"Generated: {json.dumps(input_data.get('timestamp') if input_data else 'now')}",
        "",
        "## System Resources",
        "",
        f"**CPU**: {resources['cpu']['percent_used']:.1f}% used, {resources['cpu']['count']} cores",
        f"**Memory**: {resources['memory']['used_gb']:.1f}GB / {resources['memory']['total_gb']:.1f}GB ({resources['memory']['percent_used']:.1f}% used)",
        f"**Disk**: {resources['disk']['used_gb']:.1f}GB / {resources['disk']['total_gb']:.1f}GB ({resources['disk']['percent_used']:.1f}% used)",
        "",
        "## Top Resource Consumers",
        ""
    ]

    for i, proc in enumerate(processes["processes"][:5], 1):
        report_lines.append(f"{i}. **{proc['name']}** (PID {proc['pid']}): {proc['cpu_percent']:.1f}% CPU, {proc['memory_percent']:.1f}% RAM")

    report_lines.extend([
        "",
        "## Killable Processes",
        f"Found {killable['killable_count']} killable processes",
        ""
    ])

    for proc in killable["killable_processes"][:5]:
        report_lines.append(f"- **{proc['name']}** (PID {proc['pid']}): {proc['reason']}")

    report_lines.extend([
        "",
        "## CPU Bottlenecks",
        f"Found {len(bottlenecks['bottlenecks'])} bottlenecks",
        ""
    ])

    for bn in bottlenecks["bottlenecks"]:
        report_lines.append(f"- **{bn['type']}** ({bn['severity']}): {bn['description']}")

    report_lines.extend([
        "",
        "## GPU ROI Analysis",
        "",
        f"**Current CPU execution**: {gpu_roi['cpu_execution']['total_time_hours']:.1f}hrs, ${gpu_roi['cpu_execution']['total_cost']:.2f}",
        "",
        "**GPU Options**:"
    ])

    for key, option in gpu_roi["gpu_options"].items():
        report_lines.append(f"- **{option['name']}**: {option['total_time_hours']:.1f}hrs, ${option['total_cost']:.2f} (saves ${option['cost_saved']:.2f}, {option['speedup']}x faster)")

    report_lines.extend([
        "",
        f"**Recommendation**: {gpu_roi['recommendation']['provider']} - {gpu_roi['recommendation']['reason']}",
        "",
        "## Action Items",
        "",
        "1. **Immediate**: Kill resource-hogging processes to free compute",
        f"2. **Short-term**: Deploy to {gpu_roi['recommendation']['provider']} for evaluation",
        "3. **Long-term**: Implement hybrid CPU/GPU architecture for cost optimization"
    ])

    report = "\n".join(report_lines)

    return {
        "task": "generate_optimization_report",
        "status": "success",
        "report": report,
        "summary": {
            "cpu_available": resources["cpu"]["percent_available"],
            "memory_available_gb": resources["memory"]["available_gb"],
            "killable_processes": killable["killable_count"],
            "recommended_gpu": gpu_roi["recommendation"]["provider"],
            "gpu_savings": gpu_roi["recommendation"]["savings"],
            "gpu_speedup": gpu_roi["recommendation"]["speedup"]
        }
    }


async def save_optimization_report(input_data: Any = None) -> Dict[str, Any]:
    """Save optimization report to file."""
    if not input_data or "report" not in input_data:
        report_data = await generate_optimization_report()
        report = report_data["report"]
    else:
        report = input_data["report"]

    output_file = "docs/SYSTEM_OPTIMIZATION_REPORT.md"

    with open(output_file, 'w') as f:
        f.write(report)

    return {
        "task": "save_optimization_report",
        "status": "success",
        "file": output_file,
        "size_bytes": len(report)
    }
