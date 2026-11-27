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
command -v uv >/dev/null || { echo "Install uv first (macOS: brew install uv)"; exit 1; }
command -v npm >/dev/null || { echo "Install Node.js and npm first"; exit 1; }
if [[ "$MODE" == local ]]; then
  if [[ "$(uname -s)" == Darwin && "$(uname -m)" != arm64 ]]; then
    echo "Local ACE-Step requires Apple Silicon on macOS."; exit 1
  fi
  mkdir -p "$(dirname "$ENGINE")"
  if [[ ! -d "$ENGINE/.git" ]]; then
    git clone https://github.com/ace-step/ACE-Step-1.5.git "$ENGINE"
  fi
  (cd "$ENGINE"; uv sync --python 3.11)
else
  echo "Remote mode: skipping local AI model installation."
fi
if ! "$ROOT/backend/.venv/bin/python" -c 'import sys; assert sys.version_info[:2] == (3, 11)' 2>/dev/null; then
  uv venv --python 3.11 "$ROOT/backend/.venv"
fi
uv pip install --python "$ROOT/backend/.venv/bin/python" -r "$ROOT/backend/requirements-dev.txt"
(cd "$ROOT/web"; npm ci --include=dev)
chmod +x "$ROOT/backend/run_ace_step_gpu.sh"
echo "Setup complete. Run bash scripts/start.sh"
