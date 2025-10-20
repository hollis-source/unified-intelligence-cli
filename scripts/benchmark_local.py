#!/usr/bin/env python3
import argparse, time, requests, json, sys, os
from urllib.parse import urljoin

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

def ttft_ms(endpoint: str, model: str, prompt: str, max_tokens: int = 256) -> int:
    headers = {'Content-Type': 'application/json'}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens, "temperature": 0.2, "stream": True}
    s = time.time()
    r = requests.post(urljoin(endpoint, '/chat/completions'), headers=headers, json=payload, stream=True, timeout=600)
    first = None
    for line in r.iter_lines():
        if not line: continue
        if line.startswith(b'data: '):
            first = time.time(); break
    if first is None:
        first = time.time()
    return int((first - s) * 1000)

def tokens_and_total_ms(endpoint: str, model: str, prompt: str, max_tokens: int = 256):
    headers = {'Content-Type': 'application/json'}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens, "temperature": 0.2}
    s = time.time()
    r = requests.post(urljoin(endpoint, '/chat/completions'), headers=headers, json=payload, timeout=600)
    el = int((time.time() - s) * 1000)
    j = r.json()
    usage = j.get('usage') or {}
    ct = usage.get('completion_tokens') or 0
    return ct, el

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--endpoint', default='http://localhost:8080/v1')
    ap.add_argument('--label', default='run')
    args = ap.parse_args()

    small = 'Summarize in one paragraph the purpose of a unit test. Keep it concise.'
    medium = 'You are refactoring a medium-size Python module. In 200-400 words, explain a safe plan to extract interfaces, add unit tests, improve dependency injection, and add structured logs with correlation IDs. Include short code examples where helpful.'

    model = get_model(args.endpoint)
    out_csv = 'metrics/llama_bench.csv'
    os.makedirs('metrics', exist_ok=True)
    def do_case(name, prompt):
        ttft = ttft_ms(args.endpoint, model, prompt)
        tokens, total = tokens_and_total_ms(args.endpoint, model, prompt)
        gen_ms = max(1, total - ttft)
        tps = round((tokens / (gen_ms / 1000.0)) if tokens > 0 else 0.0, 2)
        print(f"{name}: TTFT={ttft}ms, total={total}ms, tokens={tokens}, tok/s={tps}")
        with open(out_csv, 'a') as f:
            f.write(f"{time.strftime('%F_%T')},{args.label},{args.endpoint},{model},{name},{ttft},{total},{tokens},{tps}\n")
    print(f"Benchmarking {args.label} on {args.endpoint} (model={model})")
    do_case('small', small)
    do_case('medium', medium)

if __name__ == '__main__':
    main()

