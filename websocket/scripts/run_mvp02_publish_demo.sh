#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHONPATH=src python3 -m throughline_ws.client publish \
  --url ws://127.0.0.1:8765/ws \
  --topic /cell/modbus/state \
  --payload '{"process_state":70,"conveyor_state":1,"error_code":0}'
