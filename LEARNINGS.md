# Experiment Learnings

This file tracks key learnings from each experiment run.

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

**Next Steps:**
- Test larger model (7B+) for improved correctness
- Compare quantizations (Q4 vs Q6 vs Q8) on accuracy/latency tradeoff
- Experiment with enabling Metal/GPU if hang can be resolved
- Try binary llama-server instead of Python wrapper for faster startup

---
