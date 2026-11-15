#!/usr/bin/env bash
# Host one Gemma-2-2B server with the T2L LoRA module on the target GPU.
# Used by the phase-1 gate and the grid; the demo script builds on the same command.
set -euo pipefail

cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-6}"
LORA_DIR="${LORA_DIR:-artifacts/t2l_loras/gsm8k}"
PORT="${PORT:-8000}"
MODEL="${MODEL:-unsloth/gemma-2-2b-it}"

exec .venv-serve/bin/vllm serve \
  --model "$MODEL" \
  --enable-lora --max-lora-rank 64 \
  --lora-modules "t2l_gsm8k=${LORA_DIR}" \
  --gpu-memory-utilization 0.55 \
  --max-model-len 4096 \
  --port "$PORT"
