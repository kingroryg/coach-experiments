#!/usr/bin/env bash
set -euo pipefail

LLAMA_SERVER_BIN="${LLAMA_SERVER_BIN:-llama-server}"
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

CMD=(
  "${LLAMA_SERVER_BIN}"
  -m "${MODEL_PATH}"
  --host "${HOST}"
  --port "${PORT}"
  -t "${THREADS}"
  -c "${CTX_SIZE}"
  -ngl "${N_GPU_LAYERS}"
)

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
