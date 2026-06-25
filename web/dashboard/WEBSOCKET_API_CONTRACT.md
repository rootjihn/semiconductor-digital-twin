# WebSocket/API Contract Draft

MVP1에서는 이 계약에 맞춰 mock data와 placeholder client만 만든다. 실제 데이터 연결은 MVP2 이후 Gateway와 맞춘다.

## WebSocket URL

개발 기본값:

```text
ws://localhost:8765
```

브라우저에서는 설정값으로 변경 가능하게 만든다.

## Server → Client: state_snapshot

```json
{
  "type": "state_snapshot",
  "timestamp": "2026-06-24T12:00:00Z",
  "system": {
    "mode": "simulation",
    "state": "RUNNING",
    "health": "OK"
  },
  "process": {
    "step": "VISION_DETECT",
    "job_id": "job-001",
    "cycle_count": 12,
    "success_count": 11,
    "fail_count": 1
  },
  "robot": {
    "state": "READY",
    "connected": true,
    "pose": {"x": 120.0, "y": 30.0, "z": 80.0, "r": 0.0},
    "gripper": "OPEN"
  },
  "vision": {
    "state": "DETECTED",
    "camera_connected": true,
    "detections": [
      {"label": "target", "confidence": 0.93, "x": 320, "y": 240, "depth": 0.42}
    ]
  },
  "modbus": {
    "state": "CONNECTED",
    "last_update_ms": 120,
    "signals": {
      "conveyor_ready": true,
      "part_detected": true
    }
  },
  "alarms": []
}
```

## Server → Client: event

```json
{
  "type": "event",
  "timestamp": "2026-06-24T12:00:01Z",
  "severity": "INFO",
  "source": "gateway",
  "message": "state snapshot broadcasted"
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

## Server → Client: command_result

```json
{
  "type": "command_result",
  "request_id": "cmd-20260624-001",
  "command": "process.start",
  "status": "accepted",
  "message": "Command accepted"
}
```

## Command Names

- `process.start`
- `process.pause`
- `process.resume`
- `process.stop`
- `process.reset_error`
- `robot.home`
- `system.refresh`

## Safety Rules

- 웹 대시보드는 물리 비상정지를 대체하지 않는다.
- 위험 명령은 confirm UI를 둔다.
- 연결 끊김 상태에서는 제어 버튼을 비활성화한다.
- 모든 command는 `request_id`와 함께 event log에 남긴다.
