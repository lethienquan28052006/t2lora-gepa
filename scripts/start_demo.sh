#!/usr/bin/env bash
# One command: vLLM (GPU 7) -> FastAPI demo page -> optional cloudflared tunnel.
#
#   ./scripts/start_demo.sh              # model + web on localhost:7860
#   ./scripts/start_demo.sh --tunnel     # also publish cs222.lethienquan.site
#
# Ctrl-C stops everything it started.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${T2L_ROOT:-/data/quan.lt/temp/t2l-mistral}"
GPU="${GPU:-7}"
WEB_PORT="${WEB_PORT:-7860}"
MODEL_PORT="${MODEL_PORT:-8010}"
HOSTNAME_PUBLIC="${HOSTNAME_PUBLIC:-cs222.lethienquan.site}"
TUNNEL_ID="${TUNNEL_ID:-68bc1088-ed4b-4c81-b495-0881666d937f}"
LOGDIR="${LOGDIR:-/tmp/t2l-demo}"
RUN_DIR="${RUN_DIR:-$ROOT/runs/mistral-7b-v1/results}"
# Cold start loads 13.5 GiB of weights from Ceph, then compiles/captures CUDA graphs.
# On a busy box this easily exceeds six minutes, so wait up to 15 by default.
MODEL_WAIT_SECONDS="${MODEL_WAIT_SECONDS:-900}"

TUNNEL=0
for arg in "$@"; do
  case "$arg" in
    --tunnel) TUNNEL=1 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

mkdir -p "$LOGDIR"
export HF_HOME="$ROOT/hf"
export VLLM_USE_FLASHINFER_SAMPLER=0

PIDS=()
cleanup() {
  echo
  echo "[demo] shutting down…"
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  echo "[demo] done."
}
trap cleanup INT TERM EXIT

wait_for_models() {
  local want=6
  local pid="${1:-}"
  local deadline=$(( $(date +%s) + MODEL_WAIT_SECONDS ))
  local last_report=0
  while [ "$(date +%s)" -lt "$deadline" ]; do
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
      echo "[demo] model server exited before becoming ready; see $LOGDIR/vllm.log" >&2
      tail -n 40 "$LOGDIR/vllm.log" >&2 || true
      return 1
    fi
    local n
    n=$(curl -sf "http://localhost:${MODEL_PORT}/v1/models" 2>/dev/null \
        | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["data"]))' 2>/dev/null || echo 0)
    if [ "$n" -ge "$want" ]; then
      echo "[demo] model server ready with $n models"
      return 0
    fi
    local now
    now=$(date +%s)
    if [ $((now - last_report)) -ge 30 ]; then
      echo "[demo] waiting for model server (${n}/${want} models, $((deadline - now))s left)"
      last_report=$now
    fi
    sleep 2
  done
  echo "[demo] model server did not become ready after ${MODEL_WAIT_SECONDS}s" >&2
  echo "[demo] last 40 lines of $LOGDIR/vllm.log:" >&2
  tail -n 40 "$LOGDIR/vllm.log" >&2 || true
  return 1
}

if curl -sf "http://localhost:${MODEL_PORT}/v1/models" >/dev/null 2>&1; then
  echo "[demo] reusing the model server already on :${MODEL_PORT}"
else
  echo "[demo] writing demo serve config (gpu_memory_utilization 0.35)"
  python3 "$REPO/scripts/write_demo_config.py" --root "$ROOT"
  echo "[demo] starting vLLM on GPU ${GPU} (:${MODEL_PORT})"
  CUDA_VISIBLE_DEVICES="$GPU" "$REPO/.venv-serve/bin/vllm" serve \
    --config "$ROOT/serve_demo.yaml" > "$LOGDIR/vllm.log" 2>&1 &
  MODEL_PID=$!
  PIDS+=("$MODEL_PID")
  wait_for_models "$MODEL_PID"
fi

if curl -sf "http://localhost:${WEB_PORT}/api/meta" >/dev/null 2>&1; then
  echo "[demo] reusing the web app already on :${WEB_PORT}"
else
  echo "[demo] starting web app on :${WEB_PORT}"
  ( cd "$REPO" && PYTHONPATH="$REPO/src${PYTHONPATH:+:$PYTHONPATH}" "$REPO/.venv/bin/python" -m t2lgepa.webapp.app \
      --config configs/mistral.yaml \
      --results "$RUN_DIR" \
      --base-url "http://localhost:${MODEL_PORT}" \
      --port "$WEB_PORT" > "$LOGDIR/web.log" 2>&1 ) &
  PIDS+=($!)
  for _ in $(seq 1 60); do
    curl -sf "http://localhost:${WEB_PORT}/api/meta" >/dev/null 2>&1 && break
    sleep 1
  done
  curl -sf "http://localhost:${WEB_PORT}/api/meta" >/dev/null || {
    echo "[demo] web app failed to start; see $LOGDIR/web.log" >&2; exit 1; }
fi

echo "[demo] local:  http://localhost:${WEB_PORT}"

if [ "$TUNNEL" = "1" ]; then
  if pgrep -f "cloudflared tunnel .*run" >/dev/null 2>&1; then
    echo "[demo] a cloudflared tunnel is already running; leaving it alone"
  else
    echo "[demo] starting cloudflared tunnel ${TUNNEL_ID}"
    cloudflared tunnel --config "$HOME/.cloudflared/config.yml" run "$TUNNEL_ID" \
      > "$LOGDIR/cloudflared.log" 2>&1 &
    PIDS+=($!)
    sleep 6
  fi
  echo "[demo] public: https://${HOSTNAME_PUBLIC}"
fi

echo "[demo] logs: $LOGDIR   (Ctrl-C to stop everything)"
wait
