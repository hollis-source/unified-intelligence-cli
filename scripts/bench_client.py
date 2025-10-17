#!/usr/bin/env python3
"""
Minimal benchmarking client for llama.cpp llama-server.
Sends concurrent /completion requests and reports tokens/sec and latency p50/p95/p99.
"""
from __future__ import annotations
import argparse
import concurrent.futures as cf
import json
import statistics as stats
import time
import urllib.request


def post_json(url: str, payload: dict, timeout: float = 120.0) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def one_call(base_url: str, prompt: str, n_predict: int) -> dict:
    t0 = time.perf_counter()
    res = post_json(f"{base_url}/completion", {
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": 0,
        "stream": False,
    })
    t1 = time.perf_counter()
    latency = t1 - t0
    tokens = n_predict
    tps = None
    timings = res.get("timings") or {}
    # Try server-provided tokens/sec
    if isinstance(timings, dict):
        tps = timings.get("predicted_per_second") or timings.get("generation_per_second")
    if not tps:
        tps = tokens / latency if latency > 0 else 0.0
    return {"latency_s": latency, "tokens_sec": float(tps)}


def run_bench(base_url: str, prompt: str, n_predict: int, requests: int, concurrency: int) -> dict:
    results = []
    with cf.ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = [ex.submit(one_call, base_url, prompt, n_predict) for _ in range(requests)]
        for f in cf.as_completed(futs):
            try:
                results.append(f.result())
            except Exception as e:
                results.append({"error": str(e)})
    ok = [r for r in results if "error" not in r]
    lat = [r["latency_s"] for r in ok]
    tps = [r["tokens_sec"] for r in ok]
    pct = lambda arr, p: float(stats.quantiles(arr, n=100)[p-1]) if arr else None
    out = {
        "requests": requests,
        "concurrency": concurrency,
        "n_predict": n_predict,
        "ok": len(ok),
        "errors": len(results) - len(ok),
        "latency_s": {
            "p50": pct(lat, 50),
            "p95": pct(lat, 95),
            "p99": pct(lat, 99),
            "avg": float(sum(lat)/len(lat)) if lat else None,
        },
        "tokens_sec": {
            "avg": float(sum(tps)/len(tps)) if tps else None,
            "p50": pct(tps, 50) if tps else None,
        },
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8080", help="Base URL of llama-server")
    ap.add_argument("--prompt", default="Write a haiku about CPUs.")
    ap.add_argument("--n-predict", type=int, default=128)
    ap.add_argument("--requests", type=int, default=50)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("-o", "--out-json", help="Write results JSON to path")
    args = ap.parse_args()

    res = run_bench(args.url, args.prompt, args.n_predict, args.requests, args.concurrency)
    js = json.dumps(res, indent=2)
    if args.out_json:
        with open(args.out_json, "w") as f:
            f.write(js + "\n")
    print(js)


if __name__ == "__main__":
    main()

