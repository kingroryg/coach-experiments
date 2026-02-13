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

## TL;DR: Experiment Comparison

| Exp | Model | Size | Techniques Tried (Extremely Specific) | Correctness | Mean Lat | p95 Lat | Mean CPU | **Peak CPU** | **p99 CPU** | Status |
|-----|-------|------|---------------------------------------|-------------|----------|---------|----------|--------------|-------------|--------|
| 1 | LFM2.5-1.2B | 1.2B | Quantization: Q4_K_M, Threads: 2, nice: 10, CTX: 4096, GGML_METAL_DISABLE: 1, N_GPU_LAYERS: 0, LLAMA_SERVER_MODE: python, temp: 0.0 | 7.5% | 2.88s | 2.88s | 35.4% | ❌ N/A | ❌ N/A | ⚠️ No spike data |
| 2 | LFM2-2.6B | 2.6B | Quantization: Q4_K_M, Threads: 2, nice: 10, CTX: 4096, GGML_METAL_DISABLE: 1, N_GPU_LAYERS: 0, LLAMA_SERVER_MODE: python, temp: 0.0 | 7.5% | 15.43s | 15.43s | 35.4% | ❌ 78.3% | ❌ 78.3% | ❌ Failed (spike) |
| 3 | LFM2-2.6B | 2.6B | Quantization: Q4_K_M, **Threads: 1** (spike mitigation attempt), nice: 10, CTX: 4096, GGML_METAL_DISABLE: 1, N_GPU_LAYERS: 0, LLAMA_SERVER_MODE: python, temp: 0.0 | 7.5% | 23.98s | 23.98s | 26.3% | ❌ 70.0% | ❌ 70.0% | ❌ Failed (spike) |
| 4 | LFM2-8B (MoE) | 8B | Quantization: Q4_K_M, Threads: 2, nice: 10, CTX: 4096, GGML_METAL_DISABLE: 1, N_GPU_LAYERS: 0, LLAMA_SERVER_MODE: python, MoE architecture (1.5B active) | N/A | N/A | N/A | N/A | N/A | N/A | ❌ Load failed |
| 5 | **RedSage-Qwen3-8B** | 8B | Quantization: Q4_K_M, Threads: 2, nice: 10, CTX: 4096, GGML_METAL_DISABLE: 1, N_GPU_LAYERS: 0, LLAMA_SERVER_MODE: python, temp: 0.0, **DPO-trained model** | **73.7%** ✅ | 22.54s | 41.79s | 46.7% | ❌ **100%** | ❌ **100%** | ⚠️ Great accuracy, bad spike |
| 6 | **RedSage-Qwen3-8B** | 8B | Quantization: Q4_K_M, **Threads: 1** (spike mitigation attempt), nice: 10, CTX: 4096, GGML_METAL_DISABLE: 1, N_GPU_LAYERS: 0, LLAMA_SERVER_MODE: python, temp: 0.0, DPO-trained | **73.7%** ✅ | 38.67s | 71.57s | 38.0% | ❌ **100%** | ❌ **100%** | ⚠️ Slower, same spike |
| 7 | **RedSage-Qwen3-8B** | 8B | Quantization: Q4_K_M, Threads: 2, **nice: 19** (max nice, spike mitigation attempt), CTX: 4096, GGML_METAL_DISABLE: 1, N_GPU_LAYERS: 0, LLAMA_SERVER_MODE: python, temp: 0.0, DPO-trained | **73.7%** ✅ | 22.05s | 40.24s | 40.2% | ❌ **100%** | ❌ **100%** | ❌ Nice doesn't cap CPU |

**Spike Mitigation Techniques Tested:**
- ❌ Thread reduction (2→1): Still 100% spike
- ❌ Nice priority increase (10→19): Still 100% spike
- ❌ Process priority scheduling: Does not cap CPU usage

**NOT Tested (because unavailable on macOS):**
- cpulimit tool (not installed, brew install failed)
- cgroups (Linux-only kernel feature)
- CPU affinity with hard caps

**Key Findings:**
- ✅ **RedSage-Qwen3-8B achieves 73.7% correctness** (near 80% goal!)
- ❌ **ALL models have CPU spikes ≥ 70%** (target: ≤ 50% p99)
- ❌ **Thread reduction (Exp 3, 6) doesn't prevent spikes** (architectural issue)
- ❌ **Nice priority (Exp 7) doesn't prevent spikes** (only affects scheduling order)
- ⚠️ **LFM models underperform** on security tasks (7.5% vs 73.7%)
- ⚠️ **Spike occurs regardless of model size** (1.2B to 8B)

**Conclusion:** Model selection solved correctness, but CPU spike problem remains unsolved. OS-level controls (nice, threads) are ineffective. Next: Test chunked prefill (application-level control).

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

## Experiment 2: LFM2-2.6B with 2 Threads

**Date:** 2026-02-13

**Model:** LiquidAI/LFM2-2.6B-GGUF (Q4_K_M quantization)

**Configuration:**
- Threads: 2
- Context size: 4096
- GPU layers: 0 (CPU-only with GGML_METAL_DISABLE=1)
- Temperature: 0.0
- Top-p: 1.0

**Results:**
- **Mean correctness score:** 0.075 (7.5%) - NO IMPROVEMENT
- **Mean latency:** 15.43s (5x slower than 1.2B!)
- **p50/p95/p99 latency:** 15.43s (perfectly stable, ratio = 1.0)
- **Mean system CPU:** 35.4%
- **🚨 PEAK system CPU:** 78.3%
- **🚨 p99 system CPU:** 78.3%
- **Process RSS:** 22.38 MB

**Key Findings:**

1. **CRITICAL: CPU Spikes Violate Requirements**
   - Peak CPU hit 78.3% - exceeds 50% p99 threshold
   - "Invisible" goal FAILED due to spikes
   - Enhanced metrics successfully caught the spike

2. **No Correctness Improvement:** 2.6B vs 1.2B showed no quality gain
   - Still only 7.5% score on security tasks
   - Suggests architectural issues or poor task fit

3. **Latency Degradation:** 5x slower than 1.2B despite only 2x size
   - Possible architecture differences (MoE overhead?)

4. **Latency Very Predictable:** p99/p50 ratio = 1.0 (excellent)

---

## Experiment 3: LFM2-2.6B with 1 Thread (Spike Mitigation)

**Date:** 2026-02-13

**Model:** LiquidAI/LFM2-2.6B-GGUF (Q4_K_M quantization)

**Configuration:**
- Threads: 1 (reduced to control spikes)
- Context size: 4096
- GPU layers: 0 (CPU-only)

**Results:**
- **Mean correctness score:** 0.075 (unchanged)
- **Mean latency:** 23.98s (56% slower than THREADS=2)
- **Mean system CPU:** 26.3%
- **🚨 PEAK system CPU:** 70.0%
- **🚨 p99 system CPU:** 70.0%
- **Process RSS:** 22.14 MB

**Key Findings:**

1. **Thread Reduction Did NOT Solve Spikes**
   - Still 70% peak CPU (above 50% threshold)
   - THREADS=1 made latency worse without fixing spikes

2. **Latency-Spike Tradeoff Poor**
   - Lost 56% performance for only 8% CPU reduction
   - Not a viable solution

---

## Experiment 4: LFM2-8B (FAILED)

**Date:** 2026-02-13

**Model:** LiquidAI/LFM2-8B-A1B-GGUF (Q4_K_M quantization)

**Result:** Model failed to load
**Error:** `ValueError: Failed to load model from file`

**Hypothesis:** MoE architecture incompatible with current llama-cpp-python version

---

## Critical Insights from Experiments 2-4

**Problem Statement:** CPU spikes exceed "invisible" threshold, models too inaccurate

1. **CPU Spike Root Cause:** Likely prefill phase causing burst
   - Need chunked prefill (split into smaller batches)
   - May need process CPU affinity/cgroups for hard limits

2. **Model Selection Issue:** LFM models underperforming on security tasks
   - Consider trying established models (Mistral, Llama, Qwen)
   - May need security-fine-tuned models

3. **Next Experiments Needed:**
   - Test chunked prefill (`--n-batch` parameter in llama.cpp)
   - Try Mistral-7B or Qwen2.5-7B with security fine-tuning
   - Investigate cgroups/CPU affinity for spike control
   - Test if smaller batch size reduces prefill spike


## Experiment 5: RedSage-Qwen3-8B with 2 Threads

**Date:** 2026-02-13

**Model:** mradermacher/RedSage-Qwen3-8B-DPO-GGUF (Q4_K_M quantization)

**Configuration:**
- Threads: 2
- Context size: 4096
- GPU layers: 0 (CPU-only with GGML_METAL_DISABLE=1)
- Temperature: 0.0
- Top-p: 1.0

**Results:**
- **🎉 Mean correctness score:** 0.7367 (73.67%) - MAJOR BREAKTHROUGH!
- **Min score:** 0.0
- **Mean latency:** 22.54s
- **p50 latency:** 23.53s
- **p95 latency:** 41.79s
- **p99 latency:** 41.79s
- **Latency p99/p50 ratio:** 1.78 (acceptable predictability)
- **Mean system CPU:** 46.7%
- **🚨 PEAK system CPU:** 100.0%
- **🚨 p99 system CPU:** 100.0%
- **Process RSS:** 13.8 MB mean, 22.22 MB peak

**Key Findings:**

1. **BREAKTHROUGH: Model Selection Solves Correctness**
   - 73.67% score is 10x better than LFM models (7.5%)
   - Nearly meets 80% correctness goal
   - RedSage-Qwen3 DPO training likely helps with instruction following

2. **CRITICAL: Worst CPU Spike Yet**
   - 100% CPU spike - completely saturates system
   - Mean CPU 46.7% is acceptable, but spikes violate "invisible" goal
   - User would definitely notice system slowdown

3. **Latency More Variable**
   - p99/p50 ratio of 1.78 shows some variability (still < 2.0 goal)
   - Longer prompts show higher latency (p95: 41.79s)

4. **Memory Efficient**
   - 22 MB peak RSS is well under budget
   - Not a constraint

---

## Experiment 6: RedSage-Qwen3-8B with 1 Thread (Spike Mitigation)

**Date:** 2026-02-13

**Model:** mradermacher/RedSage-Qwen3-8B-DPO-GGUF (Q4_K_M quantization)

**Configuration:**
- Threads: 1 (reduced to control spikes)
- Context size: 4096
- GPU layers: 0 (CPU-only)

**Results:**
- **Mean correctness score:** 0.7367 (73.67%) - unchanged
- **Mean latency:** 38.67s (72% slower)
- **p50 latency:** 40.40s
- **p95 latency:** 71.57s
- **p99 latency:** 71.57s
- **Latency p99/p50 ratio:** 1.77 (still acceptable)
- **Mean system CPU:** 38.0%
- **🚨 PEAK system CPU:** 100.0%
- **🚨 p99 system CPU:** 100.0%
- **Process RSS:** 22.62 MB

**Key Findings:**

1. **Thread Reduction DOES NOT Prevent Spikes**
   - Still 100% CPU spike despite using only 1 thread
   - Confirms spike is architectural, not a thread limit issue

2. **Severe Latency Penalty**
   - 72% slower than THREADS=2
   - p95 latency: 71.57s (way above 2.5s goal)
   - Not a viable tradeoff

3. **Spike is Single-Core Saturation**
   - 100% spike with THREADS=1 means it's saturating one core
   - Likely during prefill phase (processing prompt tokens)

---

## Critical Analysis: Experiments 5-6

**Major Success:** Found a model that meets correctness goals (RedSage-Qwen3-8B @ 73.7%)

**Major Problem:** CPU spikes cannot be controlled with thread limits alone

**Root Cause Hypothesis:**
1. **Prefill phase saturates CPU** - Processing prompt tokens happens in burst
2. **Thread limits don't prevent single-core saturation**
3. **llama.cpp processes entire prompt before responding**

**Why Thread Reduction Failed:**
- THREADS parameter limits parallel work, not single-core intensity
- Prefill is inherently sequential for each token
- 100% spike with THREADS=1 proves it's not a parallelism issue

**Next Steps (Prioritized):**

1. **Chunked Prefill (HIGHEST PRIORITY)**
   - Use `--n-batch` parameter to limit tokens processed per iteration
   - Should spread prefill work across time
   - Example: `--n-batch 128` instead of processing full prompt at once

2. **CPU Affinity / cgroups**
   - Use `taskset` to limit which cores can be used
   - Use `cgroups` to cap CPU percentage at kernel level
   - More invasive but guaranteed to work

3. **Test Different Quantizations**
   - Q6_K or Q8_0 might have different spike profiles
   - Trade memory for potentially better spike control

4. **Prompt Length Analysis**
   - Measure spike correlation with prompt length
   - Shorter prompts might stay under threshold


## Experiment 7: Nice Priority Test (nice=19 vs nice=10)

**Date:** 2026-02-13

**Model:** mradermacher/RedSage-Qwen3-8B-DPO-GGUF (Q4_K_M quantization)

**Configuration:**
- Threads: 2
- Context size: 4096
- GPU layers: 0 (CPU-only)
- **Nice level: 19 (maximum niceness)**

**Results:**
- **Mean correctness score:** 0.7367 (73.67%) - unchanged
- **Mean latency:** 22.05s (slightly better than nice=10)
- **p50 latency:** 22.23s
- **p95 latency:** 40.24s
- **p99 latency:** 40.24s
- **Latency p99/p50 ratio:** 1.81
- **Mean system CPU:** 40.2%
- **🚨 PEAK system CPU:** 100.0%
- **🚨 p99 system CPU:** 100.0%
- **Process RSS:** 22.25 MB

**Key Findings:**

1. **Nice Priority Does NOT Prevent CPU Spikes**
   - Still 100% system CPU spike despite maximum niceness (19)
   - Nice only affects *scheduling priority*, not CPU usage caps
   - When no other processes are competing, nice process gets 100% anyway

2. **Understanding Nice:**
   - Nice -20 to +19 controls scheduling priority
   - Higher nice = yields to other processes when they need CPU
   - Does NOT limit max CPU usage when system is idle
   - ❌ Not a solution for "invisible" requirement

3. **What We Actually Need:**
   - Hard CPU caps (cgroups on Linux, not available on macOS)
   - Process throttling (SIGSTOP/SIGCONT, causes stuttering)
   - Chunked prefill (spread work over time)

---

## Resource Restriction Analysis

**Tested Approaches:**

| Technique | What It Does | Does It Cap CPU? | Result |
|-----------|--------------|------------------|--------|
| **Nice priority (10)** | Lower scheduling priority | ❌ No | 100% spike |
| **Nice priority (19)** | Minimum scheduling priority | ❌ No | 100% spike |
| **Thread limit (1)** | Reduce parallelism | ❌ No | 100% spike (single core) |
| **Thread limit (2)** | Moderate parallelism | ❌ No | 100% spike |

**Why Current Techniques Fail:**

1. **Nice** = Scheduling priority, not CPU cap
   - Only helps when competing with other processes
   - If system is idle, nice process still gets 100%

2. **Thread limits** = Parallelism control, not intensity control
   - THREADS=1 means "use 1 thread"
   - That 1 thread can still run at 100% CPU

3. **Root cause:** Prefill phase processes all prompt tokens in one burst
   - No matter how many threads, it saturates whatever cores it uses
   - Need to spread the work over time, not just reduce parallelism

**What Would Actually Work:**

1. **Chunked Prefill** (HIGHEST PRIORITY)
   - Process N tokens, yield, process N more
   - Spreads CPU usage over time
   - llama.cpp `--n-batch` parameter

2. **Linux cgroups** (not available on macOS)
   - Hard kernel-level CPU percentage cap
   - Would work but requires Linux

3. **Custom Throttling** (possible but hacky)
   - Monitor CPU usage, send SIGSTOP when over threshold
   - Causes stuttering, not recommended

4. **Hardware-level** (extreme)
   - Run in VM with CPU limit
   - Too much overhead for this use case

**Conclusion:** Nice priority and thread limits are ineffective. Need chunked prefill or move to Linux with cgroups.

