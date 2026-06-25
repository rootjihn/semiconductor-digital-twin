# Throughline Web Dashboard MVP1

목표: 실제 ROS2/Modbus/비전 데이터가 완성되기 전까지, 웹 대시보드의 UI 구조와 통신 계약을 먼저 고정한다.

## MVP1 원칙

- 데이터는 mock state와 WebSocket/API contract만 사용한다.
- 웹은 Modbus, 로봇 SDK, ROS2를 직접 호출하지 않는다.
- 웹은 Gateway가 주는 JSON snapshot/event/command_result만 소비한다.
- 제어 버튼은 UI와 command payload 생성까지만 구현한다.
- 실장비 연결은 MVP2 이후에 붙인다.

## 실행

현재 원격 서버에 Node/Vite가 없으므로 MVP1은 빌드 없는 정적 HTML/CSS/JS로 시작한다.

```bash
cd /home/ssafy/penetrate_pjt/web/dashboard
python3 -m http.server 5173
```

브라우저에서 `http://<server-ip>:5173` 접속.

## 파일

- `DASHBOARD_PLAN.md`: 화면 구조와 MVP 범위
- `WEBSOCKET_API_CONTRACT.md`: 나중에 Gateway와 맞출 메시지 계약
- `index.html`: MVP1 정적 UI
- `src/styles.css`: 대시보드 스타일
- `src/app.js`: mock state, WebSocket placeholder, command payload 생성
