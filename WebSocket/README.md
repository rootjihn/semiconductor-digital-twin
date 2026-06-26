# Throughline WebSocket Dashboard

Throughline 공정/로봇/비전/PLC 상태를 관제하기 위한 웹 대시보드 MVP입니다.

## MVP1 목표

실제 데이터 연동 전, UI 구조와 통신 계약을 먼저 고정합니다.

- 실제 ROS2/Modbus/Dobot/비전 데이터는 아직 붙이지 않습니다.
- 데이터는 mock snapshot으로 렌더링합니다.
- WebSocket/API client 함수와 메시지 타입은 미리 구현합니다.
- 제어 버튼은 command payload 생성과 UI 이벤트 로그까지만 수행합니다.

## 실행

```bash
cd /home/quincy/HDD/Throughline_PJT/WebSocket
npm install
npm run dev
```

접속:

```text
http://localhost:5173
```

## 빌드 검증

```bash
npm run build
```

## 문서

- `docs/DASHBOARD_PLAN.md`
- `docs/WEBSOCKET_API_CONTRACT.md`
- `docs/MVP_ROADMAP.md`
