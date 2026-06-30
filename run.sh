#!/usr/bin/env bash
# Start the Signal Lab locally -> open http://127.0.0.1:7700/
[ -x .venv/bin/uvicorn ] || { echo "Run ./setup.sh first."; exit 1; }
echo "Signal Lab at http://127.0.0.1:7700/   (Ctrl+C to stop)"
exec ./.venv/bin/uvicorn server:app --port 7700
