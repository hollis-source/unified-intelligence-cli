#!/usr/bin/env python3
"""
Prometheus textfile collector writer for llama-server.
It tries /metrics; if unavailable, it probes /completion with small n_predict
and writes a few metrics to a textfile (for node_exporter's textfile collector).
"""
from __future__ import annotations
import argparse
import json
import time
import urllib.request
from pathlib import Path


def get(url: str, timeout: float = 5.0) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8")
    except Exception:
        return 0, ""


def post(url: str, payload: dict, timeout: float = 10.0) -> tuple[int, dict]:
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except Exception:
        return 0, {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8080", help="Base URL of llama-server")
    ap.add_argument("--out", default="/var/lib/node_exporter/textfile_collector/llama.prom")
    ap.add_argument("--prompt", default="ping")
    ap.add_argument("--n-predict", type=int, default=8)
    args = ap.parse_args()

    metrics = {}
    # Try /metrics pass-through
    status, body = get(f"{args.url}/metrics")
    if status == 200 and "# HELP" in body:
        # Assume server exposes Prometheus; write as-is
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(body)
        return

    # Fallback: try health
    status, _ = get(f"{args.url}/health")
    metrics["llama_up"] = 1 if status == 200 else 0

    # Probe a tiny completion to estimate tokens/sec
    if metrics["llama_up"]:
        st, res = post(f"{args.url}/completion", {"prompt": args.prompt, "n_predict": args.n_predict, "stream": False, "temperature": 0})
        tps = None
        if isinstance(res, dict):
            timings = res.get("timings") or {}
            tps = timings.get("predicted_per_second") or timings.get("generation_per_second")
        metrics["llama_tokens_per_second"] = float(tps) if tps else 0.0
    # Write textfile
    lines = [f"# HELP llama_up 1 if llama-server healthy\n# TYPE llama_up gauge\nllama_up {metrics.get('llama_up', 0)}\n"]
    if "llama_tokens_per_second" in metrics:
        lines.append("# HELP llama_tokens_per_second Approx tokens/sec from probe\n# TYPE llama_tokens_per_second gauge\n")
        lines.append(f"llama_tokens_per_second {metrics['llama_tokens_per_second']}\n")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("".join(lines))


if __name__ == "__main__":
    main()

