# Throughline Vue 대시보드 디자인 검수

## 1. 검수 범위

이 문서는 Vue Router 기반 `WebSocket/` 프론트 구현물을 사용자 요구 기준으로 시각 QA한 결과다.

검수 기준:
- 깔끔하고 현대적인 관제 화면인지
- 사각형 아이콘 박스/두꺼운 테두리 카드 느낌이 과하지 않은지
- 노드, 선, 라벨이 겹치지 않는지
- Dobot, TurtleBot3, RoboDK, 힌지벨트, Raspberry Pi, Gateway/Server 역할이 구분되는지
- Vue Router 페이지 전환이 자연스러운지
- Chart.js가 필요한 지표에만 쓰였는지
- 마우스 모션/인터랙션이 화면 이해를 방해하지 않는지

확인한 실행:

| 항목 | 결과 | 근거 |
|---|---:|---|
| 빌드 | Pass | `npm run build && npm run smoke` 종료 코드 0 |
| 스모크 | Pass | `npm run smoke` 종료 코드 0 |
| 프리뷰 | Pass | `http://127.0.0.1:4173/` 응답 확인 |
| 확인 라우트 | Pass | `/`, `/devices`, `/simulation`, `/telemetry`, `/servers` |
| `/telemetry` DOM | Pass | `scrollWidth=1150`, `clientWidth=1150`, `overflowX=false`, `canvasCount=3` |

## 2. 스크린샷 근거

| route | 화면 | 스크린샷 경로 |
|---|---|---|
| `/` | 메인 관제 그래프 | `/home/quincy/.hermes/browser_screenshots/browser_screenshot_827e417f.png` |
| `/devices` | 장비 상태 | `/home/quincy/.hermes/browser_screenshots/browser_screenshot_57ecec66.png` |
| `/simulation` | 공정 시뮬레이션 | `/home/quincy/.hermes/browser_screenshots/browser_screenshot_441fd8d7.png` |
| `/telemetry` | 운영 데이터 | `/home/quincy/.hermes/browser_screenshots/browser_screenshot_f12f3408.png` |
| `/servers` | 게이트웨이 / 서버 | `/home/quincy/.hermes/browser_screenshots/browser_screenshot_cdb86e72.png` |

## 3. 전체 Pass / Fail 표

| 검수 기준 | 판정 | 근거 | 수정 필요 |
|---|---|---|---|
| 현대적이고 깔끔한 톤 | Pass | 흰색 패널, 절제된 색상, 라운드, 그림자 톤이 통일되어 있다. | 낮음 |
| 누운 3D 바닥판 배제 | Pass | `/simulation`에서도 실제 3D 바닥판보다 평면형/카드형 구성에 가깝다. | 낮음 |
| 요소 겹침 방지 | Fail | `/` 메인 그래프에서 중앙 강조 노드가 일부 연결선과 주변 라벨을 가린다. `/simulation` 하단 3열 카드도 밀도가 높다. | 높음 |
| 사각형 아이콘 박스/테두리 반복감 제거 | Partial | 기존의 정사각형 아이콘 나열은 줄었지만, 카드·배지·버튼이 모두 둥근 사각형 패턴이라 `/servers`와 `/simulation`에서 반복감이 남는다. | 중간 |
| 장비/서버 역할 명확성 | Partial | `/devices`는 장비 역할이 명확하다. `/`와 `/servers`는 흐름/통신 계층이 보이나 Gateway, WebSocket, Modbus, ROS2 책임 분리가 더 필요하다. | 중간 |
| Vue Router 페이지 구조 | Pass | 주요 라우트 직접 접근과 내비게이션 전환이 확인됐다. | 낮음 |
| Chart.js 제한 사용 | Pass | Chart.js는 `/telemetry` 중심으로 3개 canvas가 확인됐다. `/servers`는 sparkline 위주라 과하지 않다. | 낮음 |
| 모의/live 상태 노출 | Pass | 모의 모드, 모의 게이트웨이, 모의 데이터 문구가 숨겨지지 않는다. | 낮음 |
| 언어 품질 | Partial | 한국어 중심이나 `/telemetry`의 `Active alarms and exceptions`, `/servers`의 `EDGE`, `Chart.js` 설명 등 일부 영어/개발자 문구가 남아 있다. | 중간 |
| 첫 화면 정보 우선순위 | Partial | `/devices`는 양호하다. `/telemetry`와 `/servers`는 핵심 차트/서버 카드가 첫 화면에서 더 잘 드러나도록 압축 여지가 있다. | 중간 |

## 4. 화면별 검수

### 4.1 `/` 메인 관제 그래프

판정: Fail 포함

Pass:
- Dobot, TurtleBot3, 컨베이어/힌지벨트, Raspberry Pi, RoboDK, Gateway/Server가 한 관제 장면에 배치되어 있다.
- 카드 색상과 상태 배지가 통일되어 있고, 임시 패치식 UI 느낌은 크지 않다.
- Chart.js 과사용은 보이지 않는다.

Fail / 보완:
- 중앙 강조 노드가 주변 연결선과 일부 라벨을 가린다.
- 연결선이 교차하면서 물류 흐름, 제어 흐름, 데이터 흐름의 우선순위가 한눈에 분리되지 않는다.
- 현재 형태는 네트워크 맵이라기보다 카드형 노드 모음처럼 보이는 구간이 있다.

수정 지시:
1. `ControlGraph` 또는 메인 그래프 SVG에서 중앙 노드 크기와 연결선 z-index를 조정한다.
2. 물류/제어/데이터 흐름선을 색상뿐 아니라 dash, 굵기, 화살표 모양으로 분리한다.
3. 노드 hover 시 전체 선을 움직이기보다 선택 노드와 직접 연결된 선만 강조한다.
4. 라벨은 노드 내부 중앙 정렬보다 노드 바깥 고정 anchor에 배치해 겹침을 줄인다.
5. 첫 viewport 1150x727 기준으로 핵심 노드 10개가 모두 보이고, 텍스트가 겹치지 않는지 다시 확인한다.

### 4.2 `/devices` 장비 상태

판정: Pass

Pass:
- 라우트 전환이 자연스럽고 장비 카드 간 간격이 충분하다.
- Dobot, TurtleBot3, 컨베이어, Raspberry Pi, RoboDK, Gateway/Bridge류 역할 구분이 읽힌다.
- 카드 과밀, 겹침, 가로 오버플로우가 보이지 않는다.
- 차트 과사용이 없다.

보완:
- 반복되는 둥근 사각 카드 구조는 유지해도 되지만, 로봇/이송/비전/서버 계층별 색상 rail 또는 작은 아이콘 실루엣을 추가하면 스캔 속도가 빨라진다.

수정 지시:
1. 장비 category별로 왼쪽 얇은 rail 색상을 부여한다.
2. 서버류 장비는 `/servers` 상세로 이어지는 링크/CTA를 명확히 유지한다.
3. 장비 상태 필드는 현재처럼 텍스트 우선으로 두고 아이콘만 있는 표현은 추가하지 않는다.

### 4.3 `/simulation` 공정 시뮬레이션

판정: Partial / Fail 포함

Pass:
- RoboDK와 디지털 트윈 메시지는 전달된다.
- 실제 연동 전 모의/mock 상태를 숨기지 않는다.
- 차트 과사용은 없다.

Fail / 보완:
- SVG 흐름도와 단계 카드가 함께 보이는 구간에서 하단 3열 레이아웃이 빽빽하다.
- 공정 흐름의 핵심 단계가 카드 묶음에 묻혀 한 번에 읽히지 않는다.
- RoboDK가 실제 제어 주체인지 검증/시뮬레이션 계층인지 더 명확히 분리할 필요가 있다.

수정 지시:
1. 하단 3열 카드를 2열 + 보조 로그 구조로 줄이거나, 주요 흐름 1열 timeline으로 바꾼다.
2. RoboDK는 `시뮬레이션/검증 계층` 배지로 고정 표기한다.
3. 실제 라인 상태와 twin 상태 차이는 별도 `Mismatch` 영역으로 분리한다.
4. 단계 카드의 제목, 상태, 최근 갱신만 남기고 설명문 길이를 줄인다.
5. `/simulation` 첫 화면에서 공정 흐름 SVG가 카드보다 먼저 읽히도록 상단 여백과 대비를 조정한다.

### 4.4 `/telemetry` 운영 데이터

판정: Pass / 일부 보완

Pass:
- Chart.js canvas 3개가 확인되어 지표 전용 페이지 기준에 맞는다.
- DOM 기준 가로 오버플로우가 없다.
- 카드/차트 겹침은 보이지 않는다.
- 기술 용어를 제외하면 한국어 정리는 대체로 유지되어 있다.

보완:
- 첫 화면에서는 실제 차트보다 상단 설명/카드가 더 먼저 보인다.
- `Active alarms and exceptions`, `Alarms`, `WARN`, `fallback`, `gateway`, `modbus` 등 영어 잔여가 있다. `WARN`, `gateway`, `modbus`는 로그 source/severity로 허용 가능하지만 제목 문구는 한국어화가 낫다.

수정 지시:
1. `Active alarms and exceptions`를 `활성 알람과 예외`로 바꾼다.
2. 첫 화면에서 차트 1개 이상이 더 명확히 보이도록 상단 요약 카드 높이를 줄인다.
3. 로그 source/severity는 기술값으로 유지하되, 섹션 제목과 설명문은 한국어로 맞춘다.
4. Chart.js는 현재 3개 수준을 유지하고 추가 차트는 만들지 않는다.

### 4.5 `/servers` 게이트웨이 / 서버

판정: Partial

Pass:
- Gateway API, WebSocket Stream, Modbus Bridge, ROS 2 Bridge 카드가 분리되어 있다.
- 모의 모드와 모의 데이터 상태가 보인다.
- Chart.js 대신 sparkline 중심으로 구성되어 서버 화면이 과하게 무겁지 않다.

보완:
- 각 계층의 책임이 카드 안에서는 보이나, 첫눈에 `명령/스냅샷`, `실시간 스트림`, `PLC/I/O`, `로봇 토픽`으로 분리되지는 않는다.
- 둥근 사각 카드와 배지가 반복되어 화면이 모듈 조립식처럼 보이는 구간이 있다.
- `Chart.js 대신 경량 sparkline...` 문장은 운영 화면보다 개발 메모에 가깝다.
- `EDGE`, `STREAM`, `FIELD BUS`, `ROBOTICS` 같은 라벨은 허용 가능하지만 한국어 화면에서는 약간 튄다.

수정 지시:
1. Gateway/WebSocket/Modbus/ROS2 4개 카드를 같은 카드 반복 대신 계층형 topology 또는 timeline 형태로 바꾼다.
2. 각 계층 카드 상단에 한 줄 책임을 고정한다: `REST 명령/스냅샷`, `실시간 이벤트`, `PLC/I/O`, `ROS2 토픽/서비스`.
3. `Chart.js 대신 경량 sparkline...` 문장은 사용자용 문장으로 바꾼다. 예: `연결 추세만 간단히 표시합니다.`
4. `EDGE`, `STREAM`, `FIELD BUS`, `ROBOTICS` 라벨은 `게이트웨이`, `스트림`, `현장 버스`, `로봇 브리지`로 바꾸거나 한글 병기를 쓴다.
5. 연결 실패 표시는 상태 색상만 쓰지 말고 마지막 성공 시각과 원인 텍스트를 같이 둔다.

## 5. 우선순위별 수정 지시 목록

### P1. 겹침/가독성

대상:
- `/` 메인 관제 그래프
- `/simulation` 하단 카드/흐름도

수정 범위:
- 메인 그래프 노드 크기, 연결선 z-index, 라벨 anchor 조정
- `/simulation` 단계 카드 밀도 축소
- 1150x727 기준 첫 화면 재검수

완료 기준:
- 핵심 노드와 라벨이 겹치지 않는다.
- 연결선은 물류/제어/데이터 흐름별로 구분된다.
- `/simulation`에서 공정 흐름 SVG가 먼저 읽힌다.

### P2. 역할 분리 표현

대상:
- `/servers`
- `/` 메인 관제 그래프의 Gateway/Bridge 노드

수정 범위:
- Gateway/WebSocket/Modbus/ROS2 책임 문구 고정
- 서버 계층 topology 또는 timeline 표현 보강
- 모의/live 상태 유지

완료 기준:
- Gateway는 REST 명령/스냅샷, WebSocket은 실시간 이벤트, Modbus는 PLC/I/O, ROS2는 로봇 토픽/서비스로 한눈에 구분된다.
- 연결 실패 시 상태, 원인, 마지막 성공 시각이 함께 보인다.

### P3. 언어/운영 문구 정리

대상:
- `/telemetry`
- `/servers`

수정 범위:
- `Active alarms and exceptions` 등 제목 문구 한국어화
- 개발 메모처럼 보이는 `Chart.js 대신...` 문장 제거 또는 사용자용 문장으로 변경
- 기술 source/severity 값은 유지

완료 기준:
- 제목과 설명은 한국어 중심이다.
- 로그 source, protocol, severity처럼 기술값으로 필요한 영어만 남는다.

### P4. 카드 반복감 완화

대상:
- `/devices`
- `/servers`
- `/simulation`

수정 범위:
- 계층별 rail, timeline, topology, 실루엣 등으로 카드 변주 추가
- 배지/버튼형 요소 과다 사용 줄이기

완료 기준:
- 모든 정보가 같은 둥근 사각 카드처럼 보이지 않는다.
- 로봇/이송/비전/서버 계층이 스캔만으로 구분된다.

## 6. 후속 보완 카드 제안

실패/부분 통과 항목이 있어 구현 보완 카드를 별도로 둘 수 있다.

제안 카드 1:
- 제목: `P2-디자인 보완: 메인 관제 그래프 겹침 제거 및 흐름선 가독성 개선`
- assignee: `coding`
- 범위: `WebSocket/src/components/MainLanding.vue`, 그래프/노드/edge 관련 컴포넌트와 스타일
- 완료 기준: 1150x727 기준 노드/라벨 겹침 없음, 물류/제어/데이터 흐름선 구분, `npm run build && npm run smoke` 통과

제안 카드 2:
- 제목: `P2-디자인 보완: simulation/servers 카드 반복감과 역할 분리 개선`
- assignee: `coding`
- 범위: `/simulation`, `/servers` page 컴포넌트와 관련 스타일
- 완료 기준: `/simulation` 흐름도 우선순위 개선, `/servers` Gateway/WebSocket/Modbus/ROS2 책임 분리, 개발자 문구 제거, `npm run build && npm run smoke` 통과

제안 카드 3:
- 제목: `P3-문구 정리: telemetry/servers 영어 잔여와 운영 문구 정리`
- assignee: `coding`
- 범위: `/telemetry`, `/servers` 제목/설명/라벨 문자열
- 완료 기준: 기술값을 제외한 제목/설명 한국어화, 로그 source/severity 유지, 빌드 통과

## 7. 결론

현재 구현은 Vue Router 기반 화면 분리, 빌드/스모크, 주요 라우트 접근, Chart.js 제한 사용 기준을 통과했다. 다만 사용자 요구 중 `요소 겹침 없음`, `사각 카드 반복감 축소`, `서버/브리지 역할의 즉시 구분`은 아직 부분 실패 또는 보완 대상이다. 다음 작업은 메인 그래프와 `/simulation`의 가독성 보완을 먼저 처리하고, 그 뒤 `/servers` 역할 분리와 문구 정리를 진행하는 순서가 적절하다.
