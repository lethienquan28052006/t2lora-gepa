#!/usr/bin/env bash
# Demo: one vLLM server on GPU 6 hosting Gemma-2-2B + the T2L LoRA module.
set -euo pipefail

cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES=6
LORA_DIR="${LORA_DIR:-artifacts/t2l_loras/gsm8k}"
PORT="${PORT:-8000}"

if [[ ! -f "$LORA_DIR/adapter_config.json" ]]; then
  echo "no LoRA at $LORA_DIR; generating one from the task description first"
  uv run python - <<'PY'
from t2lgepa.config import load_config
from t2lgepa.t2l import generate_lora

cfg = load_config("configs/base.yaml")
print(generate_lora(cfg, "gsm8k", "artifacts/t2l_loras"))
PY
fi

uv run --with vllm vllm serve \
  --model google/gemma-2-2b-it \
  --enable-lora --max-lora-rank 64 \
  --lora-modules "t2l_gsm8k=${LORA_DIR}" \
  --gpu-memory-utilization 0.85 --port "$PORT" &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT

until curl -sf "http://localhost:${PORT}/v1/models" >/dev/null; do
  sleep 5
done

uv run python -m t2lgepa.demo --base-url "http://localhost:${PORT}"
