#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE="${MELODIVA_ACESTEP_DIR:-$HOME/.local/share/melodiva/ACE-Step-1.5}"
command -v uv >/dev/null || { echo "Install uv first (macOS: brew install uv)"; exit 1; }
command -v npm >/dev/null || { echo "Install Node.js and npm first"; exit 1; }
if [[ "$(uname -s)" == Darwin && "$(uname -m)" != arm64 ]]; then
  echo "Upstream ACE-Step dependencies target Apple Silicon, not Intel Macs."; exit 1
fi
mkdir -p "$(dirname "$ENGINE")"
if [[ ! -d "$ENGINE/.git" ]]; then
  git clone https://github.com/ace-step/ACE-Step-1.5.git "$ENGINE"
fi
(cd "$ENGINE"; uv sync --python 3.11)
uv venv --allow-existing --python 3.11 "$ROOT/backend/.venv"
uv pip install --python "$ROOT/backend/.venv/bin/python" -r "$ROOT/backend/requirements-dev.txt"
(cd "$ROOT/web"; npm ci --include=dev)
chmod +x "$ROOT/backend/run_ace_step_gpu.sh"
echo "Setup complete. Run bash scripts/start.sh"
