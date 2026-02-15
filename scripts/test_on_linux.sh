#!/usr/bin/env bash
set -euo pipefail

echo "Building Docker image for Linux testing..."
docker build -t coach-experiments-test -f Dockerfile.test .

echo ""
echo "Starting Docker container..."
docker run --rm \
  -v "$(pwd)/models:/app/models" \
  -v "$(pwd)/results:/app/results" \
  -e HF_TOKEN="${HF_TOKEN:-}" \
  coach-experiments-test /bin/bash -c '
    echo "=== Testing Exp 13 config on Linux ==="
    echo ""
    echo "Starting llama server with best config (CPU-only, low threads)..."

    # Start server in background
    uv run python -m llama_cpp.server \
      --model models/mradermacher__RedSage-Qwen3-8B-DPO-GGUF/RedSage-Qwen3-8B-DPO.Q4_K_M.gguf \
      --host 127.0.0.1 \
      --port 8080 \
      --n_threads 1 \
      --n_threads_batch 1 \
      --n_ctx 4096 \
      --n_gpu_layers 0 > /tmp/server.log 2>&1 &

    SERVER_PID=$!
    echo "Server PID: $SERVER_PID"

    # Wait for server to be ready
    echo "Waiting for server to start..."
    for i in {1..60}; do
      if curl -s http://127.0.0.1:8080/v1/models >/dev/null 2>&1; then
        echo "Server ready!"
        break
      fi
      sleep 2
    done

    # Run benchmark
    echo ""
    echo "Running benchmark..."
    uv run python scripts/benchmark.py \
      --base-url http://127.0.0.1:8080 \
      --prompt-file prompts/endpoint_security_eval.jsonl \
      --output-dir results/exp20_linux_verification \
      --server-pid $SERVER_PID

    echo ""
    echo "=== Results ==="
    cat results/exp20_linux_verification/summary.json

    # Cleanup
    kill $SERVER_PID 2>/dev/null || true
  '

echo ""
echo "Test complete! Results saved to results/exp20_linux_verification/"
