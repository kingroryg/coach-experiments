# Optimization Techniques for Always-On Local LLM

## Goal Alignment Analysis

**Use Case:** Single laptop, always-on background service for endpoint security analysis
**Priorities:**
1. **No spikes** - CPU/memory/latency must stay within bounds (truly invisible)
2. Low resource impact when idle
3. Predictable performance
4. Adequate correctness

**Critical:** "Invisible" means no perceptible system slowdown. User shouldn't notice the service is running, even during inference.

---

## HIGH PRIORITY (Experiment Now)

### 1. Quantization (INT8/INT4/FP8)
**Status:** ✅ Already planned in docs/plan.md

**Why it matters:**
- Reduces memory footprint (critical for <= 6GB budget)
- Improves inference speed (helps meet <= 2.5s latency)
- Already tested Q4_K_M, need to test Q6/Q8 for accuracy tradeoff

**Experiment needed:**
- Compare Q8_0 vs Q6_K vs Q4_K_M on correctness and latency
- Find sweet spot for 7B+ model

---

### 2. Prompt/Prefix Caching
**Status:** ✅ Already planned ("Prompt/prefix reuse" in docs/plan.md)

**Why it matters:**
- System prompts repeated for every security event
- Can eliminate 50-200 tokens of processing per request
- Directly reduces active CPU time and latency
- llama.cpp supports this natively

**Experiment needed:**
- Measure latency with vs without cached system prompt
- Test KV cache reuse across requests

---

### 3. Thread Limits + Process Priority
**Status:** ✅ Already planned and partially implemented

**Why it matters:**
- Controls CPU usage during active inference
- `nice` scheduling helps achieve "invisible" idle behavior
- Thread count directly impacts CPU percentage
- **CRITICAL for no-spike goal:** Hard thread limit prevents CPU burst

**Current:** THREADS=2, NICE_LEVEL=10
**Experiment needed:**
- Test THREADS=1 vs 2 vs 4 on **peak CPU** (not just mean)
- Measure p99 CPU to ensure no spikes above threshold
- Validate that nice scheduling prevents interference with foreground tasks
- **Monitor:** p50/p95/p99 CPU during inference

---

### 4. KV-Cache Optimization
**Status:** ✅ Already planned ("KV/context tuning" in docs/plan.md)

**Why it matters:**
- Context size (CTX_SIZE) affects memory usage
- Right-sizing prevents waste for short security prompts
- KV cache quantization could save memory (if supported)

**Current:** CTX_SIZE=4096
**Experiment needed:**
- Test CTX_SIZE=2048 vs 4096 vs 8192 for typical prompt lengths
- Measure memory impact

---

---

### 5. Chunked Prefill
**Status:** 🔥 HIGH PRIORITY for no-spike goal

**Why it matters:**
- **Prevents CPU spikes** on longer prompts (even 1K tokens can spike)
- Spreads prefill work across multiple iterations
- Keeps latency predictable (critical for "invisible" operation)
- More important than initially thought due to no-spike requirement

**Experiment needed:**
- Test with/without chunked prefill on 500-2000 token prompts
- Measure **peak CPU** during prefill phase
- Validate latency stays smooth (p99/p50 ratio)
- llama.cpp may support this via `--n-batch` parameter

---

## MEDIUM PRIORITY (Consider Later)

---

### 6. Continuous Batching
**Use case:** Only if multiple concurrent security events are common

**Why deprioritized:**
- Single laptop, low concurrency workload
- Adds complexity
- README explicitly says "Deprioritize initially"

**When to test:** If you observe request queuing in production

---

## LOW PRIORITY / NOT APPLICABLE

### 7. Flash Attention
**Why not:** Requires GPU, we're CPU-only due to Metal hang

---

### 8. Speculative Decoding
**Why not:**
- Requires 2x models (draft + target)
- Adds memory and complexity
- Best for high-throughput, not background service

---

### 9. Paged Attention / vLLM
**Why not:** Designed for server workloads with many concurrent users

---

### 10. Tensor Parallelism
**Why not:** Requires multiple GPUs, not applicable to single laptop

---

### 11. Pipeline Parallelism
**Why not:** Requires multiple devices, not applicable

---

### 12. Mixed Precision Inference
**Status:** Already covered by GGUF quantization

---

### 13. Medusa / Multi-token Prediction
**Why not:**
- README says "Deprioritize initially"
- Requires special model training
- Adds complexity

---

### 14. Attention Sinks
**Why not:** For streaming/infinite context, not discrete event analysis

---

### 15. Kernel Fusion & Custom CUDA
**Why not:** CPU-only deployment, low-level optimization premature

---

### 16. Request Scheduling & Priority Queues
**Why consider:** Could be useful for burst handling
**When to test:** Only if observing request queuing

---

## Recommended Experiment Order

Based on the **no-spike "invisible" goal**:

1. **Model selection** (7B+ for adequate correctness)
2. **Quantization sweep** (Q8 → Q6 → Q4)
   - **Monitor:** Not just mean latency, but p95/p99 latency and CPU
3. **Thread tuning** (1, 2, 4 threads + nice levels)
   - **Monitor:** Peak CPU, p99 CPU during inference
   - Ensure no CPU burst above 50% even momentarily
4. **Chunked prefill** (PROMOTED to high priority)
   - Test on realistic prompt lengths (500-2000 tokens)
   - **Monitor:** CPU stability during prefill phase
5. **Context sizing** (2048, 4096, 8192 for typical workload)
   - **Monitor:** Memory spikes during context window growth
6. **Prompt caching** (measure impact of cached system prompt)
   - Reduces processing = fewer opportunities for spikes
7. **Continuous batching** (only if concurrency observed)

## Key Metrics to Track

**For "no spikes" validation:**
- CPU: mean, p95, **p99, peak**
- Memory: mean, **peak, spikes**
- Latency: p50, p95, **p99, p99/p50 ratio**
- System responsiveness (subjective: can you tell it's running?)

**Conclusion:** Updated priority to emphasize spike prevention. Chunked prefill promoted to high priority.
