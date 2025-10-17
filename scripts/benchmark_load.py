#!/usr/bin/env python3
import argparse, threading, time, requests, json, os, statistics, sys, subprocess, shutil
from urllib.parse import urljoin, urlparse
from collections import deque

SMALL_PROMPT = 'Summarize in one paragraph the purpose of a unit test. Keep it concise.'
MEDIUM_PROMPT = 'You are refactoring a medium-size Python module. In 200-400 words, explain a safe plan to extract interfaces, add unit tests, improve dependency injection, and add structured logs with correlation IDs. Include short code examples where helpful.'


def get_model(endpoint: str) -> str:
    r = requests.get(urljoin(endpoint, '/models'), timeout=5)
    j = r.json()
    if 'data' in j and j['data']:
        m = j['data'][0]
        return m.get('id') or m.get('name')
    ms = j.get('models') or []
    if ms:
        m = ms[0]
        return m.get('id') or m.get('name') or m.get('model')
    raise RuntimeError('No model available')

def infer_quant_from_model(model: str) -> str:
    base = os.path.basename(model)
    for q in ('Q2_', 'Q3_', 'Q4_', 'Q5_', 'Q6_', 'Q8_'):
        if q in base:
            # return token + qualifier, e.g., Q5_K_M or Q8_0
            start = base.find(q)
            end = base.find('.gguf') if '.gguf' in base else len(base)
            return base[start:end]
    return 'unknown'

class WorkerStats:
    def __init__(self):
        self.recs = []  # (end_ts, ttft_ms or None, total_ms, completion_tokens or None, ok:bool)

    def add(self, end_ts, ttft_ms, total_ms, comp_tokens, ok):
        self.recs.append((end_ts, ttft_ms, total_ms, comp_tokens, ok))


def ttft_stream_request(endpoint, model, prompt, max_tokens=256, timeout=600):
    headers={'Content-Type':'application/json'}
    payload={"model":model,"messages":[{"role":"user","content":prompt}],"max_tokens":max_tokens,"temperature":0.2,"stream":True}
    s=time.time()
    r=requests.post(urljoin(endpoint,'/chat/completions'),headers=headers,json=payload,stream=True,timeout=timeout)
    first=None
    for line in r.iter_lines():
        if not line: continue
        if line.startswith(b'data: '):
            first=time.time(); break
    if first is None:
        first=time.time()
    # drain remainder
    for _ in r.iter_lines():
        pass
    end=time.time()
    return int((first-s)*1000), int((end-s)*1000)

def nonstream_request(endpoint, model, prompt, max_tokens=256, timeout=600):
    headers={'Content-Type':'application/json'}
    payload={"model":model,"messages":[{"role":"user","content":prompt}],"max_tokens":max_tokens,"temperature":0.2}
    s=time.time();
    r=requests.post(urljoin(endpoint,'/chat/completions'),headers=headers,json=payload,timeout=timeout)
    el=int((time.time()-s)*1000)
    ok = (r.status_code>=200 and r.status_code<300)
    ct=0
    try:
        j=r.json()
        usage=j.get('usage') or {}
        ct=int(usage.get('completion_tokens') or 0)
    except Exception:
        ok=False
    return el, ct, ok


def worker_loop(kind, endpoint, model, prompt, stop_ts, stats: WorkerStats):
    while time.time() < stop_ts:
        try:
            if kind=='ttft':
                ttft, total = ttft_stream_request(endpoint, model, prompt)
                stats.add(time.time(), ttft, total, None, True)
            else:
                total, ct, ok = nonstream_request(endpoint, model, prompt)
                stats.add(time.time(), None, total, ct, ok)
        except Exception:
            stats.add(time.time(), None, 0, 0, False)


def sample_server_proc(endpoint, warmup_end_ts, end_ts):
    # Try to find PID listening on port and sample ps %cpu and rss (KB)
    cpu_samples=[]; rss_samples=[]
    try:
        port=urlparse(endpoint).port or 80
        if shutil.which('lsof') is None:
            return None, None
        pid = subprocess.check_output(['bash','-lc', f"lsof -i :{port} -sTCP:LISTEN -t | head -n1"], text=True).strip()
        if not pid:
            return None, None
        # sample every 5s in steady window
        t=warmup_end_ts
        while t < end_ts:
            out = subprocess.check_output(['bash','-lc', f"ps -p {pid} -o %cpu=,rss="], text=True).strip()
            if out:
                parts=out.split()
                if len(parts)>=2:
                    cpu=float(parts[0]); rss_kb=float(parts[1])
                    cpu_samples.append(cpu); rss_samples.append(rss_kb/1024.0)
            time.sleep(5)
            t+=5
        if cpu_samples:
            return round(sum(cpu_samples)/len(cpu_samples),1), round(max(rss_samples),1)
        return None, None
    except Exception:
        return None, None


def run_level(endpoint, model, prompt, level, duration, warmup):
    start = time.time()
    stop  = start + duration
    warmup_end = start + warmup
    # Half workers measure TTFT (stream), half measure throughput (non-stream)
    n_ttft = max(1, level//2)
    n_thru = level - n_ttft
    workers=[]; stats=[]
    for _ in range(n_ttft):
        st=WorkerStats(); stats.append(('ttft', st))
        th=threading.Thread(target=worker_loop, args=('ttft', endpoint, model, prompt, stop, st), daemon=True)
        th.start(); workers.append(th)
    for _ in range(n_thru):
        st=WorkerStats(); stats.append(('thru', st))
        th=threading.Thread(target=worker_loop, args=('thru', endpoint, model, prompt, stop, st), daemon=True)
        th.start(); workers.append(th)
    # Optional process sampling
    cpu_pct, rss_mb = sample_server_proc(endpoint, warmup_end, stop)
    for th in workers:
        th.join()
    # Aggregate steady-state records
    ttfts=[]; totals=[]; comp_tokens=[]; ok_count=0; req_count=0
    for kind, st in stats:
        for (ts, ttft, total, ct, ok) in st.recs:
            if ts < warmup_end: # exclude warmup
                continue
            req_count += 1
            if ok: ok_count += 1
            if kind=='ttft' and ttft is not None:
                ttfts.append(ttft)
            if kind=='thru':
                totals.append(total)
                comp_tokens.append(ct or 0)
    err_rate = 0.0 if req_count==0 else round(100.0 * (req_count-ok_count)/req_count, 2)
    ttft_p50 = int(statistics.median(ttfts)) if ttfts else 0
    ttft_p95 = int(statistics.quantiles(ttfts, n=20)[18]) if len(ttfts)>=20 else (max(ttfts) if ttfts else 0)
    # Compute tokens/sec using p50 TTFT as estimate for non-stream requests
    # Use total time (includes TTFT) as conservative denominator under non-stream mode
    gen_ms = sum(max(1, t) for t in totals)
    tok_total = sum(comp_tokens)
    tok_s_agg = round((tok_total / (gen_ms/1000.0)) if gen_ms>0 else 0.0, 2)
    tok_s_avg = round((tok_s_agg / max(1, n_thru)), 2)
    req_s = round(req_count / max(1.0, (duration - warmup)), 2)
    return {
        'ttft_p50_ms': ttft_p50,
        'ttft_p95_ms': ttft_p95,
        'tok_s_avg': tok_s_avg,
        'tok_s_agg': tok_s_agg,
        'req_s': req_s,
        'err_rate': err_rate,
        'cpu_pct': cpu_pct,
        'rss_mb': rss_mb,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--endpoint', default='http://127.0.0.1:8080/v1')
    ap.add_argument('--label', default='load')
    ap.add_argument('--concurrency-levels', default='1,2,4,8,16,32')
    ap.add_argument('--duration-seconds', type=int, default=60)
    ap.add_argument('--warmup-seconds', type=int, default=10)
    ap.add_argument('--prompt-set', choices=['small','medium','both'], default='both')
    ap.add_argument('--csv', default='metrics/llama_bench_load.csv')
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.csv), exist_ok=True)
    endpoint = args.endpoint
    model = get_model(endpoint)
    quant = infer_quant_from_model(model)

    prompts = []
    if args.prompt_set in ('small','both'):
        prompts.append(('small', SMALL_PROMPT))
    if args.prompt_set in ('medium','both'):
        prompts.append(('medium', MEDIUM_PROMPT))

    levels = [int(x) for x in args.concurrency_levels.split(',') if x.strip()]
    # Write header if empty
    if not os.path.exists(args.csv) or os.path.getsize(args.csv)==0:
        with open(args.csv,'w') as f:
            f.write('date,label,endpoint,model,quant,prompt,level,ttft_p50_ms,ttft_p95_ms,req_s,tok_s_avg,tok_s_agg,err_rate,cpu_pct,rss_mb\n')

    for pname, prompt in prompts:
        for level in levels:
            print(f"Running {pname} @ concurrency {level} for {args.duration_seconds}s (warmup {args.warmup_seconds}s) ...")
            res = run_level(endpoint, model, prompt, level, args.duration_seconds, args.warmup_seconds)
            line = f"{time.strftime('%F_%T')},{args.label},{endpoint},{model},{quant},{pname},{level},{res['ttft_p50_ms']},{res['ttft_p95_ms']},{res['req_s']},{res['tok_s_avg']},{res['tok_s_agg']},{res['err_rate']},{res['cpu_pct'] or ''},{res['rss_mb'] or ''}\n"
            with open(args.csv,'a') as f:
                f.write(line)
            print(f" -> p50 TTFT={res['ttft_p50_ms']} ms, p95 TTFT={res['ttft_p95_ms']} ms, req/s={res['req_s']}, tok/s agg={res['tok_s_agg']}, err%={res['err_rate']}")

if __name__ == '__main__':
    main()

