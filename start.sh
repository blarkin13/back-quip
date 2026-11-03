#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

ENGINE_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
ENGINE_URL="${ENGINE_URL%/}/api/tags"
engine_ready() {
  if command -v curl >/dev/null 2>&1; then
    curl -fsS --connect-timeout 1 --max-time 2 "$ENGINE_URL" >/dev/null 2>&1
  else
    python3 - "$ENGINE_URL" <<'PY'
import sys, urllib.request
try:
    urllib.request.urlopen(sys.argv[1], timeout=2).close()
except Exception:
    sys.exit(1)
PY
  fi
}

if ! engine_ready; then
  if ! command -v ollama >/dev/null 2>&1; then
    # The macOS app can be present even when the CLI isn't yet on PATH.
    if [[ "$(uname -s)" == "Darwin" && -x /Applications/Ollama.app/Contents/Resources/ollama ]]; then
      export PATH="/Applications/Ollama.app/Contents/Resources:$PATH"
    fi
  fi
  if ! command -v ollama >/dev/null 2>&1; then
    echo "[Back Quip] The local AI engine is not installed."
    echo "[Back Quip] Official installer: https://ollama.com/download"
    if [[ ! -t 0 ]]; then
      echo "[Back Quip] Launch this script in a terminal to approve installation."
      exit 1
    fi
    read -r -p "Install the local AI engine using its official installer now? [y/N] " choice
    case "$choice" in
      y|Y|yes|YES)
        command -v curl >/dev/null 2>&1 || { echo "curl is required for the installer."; exit 1; }
        # Explicit opt-in only; download to a file and then run official script.
        installer="$(mktemp)"
        trap 'rm -f "$installer"' EXIT
        curl -fLsS https://ollama.com/install.sh -o "$installer"
        sh "$installer"
        rm -f "$installer"
        trap - EXIT
        hash -r
        ;;
      *)
        echo "[Back Quip] AI setup skipped. Install it and rerun ./start.sh."
        exit 1
        ;;
    esac
    if ! command -v ollama >/dev/null 2>&1; then
      echo "[Back Quip] Installation finished, but 'ollama' is not on PATH. Open a new terminal and rerun ./start.sh."
      exit 1
    fi
  fi
  if ! engine_ready; then
    echo "[Back Quip] Starting local AI engine..."
    # Detach the engine so it survives the shell and doesn't block the web app.
    nohup ollama serve > "${TMPDIR:-/tmp}/back-quip-ollama.log" 2>&1 < /dev/null &
    for _ in $(seq 1 40); do
      if engine_ready; then break; fi
      sleep 0.5
    done
    if ! engine_ready; then
      echo "[Back Quip] AI engine did not start. Check ${TMPDIR:-/tmp}/back-quip-ollama.log"
      exit 1
    fi
  fi
fi

echo "[Back Quip] Local AI engine ready."
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10+ is required. Install Python, then rerun ./start.sh."
  exit 1
fi
if [ ! -d .venv ]; then python3 -m venv .venv; fi
. .venv/bin/activate
python -m pip install -q -r requirements.txt
python launcher.py
