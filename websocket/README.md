# Throughline WebSocket Gateway MVP

외부 의존성 없이 Python 표준 라이브러리만으로 구현한 WebSocket 서버/클라이언트 MVP다.

자세한 구현 계획은 [`WEBSOCKET_IMPLEMENTATION_PLAN.md`](./WEBSOCKET_IMPLEMENTATION_PLAN.md)를 본다.

## 빠른 실행

```bash
cd /home/ssafy/penetrate_pjt/websocket
PYTHONPATH=src python3 -m throughline_ws.server --host 0.0.0.0 --port 8765
# 이벤트 로그 포함 운영형 실행
scripts/run_mvp05_server_with_log.sh
```

다른 터미널에서:

```bash
cd /home/ssafy/penetrate_pjt/websocket
PYTHONPATH=src python3 -m throughline_ws.client echo --url ws://127.0.0.1:8765/ws --text hello
PYTHONPATH=src python3 -m throughline_ws.client publish --url ws://127.0.0.1:8765/ws --topic /cell/modbus/state --payload '{"process_state":70}'
PYTHONPATH=src python3 -m throughline_ws.client command --url ws://127.0.0.1:8765/ws --command start --target process_manager
```

## 테스트

```bash
cd /home/ssafy/penetrate_pjt/websocket
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 현재 구현된 MVP

- MVP 01: WebSocket echo/health
- MVP 02: topic별 state hub/broadcast
- MVP 03: ROS2/Modbus 연동 adapter 경계 skeleton
- MVP 04: 단일 HTML browser client
- MVP 05: SQLite 이벤트 로그 옵션과 운영 스크립트

## 설계 원칙

- Dashboard/WebSocket은 Modbus를 직접 polling/write하지 않는다.
- 실제 장비 명령은 `process_manager_node` 또는 안전한 ROS2 service 경유를 기준으로 한다.
- 고주기 영상/point cloud는 WebSocket MVP 범위에서 제외한다.
