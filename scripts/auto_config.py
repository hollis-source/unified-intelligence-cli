#!/usr/bin/env python3
"""
Auto-config generator for llama.cpp llama-server flags based on detected hardware.
Heuristics focus on CPU-only high-core Linux servers.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List


def load_hw(path: str | None) -> Dict[str, Any]:
    if path and Path(path).exists():
        return json.loads(Path(path).read_text())
    # Fallback: import sibling detector
    import subprocess, sys
    here = Path(__file__).resolve().parent
    data = subprocess.check_output(["python3", str(here / "hw_detect.py")], text=True)
    return json.loads(data)


def bytes_human(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def recommend_instances(hw: Dict[str, Any], mode: str | None) -> List[Dict[str, Any]]:
    cpu = hw.get("cpu", {})
    numa = hw.get("numa", {})
    mem_total_kb = hw.get("memory", {}).get("mem_total_kb", 0)
    nodes = sorted(numa.get("nodes", []), key=lambda x: x.get("id", 0))

    # Decide instances: single vs per-NUMA vs interleave
    if mode == "single" or not nodes or len(nodes) <= 1:
        return [{"numa_nodes": [n.get("id", 0) for n in nodes] or [0], "cpus": None, "mem_kb": mem_total_kb}]
    if mode == "dual" and len(nodes) >= 2:
        return [{"numa_nodes": [n["id"]], "cpus": n.get("cpus"), "mem_kb": n.get("mem_total_kb")} for n in nodes]
    if mode == "interleave":
        return [{"numa_nodes": [n.get("id", 0) for n in nodes], "cpus": None, "mem_kb": mem_total_kb, "interleave": True}]

    # Auto: if nodes are balanced and each can hold model, prefer per-node instances
    return [{"numa_nodes": [n["id"]], "cpus": n.get("cpus"), "mem_kb": n.get("mem_total_kb")} for n in nodes]


def compute_flags(hw: Dict[str, Any], model_path: Path, target: str, instance: Dict[str, Any]) -> Dict[str, Any]:
    cpu = hw.get("cpu", {})
    sockets = int(cpu.get("sockets", 1) or 1)
    tpc = int(cpu.get("threads_per_core", 1) or 1)
    cores_per_socket = int(cpu.get("cores_per_socket", 1) or 1)
    physical_total = int(cpu.get("physical_cores", cores_per_socket * sockets))

    cpus = instance.get("cpus") or []
    if cpus:
        # Approx cores in this instance by logical->physical conversion using tpc
        phys_cores = max(1, len(cpus) // max(1, tpc))
    else:
        # Single or interleave: use all physical cores
        phys_cores = max(1, physical_total)

    # Threads: favor physical cores; keep 1-2 cores free for system
    threads = max(4, phys_cores - (2 if phys_cores > 32 else 1))

    # Batch threads: a small fraction of threads; bound to 2..8 typically
    threads_batch = max(2, min(8, threads // 4))

    # Parallel sequences: latency target -> 1, throughput -> scale gently with cores
    if target == "latency":
        parallel = 1
    else:
        parallel = max(1, min(8, threads // 12))

    # Memory-driven context decisions
    model_size = model_path.stat().st_size  # bytes
    avail_kb = int(instance.get("mem_kb") or hw.get("memory", {}).get("mem_total_kb", 0))
    # Reserve ~20% headroom and model_size; assume kv cache budget ~10-30 GB for large ctx
    headroom = int(avail_kb * 0.2) * 1024
    avail_bytes = max(0, avail_kb * 1024 - headroom - int(model_size * 1.1))
    if avail_bytes > 22 * 1024**3:
        ctx = 16384
    elif avail_bytes > 10 * 1024**3:
        ctx = 8192
    else:
        ctx = 4096

    # Batch sizes: keep ubatch within LLC; default conservative
    l3_kb = int(cpu.get("l3_kb") or 0)
    if l3_kb >= 128 * 1024:
        ubatch = 256
    elif l3_kb >= 64 * 1024:
        ubatch = 128
    else:
        ubatch = 64
    b = min(ctx, max(256, ubatch * 4))

    return {
        "threads": threads,
        "threads_batch": threads_batch,
        "parallel": parallel,
        "ctx": ctx,
        "batch": b,
        "ubatch": ubatch,
        "notes": [
            f"phys_cores_estimate={phys_cores}",
            f"model_size={bytes_human(model_size)}",
            f"avail_for_kv={bytes_human(avail_bytes)}",
        ],
    }


def build_command(flags: Dict[str, Any], model_path: Path, host: str, port: int, extra: List[str]) -> str:
    parts = [
        "llama-server",
        "-m", str(model_path),
        "-t", str(flags["threads"]),
        "--threads-batch", str(flags["threads_batch"]),
        "--parallel", str(flags["parallel"]),
        "-c", str(flags["ctx"]),
        "-b", str(flags["batch"]),
        "--ubatch", str(flags["ubatch"]),
        "--host", host,
        "--port", str(port),
    ] + extra
    return " ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="Path to GGUF model file")
    ap.add_argument("--hardware-json", help="Path to JSON from hw_detect.py (optional)")
    ap.add_argument("--target", choices=["latency", "throughput"], default="throughput")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--numa-mode", choices=["auto", "single", "dual", "interleave"], default="auto")
    ap.add_argument("--extra", nargs="*", default=["--no-warmup"])  # let warm path come from traffic
    ap.add_argument("-o", "--out", help="Write full recommendation JSON to path")
    args = ap.parse_args()

    hw = load_hw(args.hardware_json)
    instances = recommend_instances(hw, None if args.numa_mode == "auto" else args.numa_mode)

    model_path = Path(args.model).resolve()
    results: Dict[str, Any] = {
        "mode": args.numa_mode,
        "instances": [],
        "hardware": hw,
    }
    for inst in instances:
        flags = compute_flags(hw, model_path, args.target, inst)
        cmd = build_command(flags, model_path, args.host, args.port, args.extra)
        # Add NUMA binding hints
        numa_nodes = inst.get("numa_nodes", [])
        if inst.get("interleave"):
            cmd = f"numactl --interleave={' '.join(map(str, numa_nodes))} " + cmd
        elif len(numa_nodes) == 1:
            cmd = f"numactl --cpunodebind={numa_nodes[0]} --membind={numa_nodes[0]} " + cmd
        else:
            # multi-node single instance; let kernel balance
            pass
        results["instances"].append({
            "numa_nodes": numa_nodes,
            "flags": flags,
            "command": cmd,
        })

    out_json = json.dumps(results, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(out_json + "\n")
    print(out_json)


if __name__ == "__main__":
    main()

