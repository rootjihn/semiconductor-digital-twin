#!/usr/bin/env bash
# 로컬 PyModbus mock server 실행.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/modbus_env.sh"
cd "$MODBUS_DIR"
exec "$MODBUS_PYTHON" mock_server.py \
  --host "$MODBUS_BIND_HOST" \
  --port "$MODBUS_PORT" \
  --unit-id "$MODBUS_UNIT_ID" \
  --heartbeat-interval-sec "$MODBUS_HEARTBEAT_INTERVAL_SEC" \
  --demo-step-interval-sec "$MODBUS_DEMO_STEP_INTERVAL_SEC"
