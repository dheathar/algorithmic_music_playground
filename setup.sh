#!/usr/bin/env bash
# Signal Lab — macOS/Linux setup (run once, from the project folder).
# Requires: Python 3.12+ and ffmpeg on PATH. SuperCollider is optional, system-wide.
set -e
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt
echo "Done. Start the lab with:  ./run.sh   (needs ffmpeg: brew install ffmpeg)"
