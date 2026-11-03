#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10+ is required. Install Python, then rerun ./start.sh."
  exit 1
fi
if [ ! -d .venv ]; then python3 -m venv .venv; fi
. .venv/bin/activate
# The first run builds the built-in AI engine, which can take a few minutes.
python -m pip install -q -r requirements.txt
python launcher.py
