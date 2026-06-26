# MVP Roadmap

## MVP1 — UI 구조와 통신 계약

- Vite + React + TypeScript 대시보드
- mock snapshot
- command payload 생성
- WebSocket client placeholder
- 상태/공정/제어/알람/로그 UI

## MVP2 — WebSocket Gateway 연결

- `state_snapshot` 수신
- `event` 수신
- `command` 전송
- reconnect 처리

## MVP3 — Simulator Mode

- Gateway가 fake robot/vision/plc 상태 생성
- UI는 실제 장비 없이 테스트 가능

## MVP4 — ROS2 Adapter

- `/cell/process/state`
- `/dobot/status`
- `/vision/detections`
- `/modbus_bridge/status`
- `/alarm/events`

## MVP5 — 운영 기능

- SQLite event history API
- alarm acknowledge
- command history
- vision thumbnail/overlay
