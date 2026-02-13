# Coach Experiments: Always-On Local LLM (Correctness-First)

This project helps you answer one question:

Can a local LLM stay running in the background with predictable low impact while still being correct enough for endpoint-security tasks?

## What This Repo Does
- Runs repeatable benchmark jobs against a local `llama.cpp` server
- Measures correctness and resource impact in the same run
- Compares run profiles (quantization, threads, context size, priority)
- Produces machine-readable summaries for decision making

## What This Repo Does Not Do
- Full red-team/adversarial agent testing (use Praxis later)
- Kernel-level/GPU micro-optimization benchmarking
- Production deployment automation

## Success Criteria (Set Before Tuning)
Use concrete pass/fail thresholds:
- Idle CPU budget (example: `<= 2%`)
- Active CPU budget (example: `<= 35%`)
- RAM cap (example: `<= 6 GB`)
- Latency cap (example: `p95 <= 2.5s` for short prompts)
- Correctness floor (example: `>= 0.80`)

Detailed planning checklist: `docs/plan.md`

## Repo Layout
```text
configs/    # experiment matrix definitions
docs/       # plan and testing guidance
prompts/    # endpoint-security evaluation prompts
scripts/    # server launcher, benchmark runner, matrix orchestrator
results/    # generated run outputs
```

## Quick Start
1. Create env and install deps (`uv` first).
```bash
uv venv
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python 'llama-cpp-python[server]'
```

Alternative:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install 'llama-cpp-python[server]'
```

2. Download a GGUF model (requires `HF_TOKEN`).
```bash
export HF_TOKEN=...
source .venv/bin/activate
python scripts/download_hf_gguf.py \
  --repo-id LiquidAI/LFM2.5-1.2B-Instruct-GGUF \
  --output-dir models
```

3. Point to your model path. For server runtime, default is auto:
- if `llama-server` is in `PATH`, it uses that
- else it uses `.venv/bin/python -m llama_cpp.server`

```bash
export MODEL_PATH=/path/to/model.gguf
```

4. Start local inference server with low-priority defaults.
```bash
./scripts/start_llama_server.sh
```

5. In another shell, run one benchmark pass.
```bash
python scripts/benchmark.py \
  --base-url http://127.0.0.1:8080 \
  --prompt-file prompts/endpoint_security_eval.jsonl \
  --output-dir results/manual-run
```

6. Run multi-profile experiments from config.
```bash
python scripts/run_matrix.py --config configs/matrix.example.yaml
```

## Recommended Experiment Flow
1. Run baseline (`Q8`, low thread count, deterministic decoding).
2. Sweep quantization (`Q8 -> Q6 -> Q4`) with all else fixed.
3. Sweep context/KV settings for long prompts.
4. Sweep scheduling knobs (`THREADS`, low-priority mode).
5. Pick one profile meeting both correctness and resource budgets.
6. Run longer soak tests, then move to adversarial testing.

## Outputs You Should Read First
Each run writes to `results/<run-name>/`:
- `summary.json`: primary decision file (quality + latency + CPU + RSS)
- `responses.jsonl`: per-prompt outputs and scores
- `metrics_samples.csv`: sampled system/process metrics over time
- `server.log`: runtime logs captured for the run

`results/scoreboard.json` aggregates all matrix runs.

## Technique Prioritization (Laptop, Always-On)
Prioritize first:
- Quantization
- Prompt/prefix reuse
- KV/context tuning
- Thread limits + process priority

Deprioritize initially:
- Tensor/pipeline parallelism
- Continuous batching (unless concurrency is high)
- Medusa/multi-token prediction

## Praxis Placement
Use Praxis after runtime tuning is stable.

See: `docs/praxis.md`

Praxis is useful for adversarial and agent-behavior testing; it is not the right tool for low-level inference performance profiling.
