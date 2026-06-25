#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p runtime
PYTHONPATH=src python3 -m throughline_ws.server --host 0.0.0.0 --port 8765 --sqlite-path runtime/gateway_events.sqlite3
