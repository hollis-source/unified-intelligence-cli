#!/usr/bin/env python3
"""
Hardware detection for CPU/NUMA/memory/cache on Linux hosts.
Outputs a single JSON document to stdout (or -o path).
Gracefully degrades if dmidecode or numactl are unavailable.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List


def run(cmd: List[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return ""


def parse_lscpu() -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    out = run(["lscpu", "-J"]).strip()
    if out:
        try:
            j = json.loads(out)
            kv = {row["field"].strip(":"): row["data"] for row in j.get("lscpu", [])}
            data["vendor"] = kv.get("Vendor ID")
            data["model_name"] = kv.get("Model name")
            data["architecture"] = kv.get("Architecture")
            data["sockets"] = int(kv.get("Socket(s)", 1) or 1)
            data["cores_per_socket"] = int(kv.get("Core(s) per socket", 1) or 1)
            data["threads_per_core"] = int(kv.get("Thread(s) per core", 1) or 1)
            data["logical_cores"] = int(kv.get("CPU(s)", 1) or 1)
            # caches as kB
            def to_kb(v: str | None) -> int | None:
                if not v:
                    return None
                m = re.match(r"(\d+)\s*(K|M|G)i?B", v)
                if not m:
                    return None
                n = int(m.group(1))
                unit = m.group(2)
                return n if unit == "K" else (n * 1024 if unit == "M" else n * 1024 * 1024)

            data["l1d_kb"] = to_kb(kv.get("L1d cache"))
            data["l1i_kb"] = to_kb(kv.get("L1i cache"))
            data["l2_kb"] = to_kb(kv.get("L2 cache"))
            data["l3_kb"] = to_kb(kv.get("L3 cache"))
        except Exception:
            pass
    # Flags
    flags = []
    cpuinfo = Path("/proc/cpuinfo").read_text(errors="ignore")
    m = re.search(r"^flags\s*:\s*(.+)$", cpuinfo, re.M)
    if m:
        flags = m.group(1).split()
    data["flags"] = flags
    # physical cores estimate
    phys = data.get("sockets", 1) * data.get("cores_per_socket", 1)
    data["physical_cores"] = phys
    return data


def parse_numactl() -> Dict[str, Any]:
    res: Dict[str, Any] = {"nodes": []}
    out = run(["numactl", "-H"]).strip()
    if not out:
        return res
    node_re = re.compile(r"node\s+(\d+)\s+cpus:\s+([0-9\s]+)")
    size_re = re.compile(r"node\s+(\d+)\s+size:\s+([0-9.]+)\s*(\wB)")
    # Build maps
    cpus_map: Dict[int, List[int]] = {}
    mem_map: Dict[int, int] = {}
    for line in out.splitlines():
        m = node_re.search(line)
        if m:
            nid = int(m.group(1))
            cpus = [int(x) for x in m.group(2).split() if x.isdigit()]
            cpus_map[nid] = cpus
        m2 = size_re.search(line)
        if m2:
            nid = int(m2.group(1))
            val = float(m2.group(2))
            unit = m2.group(3)
            kb = int(val * (1024 if unit == "kB" else (1024 * 1024 if unit == "MB" else 1024 * 1024 * 1024)))
            mem_map[nid] = kb
    for nid in sorted(set(cpus_map.keys()) | set(mem_map.keys())):
        res["nodes"].append({"id": nid, "cpus": cpus_map.get(nid, []), "mem_total_kb": mem_map.get(nid)})
    return res


def parse_meminfo() -> Dict[str, int]:
    info: Dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            m = re.search(r"(\d+)", v)
            if m:
                info[k.strip()] = int(m.group(1))  # kB
    return {"mem_total_kb": info.get("MemTotal", 0), "swap_total_kb": info.get("SwapTotal", 0)}


def parse_memory_channels() -> int | None:
    # dmidecode often requires root; best-effort parsing of channel labels
    if not shutil.which("dmidecode"):
        return None
    out = run(["dmidecode", "-t", "memory"]).lower()
    if not out:
        return None
    # Look for strings like "channel a", "channel-b", etc.
    channels = set(re.findall(r"channel\s*([a-z])", out))
    return len(channels) or None


def build_output() -> Dict[str, Any]:
    cpu = parse_lscpu()
    numa = parse_numactl()
    mem = parse_meminfo()
    channels = parse_memory_channels()
    out: Dict[str, Any] = {
        "cpu": cpu,
        "numa": numa,
        "memory": {**mem, "channels_per_socket": channels},
        "host": {"hostname": os.uname().nodename},
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", help="Write JSON to path instead of stdout")
    args = ap.parse_args()
    data = build_output()
    js = json.dumps(data, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(js + "\n")
    else:
        print(js)


if __name__ == "__main__":
    main()

