# Dashboard MVP1 Plan

## 목적

Throughline 공정/로봇/비전/PLC 상태를 한 화면에서 관제하고, 최소한의 제어 명령을 보낼 수 있는 웹 대시보드 UI 구조를 만든다.

MVP1에서는 실제 데이터 연동을 하지 않는다. 대신 mock data와 통신 adapter 함수만 둔다.

## 핵심 화면 구조

```text
상단 상태 바
  - System state
  - Robot state
  - Vision state
  - PLC/Modbus state
  - WebSocket state

본문 3열
  - 좌측: Process Flow
  - 중앙: Live Monitoring Panels
  - 우측: Control Panel / Safety Panel

하단
  - Alarm List
  - Event Log
```

## MVP1에서 구현할 UI 컴포넌트

1. Status Header
   - RUNNING/IDLE/ERROR 상태 배지
   - Robot/Vision/PLC/WS 연결 상태

2. Process Flow
   - 입고 → 비전 → 픽업 → 검사/분류 → 배출
   - 현재 step 강조

3. Monitoring Cards
   - Current Job
   - Robot Pose
   - Vision Detection
   - PLC Signals
   - Health Monitor

4. Control Panel
   - Start
   - Pause
   - Stop
   - Reset Error
   - Home Robot
   - Refresh

5. Alarm/Event Log
   - severity/source/message/time
   - command 전송 결과를 event로 append

## MVP1에서 하지 않을 것

- 실제 ROS2 연결
- 실제 Modbus polling
- 실제 Dobot 제어
- 영상 스트리밍
- 로그인/권한 시스템
- DB 조회 API
- chart 고도화

## MVP2로 넘길 것

- WebSocket Gateway 연결
- `state_snapshot` 수신
- `event` 수신
- `command` 전송
- reconnect 처리

## MVP3 이후

- ROS2 adapter 연결
- command safety 결과 처리
- SQLite event history API
- vision frame/thumbnail 표시
