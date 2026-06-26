# Dashboard MVP1 Plan

## 방향

MVP1은 데이터 연동보다 UI 정보구조를 우선합니다. 모든 실제 데이터는 이후 WebSocket Gateway/API로 붙입니다.

## 화면 구조

1. 상단 상태 바
   - System
   - Robot
   - Vision
   - PLC/Modbus
   - WebSocket

2. 메인 영역
   - 좌측: 공정 흐름
   - 중앙: 작업/로봇/비전/PLC/헬스 카드
   - 우측: 제어 패널/알람

3. 하단
   - 이벤트 로그

## MVP1에서 구현

- mock state snapshot
- WebSocket 연결 placeholder
- command payload 생성
- 상태 카드/공정 흐름/제어 패널/알람/로그 UI
- 나중에 실제 데이터로 교체 가능한 타입 구조

## MVP1에서 제외

- 실제 ROS2 연결
- 실제 Modbus polling
- 실제 로봇 제어
- 영상 스트리밍
- 로그인/권한
- DB 조회 API
