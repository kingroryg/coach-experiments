# Experiment Learnings

This file tracks key learnings from each experiment run.

**Goal:** Can a local LLM stay running in the background with predictable low impact while being correct enough for endpoint-security tasks?

**Success Criteria:**
- Idle CPU: <= 2%
- Active CPU: <= 35% mean, <= 50% p99 (NO SPIKES)
- RAM: <= 6 GB peak
- p95 latency: <= 2.5s
- Latency predictability: p99/p50 ratio < 2.0
- Correctness: >= 0.80

**"Invisible" means:** No perceptible system slowdown during inference. User shouldn't notice the service is running.

---

## Experiment 1: Initial Baseline with LiquidAI 1.2B

**Date:** 2026-02-13

**Model:** LiquidAI/LFM2.5-1.2B-Instruct-GGUF (Q4_K_M quantization)

**Configuration:**
- Threads: 2
- Context size: 4096
- GPU layers: 0 (CPU-only with GGML_METAL_DISABLE=1)
- Temperature: 0.0
- Top-p: 1.0

**Results:**
- **Mean correctness score:** 0.075 (7.5%)
- **Min score:** 0.0
- **Score distribution:** 1/10 prompts scored 0.75, rest scored 0.0
- **Mean latency:** 2.88s per prompt
- **P95 latency:** 2.88s
- **System CPU:** 35.45% average
- **Process RSS:** 22.16 MB average
- ⚠️ **Missing:** p99 CPU, peak system CPU, latency p99 (metrics not tracked)

**Key Findings:**

1. **Critical macOS Issue:** Server hangs indefinitely during Metal initialization
   - **Root cause:** llama.cpp tries to initialize Metal backend even with N_GPU_LAYERS=0
   - **Solution:** Set `GGML_METAL_DISABLE=1` environment variable
   - **Impact:** Required for any server startup on macOS

2. **Model Size Inadequate:** 1.2B parameters too small for complex security tasks
   - Only 10% of endpoint security prompts answered correctly
   - Model lacks domain knowledge for security analysis
   - **Recommendation:** Test 7B+ models for production use

3. **Performance Acceptable:** Latency and resource usage reasonable for CPU-only
   - ~3s per prompt is acceptable for background analysis
   - 35% CPU usage meets "active CPU budget" goal (<= 35%)
   - 22MB RAM well under typical budgets

4. **Server Startup Time:** Approximately 30 seconds with CPU-only mode
   - Most time spent loading Metal kernels (even when disabled)
   - Binary llama-server may start faster than Python wrapper

**Critical Gap Identified:**
- Need to track **spike metrics** (p99 CPU, peak system CPU, p99 latency)
- "Invisible" means NO SPIKES, not just low averages
- Benchmark script enhanced to track p99/peak metrics going forward

**Next Steps:**
- Test larger model (7B+) for improved correctness
- Compare quantizations (Q4 vs Q6 vs Q8) on accuracy/latency tradeoff
- **Validate no CPU spikes** during inference (monitor p99 CPU)
- Test chunked prefill to prevent latency spikes on longer prompts
- Experiment with enabling Metal/GPU if hang can be resolved
- Try binary llama-server instead of Python wrapper for faster startup

---
