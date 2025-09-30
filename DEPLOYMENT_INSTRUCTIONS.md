# Llama.cpp Deployment Instructions

**Status:** Requires one-time sudo (Docker OR build tools)

**Recommended:** Docker-based deployment (see DEPLOYMENT_COMPARISON.md for analysis)

---

## Current Situation

- ✅ Git commit pushed to origin/master (f764e41)
- ✅ llama.cpp repository cloned to ~/llama.cpp
- ✅ Docker deployment script created
- ✅ Native build deployment script created
- ⚠️ Docker OR build tools not installed (requires sudo)

---

## Deployment Options

**Option A: Docker-based (Recommended)** - Industry standard, reproducible, aligns with project's existing Docker workflow

**Option B: Native Build** - Simpler, slightly faster (~2%), but less portable

See `DEPLOYMENT_COMPARISON.md` for detailed analysis.

---

# Option A: Docker Deployment (Recommended)

## Quick Start

```bash
# 1. Install Docker (one-time sudo)
./INSTALL_DOCKER.sh

# 2. Logout and login (for docker group membership)
exit  # Then reconnect

# 3. Deploy llama.cpp with Tongyi-30B
./scripts/deploy_llamacpp_docker.sh

# 4. Verify server is running
curl http://localhost:8080/completion -H 'Content-Type: application/json' \
  -d '{"prompt": "Test", "n_predict": 10}'
```

**Total time:** 10-21 minutes (mostly model download)

---

## Detailed Docker Deployment Steps

### Step 1: Install Docker (Requires Sudo)

```bash
# Run installation script
./INSTALL_DOCKER.sh

# This will:
# - Install docker.io and docker-compose
# - Add your user to docker group
# - Verify installation
```

**Expected output:**
```
✓ Docker installed!
Docker version 24.0.5, build 24.0.5-0ubuntu1
```

**⚠️ IMPORTANT:** You must logout and login after installation for group membership to take effect.

**Verification after logout/login:**
```bash
docker ps  # Should work without sudo
```

**Estimated time:** 2-3 minutes + logout/login

---

### Step 2: Deploy llama.cpp Server

```bash
./scripts/deploy_llamacpp_docker.sh
```

**This script will:**
1. ✅ Verify Docker is working
2. ✅ Check system resources (RAM, disk space)
3. ✅ Install HuggingFace CLI (if needed)
4. ✅ Download Tongyi-DeepResearch-30B model (32.5 GB)
5. ✅ Pull llama.cpp Docker image
6. ✅ Start llama-cpp-server container
7. ✅ Run validation tests

**Expected output:**
```
========================================
  DEPLOYMENT COMPLETE
========================================

Container: llama-cpp-server (running)
API: http://localhost:8080
Model: Tongyi-DeepResearch-30B-A3B-Q8_0.gguf (32G)

✓ Server responding
✓ Inference successful
```

**Estimated time:** 8-18 minutes (mostly model download)

---

### Step 3: Test Inference

```bash
# Basic test
curl http://localhost:8080/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "You are a coordinator agent. Plan: Build REST API with authentication",
    "n_predict": 256,
    "temperature": 0.7
  }'

# Check container logs
docker logs llama-cpp-server -f

# Check container status
docker ps
```

**Expected response:**
```json
{
  "content": "[Agentic reasoning response with task breakdown]",
  "tokens_predicted": 256,
  "tokens_evaluated": 48
}
```

---

### Docker Management Commands

```bash
# Stop server
docker stop llama-cpp-server

# Start server
docker start llama-cpp-server

# Restart server
docker restart llama-cpp-server

# View logs
docker logs llama-cpp-server -f

# Remove container (keeps model downloaded)
docker rm -f llama-cpp-server

# Re-deploy (after removal)
./scripts/deploy_llamacpp_docker.sh
```

---

# Option B: Native Build Deployment

## Quick Start

```bash
# 1. Install build tools (one-time sudo)
./INSTALL_BUILD_TOOLS.sh

# 2. Build and deploy
./scripts/deploy_llamacpp.sh
```

**Total time:** 12-23 minutes

---

## Detailed Native Build Steps

### Step 1: Install Build Dependencies (Requires Sudo)

```bash
# Run installation script
./INSTALL_BUILD_TOOLS.sh

# Or manually:
# sudo apt update
# sudo apt install -y build-essential cmake
```

**Expected output:**
```
✓ Build tools installed!
gcc (Ubuntu 13.2.0-4ubuntu3) 13.2.0
GNU Make 4.3
cmake version 3.28.3
```

**Estimated time:** 2-3 minutes

---

### Step 2: Build llama.cpp and Deploy Model

```bash
./scripts/deploy_llamacpp.sh
```

**This script will:**
1. ✅ Verify build tools are installed
2. ✅ Clone/update llama.cpp repository
3. ✅ Build with AVX-512 optimization (make -j48)
4. ✅ Install HuggingFace CLI
5. ✅ Download Tongyi-DeepResearch-30B model
6. ✅ Run validation tests

**Or manually:**
```bash
cd ~/llama.cpp
make clean && make -j48
./llama-cli --version  # Verify AVX512 = 1
```

**Expected output:**
```
AVX = 1
AVX2 = 1
AVX512 = 1
FMA = 1
```

**Estimated time:** 2-3 minutes (with 48 cores)

---

### Step 3: Test Inference

```bash
# Test 1: Basic inference
llama-cli \
  -m ~/models/tongyi/Tongyi-DeepResearch-30B-A3B-Q8_0.gguf \
  -p "You are a coordinator agent. Break down this task into subtasks: Build a REST API with authentication, unit tests, and deployment scripts." \
  -n 256 -c 4096 -t 48 \
  --temp 0.7

# Expected behavior:
# - Loads in <60 seconds
# - Generates >20 tokens/second
# - Shows multi-step planning/reasoning
# - Output includes subtasks and assignments

# Test 2: Benchmark performance
llama-bench \
  -m ~/models/tongyi/Tongyi-DeepResearch-30B-A3B-Q8_0.gguf \
  -t 48 -p 512 -n 256

# Expected results:
# - Prompt processing (pp512): ~1-2s
# - Token generation (tg256): ~10-12s
# - Speed: 23-27 tokens/second average
```

**Success Criteria:**
- ✅ Model loads successfully
- ✅ Speed >20 tokens/second
- ✅ Output shows coherent multi-step reasoning
- ✅ No memory errors

---

# Comparison: Docker vs Native

| Criterion | Docker | Native | Winner |
|-----------|--------|--------|--------|
| **Setup time** | 10-21 min | 12-23 min | Docker |
| **Performance** | ~26 tok/s | ~27 tok/s | Native (+2%) |
| **Portability** | ⭐⭐⭐⭐⭐ | ⭐⭐ | Docker |
| **Maintenance** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Docker |
| **Project alignment** | ⭐⭐⭐⭐⭐ (v1.0.0 on Docker Hub) | ⭐⭐ | Docker |
| **Simplicity** | ⭐⭐⭐ | ⭐⭐⭐⭐ | Native |

**Recommendation:** Docker (wins 4/6 criteria)

See `DEPLOYMENT_COMPARISON.md` for detailed analysis.

---

## Progress Tracking

**Completed:**
- ✅ Week 1: Error infrastructure + agent bug fix
- ✅ User simulation framework (83% success rate)
- ✅ System hardware analysis (EPYC 9454P, 1.2TB RAM)
- ✅ Model research (Tongyi-DeepResearch-30B selected)
- ✅ Git commit pushed to origin/master (f764e41)
- ✅ llama.cpp repository cloned
- ✅ Docker deployment scripts created
- ✅ Native build deployment scripts created
- ✅ Deployment comparison analysis (Docker vs Native)

**Blocked (Requires User Action - One-Time Sudo):**

**Choose ONE:**
- ⚠️ **Option A (Recommended):** Run `./INSTALL_DOCKER.sh` + logout/login + `./scripts/deploy_llamacpp_docker.sh`
- ⚠️ **Option B (Alternative):** Run `./INSTALL_BUILD_TOOLS.sh` + `./scripts/deploy_llamacpp.sh`

**Next After Deployment:**
- Implement `TongyiDeepResearchAdapter` (HTTP or subprocess)
- Week 2: Rich error formatting for CLI
- Week 3: Debug flags (--verbose, --debug)
- Week 4: Real LLM validation with Tongyi + Grok

---

## Quick Command Summary

**Docker Deployment (Recommended):**
```bash
# One-time setup
./INSTALL_DOCKER.sh
exit  # Logout and reconnect

# Deploy
./scripts/deploy_llamacpp_docker.sh

# Test
curl http://localhost:8080/completion -H 'Content-Type: application/json' \
  -d '{"prompt": "Test", "n_predict": 10}'
```

**Native Build Deployment (Alternative):**
```bash
# One-time setup
./INSTALL_BUILD_TOOLS.sh

# Deploy
./scripts/deploy_llamacpp.sh

# Test
~/llama.cpp/llama-cli -m ~/models/tongyi/Tongyi-DeepResearch-30B-A3B-Q8_0.gguf \
  -p "Test" -n 10
```

---

**Last Updated:** 2025-09-30
**Status:** Ready for user execution
**Blockers:** One-time sudo required (Docker OR build tools)
**Scripts:** 4 deployment scripts created (2 installation + 2 deployment)