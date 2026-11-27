#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE="${MELODIVA_ACESTEP_DIR:-$HOME/.local/share/melodiva/ACE-Step-1.5}"
MODE="${MELODIVA_ENGINE_MODE:-auto}"
if [[ "$MODE" == auto ]]; then
  if [[ "$(uname -s)" == Darwin && "$(uname -m)" != arm64 ]]; then MODE=remote; else MODE=local; fi
fi
case "$MODE" in local|remote) ;; *) echo "Invalid MELODIVA_ENGINE_MODE"; exit 1;; esac
export MELODIVA_ENGINE_MODE="$MODE"
PIDS=()
cleanup() {
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
if [[ ! -x "$ROOT/backend/.venv/bin/python" || ! -d "$ROOT/web/node_modules" ]]; then
  echo "Run bash scripts/setup.sh first"; exit 1
fi
export MELODIVA_ENABLE_ACESTEP=1
export ACESTEP_BASE_URL="${ACESTEP_BASE_URL:-http://127.0.0.1:8001}"
export MELODIVA_PYTHON="$ROOT/backend/.venv/bin/python"
if [[ "$MODE" == local ]]; then
  export ACESTEP_BASE_URL=http://127.0.0.1:8001
if ! curl -fsS --max-time 2 "$ACESTEP_BASE_URL/health" >/dev/null 2>&1; then
  [[ -x "$ENGINE/.venv/bin/acestep-api" ]] || { echo "Run bash scripts/setup.sh first"; exit 1; }
  (cd "$ENGINE"; exec .venv/bin/acestep-api --host 127.0.0.1 --port 8001) &
  PIDS+=("$!")
fi
echo "Waiting for ACE-Step (first startup may download models)..."
deadline=$((SECONDS + ${MELODIVA_ENGINE_TIMEOUT:-1800}))
until curl -fsS --max-time 2 "$ACESTEP_BASE_URL/health" >/dev/null 2>&1; do
  if [[ ${#PIDS[@]} -gt 0 ]] && ! kill -0 "${PIDS[0]}" 2>/dev/null; then
    echo "ACE-Step exited; check the output above."; exit 1
  fi
  if (( SECONDS >= deadline )); then echo "ACE-Step startup timed out"; exit 1; fi
  sleep 3
done
else
  if [[ "$ACESTEP_BASE_URL" != https://* || -z "${ACESTEP_API_KEY:-}" ]]; then
    echo "Remote engine not configured. Studio will start with generation disabled."
    export MELODIVA_ENABLE_ACESTEP=0
  else
    echo "Remote ACE-Step configured; backend will check readiness."
  fi
fi
(cd "$ROOT/backend"; exec "$MELODIVA_PYTHON" -m uvicorn server:app --host 127.0.0.1 --port 8002) &
PIDS+=("$!")
(cd "$ROOT/web"; exec node node_modules/vite/bin/vite.js --host 127.0.0.1 --strictPort) &
PIDS+=("$!")
echo "Melodiva: http://127.0.0.1:5174/#/full-song"
while true; do
  for pid in "${PIDS[@]}"; do
    if ! kill -0 "$pid" 2>/dev/null; then echo "A managed service exited; stopping launcher."; exit 1; fi
  done
  sleep 2
done
