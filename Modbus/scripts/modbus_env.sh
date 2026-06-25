#!/usr/bin/env bash
# Throughline Modbus 로컬 실행 공통 환경.
# .env.local이 있으면 우선 읽고, 없으면 안전한 개발 기본값을 사용한다.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODBUS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -f "$MODBUS_DIR/.env.local" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$MODBUS_DIR/.env.local"
  set +a
fi

export MODBUS_HOST="${MODBUS_HOST:-127.0.0.1}"
export MODBUS_BIND_HOST="${MODBUS_BIND_HOST:-127.0.0.1}"
export MODBUS_PORT="${MODBUS_PORT:-15020}"
export MODBUS_UNIT_ID="${MODBUS_UNIT_ID:-1}"
export MODBUS_DEMO_STEP_INTERVAL_SEC="${MODBUS_DEMO_STEP_INTERVAL_SEC:-3.0}"
export MODBUS_HEARTBEAT_INTERVAL_SEC="${MODBUS_HEARTBEAT_INTERVAL_SEC:-1.0}"
export MODBUS_PYTHON="$MODBUS_DIR/.venv/bin/python"

if [[ ! -x "$MODBUS_PYTHON" ]]; then
  echo "ERROR: .venv가 없습니다. 먼저 'cd $MODBUS_DIR && uv sync'를 실행하세요." >&2
  exit 1
fi
