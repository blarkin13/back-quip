#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then echo 'Install Python 3.10–3.12 first.'; exit 1; fi
if [[ ! -f .venv/bin/python ]]; then python3 -m venv .venv; fi
. .venv/bin/activate
python -m pip install -q --upgrade pip
if [[ "$(uname -s)" == "Darwin" ]]; then
  # Metal wheels are available for compatible macOS / Python versions.
  python -m pip install --only-binary=:all: --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/metal 'llama-cpp-python>=0.3.16,<0.4'
else
  python -m pip install --only-binary=:all: --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu 'llama-cpp-python>=0.3.16,<0.4'
fi
python -m pip install -r requirements.txt
python launcher.py
