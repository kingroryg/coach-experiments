# Local LLM Benchmarking for Endpoint Security

Benchmark local `llama.cpp` server for correctness and resource impact on endpoint-security tasks.

**Core question:** Can a local LLM run in the background with low resource impact while being correct enough for security workloads?

## Setup

Install dependencies:
```bash
uv venv
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python 'llama-cpp-python[server]'
```

Download a model:
```bash
export HF_TOKEN=...
source .venv/bin/activate
python scripts/download_hf_gguf.py --repo-id LiquidAI/LFM2.5-1.2B-Instruct-GGUF --output-dir models
```

## Usage

Single benchmark run:
```bash
export MODEL_PATH=/path/to/model.gguf
./scripts/start_llama_server.sh  # terminal 1

python scripts/benchmark.py \
  --base-url http://127.0.0.1:8080 \
  --prompt-file prompts/endpoint_security_eval.jsonl \
  --output-dir results/run1  # terminal 2
```

Matrix experiments:
```bash
python scripts/run_matrix.py --config configs/matrix.example.yaml
```

## Outputs

Each run writes to `results/<run-name>/`:
- `summary.json` - aggregated quality, latency, CPU, and RSS metrics
- `responses.jsonl` - per-prompt outputs and scores
- `metrics_samples.csv` - time-series resource usage
- `server.log` - server logs

Matrix runs produce `results/scoreboard.json` for comparison.

## Tuning Priority

1. Quantization (Q8 → Q6 → Q4)
2. Thread limits and process priority
3. Context size and KV cache
4. Prompt/prefix reuse

See `CLAUDE.md` for detailed architecture and `docs/plan.md` for experiment methodology.
