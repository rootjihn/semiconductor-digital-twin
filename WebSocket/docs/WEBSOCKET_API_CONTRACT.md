# WebSocket/API Contract Draft

## 원칙

웹은 ROS2, Modbus, 로봇 SDK를 직접 호출하지 않습니다. 웹은 Gateway의 WebSocket/API만 사용합니다.

## WebSocket 기본 URL

```text
ws://localhost:8765
```

## Server → Client: state_snapshot

```json
{
  "type": "state_snapshot",
  "timestamp": "2026-06-24T12:00:00Z",
  "system": { "mode": "mock", "state": "RUNNING", "health": "OK" },
  "process": { "step": "VISION_DETECT", "job_id": "job-001", "cycle_count": 12, "success_count": 11, "fail_count": 1 },
  "robot": { "state": "READY", "connected": true, "pose": { "x": 120, "y": 30, "z": 80, "r": 0 }, "gripper": "OPEN" },
  "vision": { "state": "DETECTED", "camera_connected": true, "detections": [] },
  "modbus": { "state": "CONNECTED", "last_update_ms": 120, "signals": { "conveyor_ready": true, "part_detected": true } },
  "alarms": []
}
```

## Client → Server: command

```json
{
  "type": "command",
  "request_id": "cmd-20260624-001",
  "command": "process.start",
  "payload": {}
}
```

## Command 목록

- `process.start`
- `process.pause`
- `process.resume`
- `process.stop`
- `process.reset_error`
- `robot.home`
- `system.refresh`

## 안전 정책

- 물리 비상정지를 웹 대시보드가 대체하지 않습니다.
- 위험 명령은 confirm UI를 추가합니다.
- WebSocket 연결이 끊겨도 MVP1에서는 mock command만 생성합니다.
- 모든 command는 request_id와 함께 로그에 남깁니다.
