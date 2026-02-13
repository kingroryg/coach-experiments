# Plan: Invisible Local LLM Experiment

## Success Criteria
Set these before tuning:
- Idle CPU budget (example: <= 2%)
- Active CPU budget (example: <= 35%)
- RAM cap (example: <= 6 GB)
- p95 latency cap (example: <= 2.5 s for short prompts)
- Correctness floor (example: >= 0.80 rubric score)

## Prioritized Techniques (Single Laptop)
Test first:
- Quantization (Q8/Q6/Q4)
- Prompt/prefix reuse
- KV/context tuning
- Thread limits and process priority

Deprioritize initially:
- Tensor parallelism
- Pipeline parallelism
- Continuous batching (unless many concurrent requests)
- Medusa/multi-token prediction

## Suggested Test Order
1. Baseline with high quality quantization + low thread count
2. Quantization sweep while holding all other knobs constant
3. Context and KV sweep on representative long prompts
4. Priority and thread scheduling sweep to reduce background impact
5. Lock a deployment profile and run long-duration stability tests
