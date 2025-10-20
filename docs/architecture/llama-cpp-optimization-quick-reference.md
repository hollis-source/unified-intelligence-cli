# llama.cpp CPU Optimization Quick Reference

**Target**: IBM Granite 32B GGUF on resource-rich servers (1TB+ RAM, high core count)

---

## Critical Architectural Decisions

### 1. Thread Count Formula

**DO NOT use all CPU cores!** Memory bandwidth saturates long before CPU cores.

```
Optimal Threads = 16-32 for most systems
(Regardless of whether you have 32, 64, or 128 cores)
```

**Empirical Guidelines**:
- Single-socket DDR4 (~100 GB/s): **8-16 threads**
- Single-socket DDR5 (~200 GB/s): **16-32 threads**  
- Dual-socket DDR5 (~400 GB/s): **32-64 threads** (16-32 per NUMA node)

**How to find your optimal**:
```bash
for t in 8 16 24 32 48 64; do
  echo "Testing $t threads..."
  llama-cli --threads $t --model granite-32b-q4.gguf \
    --prompt "Explain quantum computing" --n-predict 100
done
# Use thread count where tokens/s plateaus
```

---

### 2. NUMA Configuration Decision Tree

```
Single Socket? → NUMA OFF (numactl not needed)

Dual Socket + Single Model? → NUMA Interleave
  numactl --interleave=all llama-server ...

Dual Socket + Multiple Models? → NUMA Pinning
  numactl --cpunodebind=0 --membind=0 llama-server --port 8001 ...
  numactl --cpunodebind=1 --membind=1 llama-server --port 8002 ...
```

**Why**: Cross-NUMA memory access is 1.3-2.5× slower than local access.

---

### 3. mlock Policy

| Available RAM | Model Size | Use mlock? |
|---------------|------------|------------|
| > 4× model size | Any | **YES** (`--mlock`) |
| 2-4× model size | Any | **MAYBE** (test with monitoring) |
| < 2× model size | Any | **NO** (`--no-mlock`) |

**Example**: 
- 1TB RAM + 18GB Q4 model = 55× → **Use mlock**
- 64GB RAM + 18GB Q4 model = 3.5× → **Don't use mlock**

---

### 4. Context Window Sizing

**KV Cache Memory Formula**:
```
Granite 32B KV Cache:
- 8K context, FP16: ~12 GB
- 16K context, FP16: ~24 GB
- 32K context, FP16: ~48 GB

Use Q8 KV cache to cut this in half!
```

**Decision Matrix**:

| Available RAM | Quantization | Max Safe Context | KV Cache Type |
|---------------|--------------|------------------|---------------|
| 1TB | Q4 (18GB) | 128K | FP16 |
| 512GB | Q5 (22GB) | 64K | FP16 |
| 256GB | Q4 (18GB) | 32K | Q8 |
| 128GB | Q4 (18GB) | 16K | Q8 |

**Command**:
```bash
# Use Q8 KV cache to save 50% memory
llama-server --cache-type-k q8_0 --cache-type-v q8_0 --ctx-size 32768
```

---

### 5. Multi-Model Architecture

**For 3+ concurrent models, use process isolation**:

```bash
# Model 1: Fast (Q4) on NUMA 0
numactl --cpunodebind=0 --membind=0 \
  llama-server --model granite-32b-q4.gguf --threads 20 \
  --ctx-size 16384 --port 8001 &

# Model 2: Balanced (Q5) on NUMA 0  
numactl --cpunodebind=0 --membind=0 \
  llama-server --model granite-32b-q5.gguf --threads 20 \
  --ctx-size 16384 --port 8002 &

# Model 3: Quality (Q8) on NUMA 1
numactl --cpunodebind=1 --membind=1 \
  llama-server --model granite-32b-q8.gguf --threads 20 \
  --ctx-size 8192 --port 8003 &
```

**Load balancer** (nginx):
```nginx
upstream llama_backends {
    server 127.0.0.1:8001 weight=6;  # Q4 - 60% traffic
    server 127.0.0.1:8002 weight=3;  # Q5 - 30% traffic
    server 127.0.0.1:8003 weight=1;  # Q8 - 10% traffic
}
```

---

## Hardware Detection Commands

```bash
# 1. View complete topology
lstopo --of console

# 2. Check NUMA configuration
numactl --hardware

# 3. Measure NUMA latency
numactl --latency

# 4. CPU summary
lscpu | grep -E "Socket|Core|Thread|NUMA"

# 5. Memory bandwidth (install STREAM benchmark)
./stream

# 6. Monitor NUMA balance during inference
watch -n 1 numastat

# 7. Check for swapping (should be 0)
vmstat 1
```

---

## Performance Monitoring

**During inference, monitor**:

```bash
# Memory bandwidth utilization (should be 70-90%)
perf stat -e cycles,instructions,cache-misses,mem_load_retired.l3_miss \
  llama-cli --model granite-32b-q4.gguf --prompt "test" --n-predict 100

# NUMA node usage (should be balanced if using interleave)
numastat -c llama-server

# No swapping (si/so should be 0)
vmstat 1

# Memory usage
free -h
```

**Red flags**:
- ❌ Swap usage > 0 → Reduce context size or use lower quantization
- ❌ CPU usage < 30% but tokens/s not increasing → Memory bandwidth saturated
- ❌ NUMA imbalance (90% on one node, 10% on other) → Fix pinning
- ❌ Cache miss rate > 10% → Reduce thread count

---

## Memory Budget Calculator

**For 1TB RAM system running 3× Granite 32B models**:

| Component | Q4 Model | Q5 Model | Q8 Model | Total |
|-----------|----------|----------|----------|-------|
| Model weights | 18 GB | 22 GB | 35 GB | 75 GB |
| KV cache (16K, Q8) | 12 GB | 12 GB | 6 GB | 30 GB |
| Per-model total | 30 GB | 34 GB | 41 GB | **105 GB** |
| OS reserved | - | - | - | 100 GB |
| **Available** | - | - | - | **819 GB** |

**Headroom**: 819 GB available for additional models or larger contexts.

---

## Common Pitfalls

### ❌ Using all CPU cores
```bash
# BAD: Using all 128 cores
llama-server --threads 128  # Memory bandwidth saturated at ~32 threads!
```

### ✅ Using optimal thread count
```bash
# GOOD: Using bandwidth-optimal thread count
llama-server --threads 24
```

---

### ❌ Ignoring NUMA on dual-socket
```bash
# BAD: Random NUMA allocation
llama-server --model granite-32b-q4.gguf
```

### ✅ NUMA-aware allocation
```bash
# GOOD: Pinned to NUMA node
numactl --cpunodebind=0 --membind=0 llama-server --model granite-32b-q4.gguf
```

---

### ❌ Using FP16 KV cache when RAM-constrained
```bash
# BAD: 48 GB KV cache for 32K context
llama-server --ctx-size 32768  # Default FP16 KV cache
```

### ✅ Using Q8 KV cache
```bash
# GOOD: 24 GB KV cache for 32K context (50% savings)
llama-server --ctx-size 32768 --cache-type-k q8_0 --cache-type-v q8_0
```

---

## Quantization Selection Guide

| Quantization | Size (32B) | Quality | Speed | Use Case |
|--------------|------------|---------|-------|----------|
| **Q4_K_M** | 18 GB | Good | Fastest | High-throughput, latency-sensitive |
| **Q5_K_M** | 22 GB | Better | Fast | Balanced quality/speed |
| **Q6_K** | 26 GB | Very Good | Medium | Quality-focused |
| **Q8_0** | 35 GB | Excellent | Slower | Maximum quality, research |

**Recommendation for 1TB RAM**:
- Run **2× Q4** + **1× Q5** + **1× Q8** simultaneously
- Route based on user tier or quality requirements

---

## Health Check Configuration

**systemd service** with auto-restart:

```ini
[Unit]
Description=llama.cpp server (Q4)
After=network.target

[Service]
Type=simple
User=llama
WorkingDirectory=/opt/llama.cpp
ExecStart=/usr/bin/numactl --cpunodebind=0 --membind=0 \
  /opt/llama.cpp/llama-server \
  --model /models/granite-32b-q4.gguf \
  --threads 20 \
  --ctx-size 16384 \
  --mlock \
  --port 8001
Restart=on-failure
RestartSec=10s
MemoryMax=50G
OOMPolicy=kill

[Install]
WantedBy=multi-user.target
```

**nginx health check**:
```nginx
upstream llama_q4 {
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
    
    # Health check (requires nginx-plus or custom module)
    check interval=10000 rise=2 fall=3 timeout=5000 type=http;
    check_http_send "GET /health HTTP/1.0\r\n\r\n";
    check_http_expect_alive http_2xx http_3xx;
}
```

---

## Troubleshooting Guide

### Problem: Low tokens/s despite high core count

**Diagnosis**:
```bash
# Check memory bandwidth utilization
perf stat -e mem_load_retired.l3_miss llama-cli ...
```

**Solution**: Reduce thread count to bandwidth saturation point (16-32).

---

### Problem: High latency on dual-socket system

**Diagnosis**:
```bash
# Check NUMA node usage
numastat -c llama-server
```

**Solution**: Pin process to single NUMA node or use interleave policy.

---

### Problem: OOM kills despite sufficient RAM

**Diagnosis**:
```bash
# Check actual memory usage
ps aux | grep llama-server
dmesg | grep -i oom
```

**Solution**: 
1. Reduce context size (`--ctx-size`)
2. Use Q8 KV cache instead of FP16
3. Disable mlock if enabled
4. Lower quantization (Q8 → Q5 → Q4)

---

### Problem: Swapping occurring

**Diagnosis**:
```bash
vmstat 1  # Watch si/so columns
```

**Solution**:
1. Enable mlock to prevent swapping
2. Reduce number of concurrent models
3. Lower context size
4. Add more RAM or use swap on NVMe

---

## Benchmark Baseline

**Expected performance** (Granite 32B Q4, optimal config):

| System | Threads | Prompt Tokens/s | Generation Tokens/s |
|--------|---------|-----------------|---------------------|
| Single-socket, DDR4 | 16 | 800-1200 | 15-25 |
| Single-socket, DDR5 | 24 | 1500-2500 | 25-40 |
| Dual-socket, DDR5 | 32 | 2500-4000 | 40-60 |

**If your numbers are significantly lower**:
1. Check thread count (reduce if too high)
2. Verify NUMA configuration
3. Monitor memory bandwidth saturation
4. Check for swapping
5. Verify no thermal throttling

---

## Quick Start Template

```bash
#!/bin/bash
# Granite 32B Q4 on 1TB RAM, dual-socket system

# Detect optimal thread count
THREADS=24  # Adjust based on bandwidth testing

# Detect NUMA nodes
NUMA_NODES=$(numactl --hardware | grep "available:" | awk '{print $2}')

if [ "$NUMA_NODES" -gt 1 ]; then
    # Dual-socket: pin to NUMA 0
    NUMA_CMD="numactl --cpunodebind=0 --membind=0"
else
    # Single-socket: no NUMA needed
    NUMA_CMD=""
fi

# Launch server
$NUMA_CMD llama-server \
    --model /models/granite-32b-q4.gguf \
    --threads $THREADS \
    --ctx-size 32768 \
    --cache-type-k q8_0 \
    --cache-type-v q8_0 \
    --mlock \
    --parallel 4 \
    --port 8080 \
    --verbose
```

---

## Key Metrics to Track

| Metric | Target | Tool |
|--------|--------|------|
| Tokens/s (generation) | 20-60 | llama-server logs |
| Memory bandwidth utilization | 70-90% | `perf`, `likwid-perfctr` |
| CPU utilization | 40-70% | `htop`, `top` |
| NUMA balance | 50/50 (interleave) | `numastat` |
| Swap usage | 0 | `free -h`, `vmstat` |
| Cache miss rate | <5% | `perf stat` |
| P95 latency | <500ms | Application logs |

---

**For full architectural details, see**: `llama-cpp-cpu-optimization-architecture.md`

