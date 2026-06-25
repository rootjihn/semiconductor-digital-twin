#!/usr/bin/env bash
# 로컬 Modbus server 상태를 watch 모드로 감시한다.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/modbus_env.sh"
cd "$MODBUS_DIR"
exec "$MODBUS_PYTHON" register_client.py \
  --host "$MODBUS_HOST" \
  --port "$MODBUS_PORT" \
  --unit-id "$MODBUS_UNIT_ID" \
  watch "${@}"
