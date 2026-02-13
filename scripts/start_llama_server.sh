#!/usr/bin/env bash
set -euo pipefail

LLAMA_SERVER_MODE="${LLAMA_SERVER_MODE:-auto}" # auto|binary|python
LLAMA_SERVER_BIN="${LLAMA_SERVER_BIN:-llama-server}"
PYTHON_CMD="${PYTHON_CMD:-uv run python}"
MODEL_PATH="${MODEL_PATH:-}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"
THREADS="${THREADS:-2}"
CTX_SIZE="${CTX_SIZE:-4096}"
N_GPU_LAYERS="${N_GPU_LAYERS:-0}"
LOW_PRIORITY="${LOW_PRIORITY:-1}"
NICE_LEVEL="${NICE_LEVEL:-10}"
EXTRA_ARGS="${EXTRA_ARGS:-}"

if [[ -z "${MODEL_PATH}" ]]; then
  echo "MODEL_PATH is required"
  exit 1
fi

build_binary_cmd() {
  CMD=(
    "${LLAMA_SERVER_BIN}"
    -m "${MODEL_PATH}"
    --host "${HOST}"
    --port "${PORT}"
    -t "${THREADS}"
    -c "${CTX_SIZE}"
    -ngl "${N_GPU_LAYERS}"
  )
}

build_python_cmd() {
  # shellcheck disable=SC2206
  CMD=(
    ${PYTHON_CMD}
    -m llama_cpp.server
    --model "${MODEL_PATH}"
    --host "${HOST}"
    --port "${PORT}"
    --n_threads "${THREADS}"
    --n_ctx "${CTX_SIZE}"
    --n_gpu_layers "${N_GPU_LAYERS}"
  )
}

if [[ "${LLAMA_SERVER_MODE}" == "binary" ]]; then
  build_binary_cmd
elif [[ "${LLAMA_SERVER_MODE}" == "python" ]]; then
  build_python_cmd
else
  if command -v "${LLAMA_SERVER_BIN}" >/dev/null 2>&1; then
    build_binary_cmd
  elif command -v uv >/dev/null 2>&1; then
    build_python_cmd
  else
    echo "No server runtime found. Set LLAMA_SERVER_BIN or install uv and run 'uv sync'."
    exit 1
  fi
fi

if [[ -n "${EXTRA_ARGS}" ]]; then
  # shellcheck disable=SC2206
  EXTRA=( ${EXTRA_ARGS} )
  CMD+=("${EXTRA[@]}")
fi

echo "Launching: ${CMD[*]}"
if [[ "${LOW_PRIORITY}" == "1" ]]; then
  exec nice -n "${NICE_LEVEL}" "${CMD[@]}"
else
  exec "${CMD[@]}"
fi
