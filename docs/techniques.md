# Optimization Techniques for Always-On Local LLM

## Goal Alignment Analysis

**Use Case:** Single laptop, always-on background service for endpoint security analysis
**Priorities:** Low resource impact when idle, predictable performance, adequate correctness

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

**Current:** THREADS=2, NICE_LEVEL=10
**Experiment needed:**
- Test THREADS=1 vs 2 vs 4 on latency/CPU tradeoff
- Validate that nice scheduling keeps idle CPU < 2%

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

## MEDIUM PRIORITY (Consider Later)

### 5. Chunked Prefill
**Use case:** Only if analyzing very long logs (>4K tokens)

**Why consider:**
- Prevents latency spikes on long prompts
- Keeps response time predictable

**When to test:** After baseline tuning, if log analysis is common

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

Based on the goal and current state:

1. **Model selection** (7B+ for adequate correctness)
2. **Quantization sweep** (Q8 → Q6 → Q4)
3. **Thread tuning** (1, 2, 4 threads + nice levels)
4. **Context sizing** (2048, 4096, 8192 for typical workload)
5. **Prompt caching** (measure impact of cached system prompt)
6. **Chunked prefill** (if log analysis is common)
7. **Continuous batching** (only if concurrency observed)

**Conclusion:** The existing plan in docs/plan.md already captures the right techniques. No major changes needed.
