# CPU Optimization Architecture for llama.cpp on Resource-Rich Servers

**Target Environment**: IBM Granite 32B GGUF models on servers with 1TB+ RAM, high core count  
**Document Type**: Architectural Design & Decision Matrices  
**Version**: 1.0  
**Date**: 2025-10-14

---

## Executive Summary

This document provides architectural guidance for optimizing llama.cpp CPU inference on resource-rich servers. It focuses on **decision frameworks** rather than implementation code, covering hardware topology detection, thread allocation strategies, memory configuration, and multi-model orchestration patterns.

**Key Architectural Principles**:
1. **Memory bandwidth is the primary bottleneck** for LLM inference (not compute)
2. **NUMA-aware allocation** critical for dual-socket systems
3. **Thread count optimization** based on memory bandwidth saturation, not core count
4. **Multi-model orchestration** requires careful resource partitioning

---

## 1. Hardware Topology Detection Strategy

### 1.1 Detection Approach

**Recommended Tools & Methods**:

| Tool | Purpose | Output | Priority |
|------|---------|--------|----------|
| `hwloc/lstopo` | Complete topology visualization | NUMA nodes, cache hierarchy, memory channels | **Primary** |
| `/sys/devices/system/cpu/` | Linux sysfs interface | Core topology, thread siblings | Secondary |
| `numactl --hardware` | NUMA configuration | Node distances, memory per node | **Primary** |
| `lscpu` | CPU summary | Sockets, cores/socket, threads/core | Tertiary |
| `dmidecode -t memory` | Memory configuration | Channel count, speed, capacity | Secondary |

**Detection Sequence**:
```
1. Detect socket count (single vs dual-socket)
2. Identify NUMA nodes per socket
3. Map cores to NUMA nodes
4. Determine cache hierarchy (L1/L2/L3 sizes and sharing)
5. Calculate memory bandwidth per NUMA node
6. Measure inter-NUMA latency (numactl --latency)
```

### 1.2 Decision Tree: NUMA Enabled vs Disabled

```
┌─────────────────────────────────────┐
│   System Configuration Detection    │
└──────────────┬──────────────────────┘
               │
               ▼
       ┌───────────────┐
       │ Socket Count? │
       └───┬───────┬───┘
           │       │
    Single │       │ Dual/Multi
           │       │
           ▼       ▼
    ┌──────────┐ ┌────────────────────┐
    │ NUMA OFF │ │ NUMA Configuration │
    │ (Simple) │ │ Decision Required  │
    └──────────┘ └─────────┬──────────┘
                           │
                           ▼
                  ┌────────────────────┐
                  │ Workload Pattern?  │
                  └──┬──────────────┬──┘
                     │              │
          Single     │              │ Multi-Model
          Model      │              │ Concurrent
                     │              │
                     ▼              ▼
            ┌─────────────┐  ┌──────────────┐
            │  NUMA ON    │  │   NUMA ON    │
            │ (Interleave)│  │ (Node Pinning)│
            └─────────────┘  └──────────────┘
```

**Decision Matrix**:

| Scenario | Socket Count | Workload | NUMA Policy | Rationale |
|----------|--------------|----------|-------------|-----------|
| **A** | Single | Any | Disabled | No cross-socket overhead |
| **B** | Dual | Single model | Interleave | Maximize bandwidth across nodes |
| **C** | Dual | Multi-model | Node pinning | Isolate models to NUMA nodes |
| **D** | Dual | Batch inference | Interleave | Distribute memory pressure |

### 1.3 Trade-offs: Single-Socket vs Dual-Socket

| Aspect | Single-Socket | Dual-Socket |
|--------|---------------|-------------|
| **Memory Bandwidth** | Limited to one socket's channels (e.g., 8-channel = ~200 GB/s) | Aggregate bandwidth (e.g., 16-channel = ~400 GB/s) |
| **Latency** | Uniform memory access | 1.3-2.5x latency for remote NUMA access |
| **Complexity** | Simple configuration | Requires NUMA-aware allocation |
| **Cost** | Lower | Higher (2x CPUs) |
| **Best For** | Models fitting in single-socket memory | Large models (32B+) or multi-model serving |

**Architectural Recommendation**:
- **Single-socket**: Granite 32B Q4/Q5 quantization (fits in 128-256GB)
- **Dual-socket**: Granite 32B Q8 + concurrent Q4 models, or multiple 32B instances

---

## 2. Thread Allocation Architecture

### 2.1 Mathematical Model for Optimal Thread Count

**Core Principle**: Thread count should saturate memory bandwidth, not CPU cores.

**Formula**:
```
Optimal_Threads = min(
    Physical_Cores,
    (Memory_Bandwidth_GB/s × 1024) / Model_Memory_Footprint_Per_Token_MB
)
```

**Example Calculation** (Granite 32B Q4_K_M):
- Memory bandwidth: 200 GB/s (single-socket DDR5-4800, 8-channel)
- Model size: 18 GB
- Context: 8K tokens
- KV cache per token: ~2 MB (32B model, Q4 quantization)

```
Bandwidth_per_thread = 2 MB/token × tokens/s
Threads_to_saturate = 200,000 MB/s ÷ 2 MB/token ÷ 20 tokens/s ≈ 5000 threads (unrealistic)

Practical limit: Memory bandwidth saturates at ~16-32 threads for LLM inference
```

**Empirical Guidelines** (from research):

| System Type | Memory Bandwidth | Recommended Threads | Notes |
|-------------|------------------|---------------------|-------|
| Single-socket DDR4 | ~100 GB/s | 8-16 | Bandwidth saturates early |
| Single-socket DDR5 | ~200 GB/s | 16-32 | Higher bandwidth allows more threads |
| Dual-socket DDR5 | ~400 GB/s | 32-64 (16-32 per NUMA) | Pin threads to NUMA nodes |
| High-core Xeon (44C+) | ~200 GB/s | 16-24 | More cores ≠ more threads |

### 2.2 Strategy for Avoiding Bandwidth Saturation

**Detection Method**:
```bash
# Benchmark memory bandwidth with varying thread counts
for threads in 4 8 16 24 32 48 64; do
    llama-cli --threads $threads --prompt "test" --n-predict 100 \
              --log-disable --model granite-32b-q4.gguf
done

# Monitor with:
# - `perf stat -e cycles,instructions,cache-misses`
# - `likwid-perfctr` for memory bandwidth
# - Watch for tokens/s plateau
```

**Saturation Indicators**:
- Tokens/s stops increasing with more threads
- CPU utilization < 50% but no performance gain
- High cache miss rate (>10%)
- Memory bandwidth utilization > 80%

**Mitigation Strategies**:

| Strategy | When to Use | Implementation |
|----------|-------------|----------------|
| **Reduce threads** | Bandwidth saturated | Set `--threads` to saturation point |
| **Batch processing** | Multiple requests | Use `--parallel` slots in llama-server |
| **NUMA interleaving** | Dual-socket | `numactl --interleave=all` |
| **Lower quantization** | Q8 → Q4 | Reduces memory traffic by 50% |

### 2.3 Design Pattern: Static vs Dynamic Thread Allocation

**Static Allocation** (Recommended for production):
```
Pros:
- Predictable performance
- No runtime overhead
- Easier to debug

Cons:
- Not adaptive to load
- May waste resources during idle

Use when: Running dedicated inference servers
```

**Dynamic Allocation** (Experimental):
```
Pros:
- Adapts to system load
- Better multi-tenancy

Cons:
- Complex implementation
- Potential performance variance
- Not natively supported in llama.cpp

Use when: Shared infrastructure with variable workloads
```

**Architectural Decision**: Use **static allocation** with per-model thread budgets.

---

## 3. Memory Configuration Strategy

### 3.1 mlock Policy Decision Matrix

**What is mlock?**: Locks model weights in RAM, preventing swap to disk.

| Scenario | Available RAM | Model Size | mlock Policy | Rationale |
|----------|---------------|------------|--------------|-----------|
| **A** | 1TB | 18 GB (Q4) | **Enable** | Plenty of headroom, avoid swap latency |
| **B** | 64 GB | 18 GB (Q4) | **Disable** | Risk of OOM, allow OS flexibility |
| **C** | 256 GB | 3× 18 GB models | **Enable** | Sufficient RAM, predictable performance |
| **D** | 128 GB | 35 GB (Q8) + OS | **Conditional** | Enable if RAM > 1.5× total model size |

**Command-line flags**:
```bash
# Enable mlock (recommended for 1TB RAM systems)
llama-cli --mlock --model granite-32b-q4.gguf

# Disable mlock (low-RAM systems)
llama-cli --no-mlock --model granite-32b-q4.gguf
```

**Trade-offs**:

| Aspect | mlock Enabled | mlock Disabled |
|--------|---------------|----------------|
| **Performance** | Consistent, no swap delays | Variable if swapping occurs |
| **Memory Pressure** | Higher (locked pages) | Lower (OS can reclaim) |
| **Startup Time** | Slower (pre-fault all pages) | Faster (lazy loading) |
| **Risk** | OOM if overcommitted | Swap thrashing if RAM low |

### 3.2 Context Window Sizing Strategy

**Formula**:
```
KV_Cache_Size_GB = (Layers × Hidden_Dim × 2 × Context_Length × Precision_Bytes) / 1e9

For Granite 32B:
- Layers: 60
- Hidden dim: 6144
- Precision: FP16 (2 bytes) or Q8 (1 byte)

KV_Cache_8K_FP16 = (60 × 6144 × 2 × 8192 × 2) / 1e9 ≈ 12 GB
KV_Cache_32K_FP16 = 48 GB
KV_Cache_8K_Q8 = 6 GB
```

**Decision Matrix**:

| Available RAM | Model Quant | Max Context | KV Cache Type | Total Memory |
|---------------|-------------|-------------|---------------|--------------|
| 1TB | Q4 (18GB) | 128K | FP16 | ~210 GB |
| 512GB | Q5 (22GB) | 64K | FP16 | ~120 GB |
| 256GB | Q4 (18GB) | 32K | Q8 | ~42 GB |
| 128GB | Q4 (18GB) | 16K | Q8 | ~30 GB |

**Architectural Recommendations**:
1. **Use Q8 KV cache** for memory-constrained systems (50% savings)
2. **Set context to power-of-2** for optimal memory alignment
3. **Reserve 20% RAM** for OS and overhead
4. **Monitor actual usage** with `--verbose` flag

### 3.3 KV Cache Allocation Across Multiple Models

**Scenario**: Running 3× Granite 32B models simultaneously on 1TB RAM system.

**Allocation Strategy**:

| Model Instance | Quantization | Context | KV Cache | Model Weights | Total per Instance |
|----------------|--------------|---------|----------|---------------|--------------------|
| Model A (Q4) | Q4_K_M | 16K | 12 GB (Q8) | 18 GB | 30 GB |
| Model B (Q5) | Q5_K_M | 16K | 12 GB (Q8) | 22 GB | 34 GB |
| Model C (Q8) | Q8_0 | 8K | 6 GB (Q8) | 35 GB | 41 GB |
| **Total** | - | - | **30 GB** | **75 GB** | **105 GB** |

**Remaining RAM**: 1024 - 105 - 100 (OS) = **819 GB available** for additional models or larger contexts.

**Design Pattern**:
```
Resource Pool Architecture:
┌─────────────────────────────────────┐
│     Total System RAM: 1TB           │
├─────────────────────────────────────┤
│ OS Reserved: 100 GB (10%)           │
├─────────────────────────────────────┤
│ Model Pool: 700 GB                  │
│  ├─ Model Weights: 400 GB           │
│  └─ KV Caches: 300 GB               │
├─────────────────────────────────────┤
│ Buffer/Overhead: 224 GB (22%)       │
└─────────────────────────────────────┘
```

---

## 4. Multi-Model Orchestration Architecture

### 4.1 Design Pattern for Running 3+ Models Simultaneously

**Architecture Options**:

#### Option A: Process-Level Isolation (Recommended)
```
┌──────────────────────────────────────────┐
│         Load Balancer (nginx/HAProxy)    │
└────┬──────────┬──────────┬───────────────┘
     │          │          │
     ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│ llama-  │ │ llama-  │ │ llama-  │
│ server  │ │ server  │ │ server  │
│ :8001   │ │ :8002   │ │ :8003   │
│ (Q4)    │ │ (Q5)    │ │ (Q8)    │
│ NUMA 0  │ │ NUMA 0  │ │ NUMA 1  │
└─────────┘ └─────────┘ └─────────┘
```

**Pros**:
- Process isolation (crash doesn't affect others)
- Independent scaling
- NUMA pinning per process
- Simple monitoring

**Cons**:
- Higher memory overhead (3× model loading)
- No weight sharing

#### Option B: Single Server with Parallel Slots
```
┌──────────────────────────────────────┐
│      llama-server --parallel 3       │
│  ┌────────┬────────┬────────┐        │
│  │ Slot 0 │ Slot 1 │ Slot 2 │        │
│  │ (Q4)   │ (Q4)   │ (Q4)   │        │
│  └────────┴────────┴────────┘        │
│      Shared Model Weights            │
└──────────────────────────────────────┘
```

**Pros**:
- Single model load (memory efficient)
- Built-in request queuing
- Simpler deployment

**Cons**:
- All requests use same quantization
- Single point of failure
- Limited to one model architecture

**Architectural Recommendation**: Use **Option A** for production (different quantizations), **Option B** for development/testing.

### 4.2 Load Balancing Strategy Across Quantization Levels

**Routing Decision Tree**:
```
Incoming Request
       │
       ▼
┌──────────────────┐
│ Latency SLA?     │
└──┬───────────┬───┘
   │           │
   │ <100ms    │ <500ms
   │           │
   ▼           ▼
┌──────┐   ┌──────┐
│ Q4   │   │ Q5   │
│ Fast │   │ Balanced│
└──────┘   └──────┘
               │
               │ Quality-critical
               ▼
           ┌──────┐
           │ Q8   │
           │ High │
           │Quality│
           └──────┘
```

**Load Balancing Algorithm**:

| Strategy | Use Case | Implementation |
|----------|----------|----------------|
| **Round-robin** | Equal priority requests | nginx `upstream` with `round_robin` |
| **Least connections** | Variable request duration | HAProxy `leastconn` |
| **Weighted** | Different model capacities | Q4:60%, Q5:30%, Q8:10% |
| **Quality-based** | User tier (free/premium) | Route premium → Q8, free → Q4 |

**Example nginx config**:
```nginx
upstream llama_backends {
    server 127.0.0.1:8001 weight=6;  # Q4 - fast
    server 127.0.0.1:8002 weight=3;  # Q5 - balanced
    server 127.0.0.1:8003 weight=1;  # Q8 - quality
}
```

### 4.3 Failover and Health Check Architecture

**Health Check Strategy**:

| Check Type | Endpoint | Frequency | Timeout | Action on Failure |
|------------|----------|-----------|---------|-------------------|
| **Liveness** | `/health` | 10s | 2s | Mark unhealthy, stop routing |
| **Readiness** | `/v1/models` | 30s | 5s | Remove from pool |
| **Performance** | `/v1/completions` (test) | 60s | 10s | Alert if slow |

**Failover Decision Matrix**:

| Failure Scenario | Detection | Response | Recovery |
|------------------|-----------|----------|----------|
| **Process crash** | Health check timeout | Route to healthy instances | Auto-restart with systemd |
| **OOM** | `dmesg` monitoring | Kill + restart with lower context | Reduce `--ctx-size` |
| **Slow responses** | P95 latency > threshold | Reduce weight in LB | Investigate (CPU/memory) |
| **NUMA imbalance** | `numastat` monitoring | Rebalance process pinning | Migrate to underutilized node |

**Monitoring Architecture**:
```
┌─────────────────────────────────────┐
│         Prometheus Exporter         │
│  ┌──────────────────────────────┐   │
│  │ Metrics:                     │   │
│  │ - llama_requests_total       │   │
│  │ - llama_tokens_per_second    │   │
│  │ - llama_memory_usage_bytes   │   │
│  │ - llama_numa_node_usage      │   │
│  └──────────────────────────────┘   │
└──────────────┬──────────────────────┘
               │
               ▼
        ┌─────────────┐
        │  Grafana    │
        │  Dashboard  │
        └─────────────┘
```

---

## 5. Implementation Checklist

### 5.1 Pre-Deployment

- [ ] Run `lstopo` and save topology diagram
- [ ] Benchmark memory bandwidth with STREAM
- [ ] Test thread scaling (4, 8, 16, 24, 32, 48, 64 threads)
- [ ] Measure NUMA latency with `numactl --latency`
- [ ] Calculate optimal context size for target RAM
- [ ] Decide on mlock policy based on available RAM

### 5.2 Configuration

- [ ] Set thread count to bandwidth saturation point
- [ ] Configure NUMA policy (interleave vs pinning)
- [ ] Set context window size with headroom
- [ ] Enable/disable mlock based on RAM
- [ ] Configure KV cache quantization (FP16 vs Q8)

### 5.3 Multi-Model Setup

- [ ] Allocate RAM budget per model instance
- [ ] Pin processes to NUMA nodes
- [ ] Configure load balancer with health checks
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Test failover scenarios

### 5.4 Validation

- [ ] Verify no swapping (`vmstat`, `free -h`)
- [ ] Check NUMA balance (`numastat`)
- [ ] Monitor memory bandwidth utilization
- [ ] Measure end-to-end latency (P50, P95, P99)
- [ ] Load test with concurrent requests

---

## 6. Reference Configurations

### 6.1 Single-Socket, 256GB RAM, 32-core

```bash
# Optimal for single Granite 32B Q5 model
llama-server \
  --model granite-32b-q5.gguf \
  --threads 24 \
  --ctx-size 32768 \
  --mlock \
  --parallel 4 \
  --port 8080
```

### 6.2 Dual-Socket, 1TB RAM, 88-core (2×44)

```bash
# Model 1: Q4 on NUMA 0
numactl --cpunodebind=0 --membind=0 \
  llama-server --model granite-32b-q4.gguf --threads 20 --ctx-size 16384 --port 8001 &

# Model 2: Q5 on NUMA 0
numactl --cpunodebind=0 --membind=0 \
  llama-server --model granite-32b-q5.gguf --threads 20 --ctx-size 16384 --port 8002 &

# Model 3: Q8 on NUMA 1
numactl --cpunodebind=1 --membind=1 \
  llama-server --model granite-32b-q8.gguf --threads 20 --ctx-size 8192 --port 8003 &
```

---

## 7. Key Takeaways

1. **Memory bandwidth, not CPU cores, limits LLM inference performance**
2. **Optimal thread count is typically 16-32 for most systems**, regardless of core count
3. **NUMA-aware allocation is critical for dual-socket systems** (1.3-2.5× latency penalty for remote access)
4. **Use mlock on systems with >4× model size in RAM** for predictable performance
5. **Q8 KV cache saves 50% memory** vs FP16 with minimal quality loss
6. **Process-level isolation** preferred for multi-model serving (different quantizations)
7. **Monitor memory bandwidth saturation** as primary performance metric

---

## 8. Further Research

- Benchmark specific CPU models (Xeon Platinum 8480+, EPYC 9654)
- Test RoPE scaling impact on KV cache size
- Evaluate Flash Attention for memory efficiency
- Measure cross-NUMA latency on specific hardware
- Profile cache miss rates with `perf` for different thread counts

---

**Document Status**: Draft for Review  
**Next Steps**: Validate with empirical benchmarks on target hardware

