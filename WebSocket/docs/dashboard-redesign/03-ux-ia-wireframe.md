# Throughline 로봇 관제 대시보드 IA / 와이어프레임 / 디자인 토큰

## 1. 문서 목적

이 문서는 `WebSocket/` 프론트를 Vue Router 기반 다중 페이지 관제 대시보드로 재구성하기 위한 구현 기준이다.

기준 범위:
- 메인 관제 그래프와 장비/서버 상태를 한 화면에서 이해할 수 있는 정보 구조
- Vue Router route 단위 페이지 정의
- 구현 카드가 바로 따라갈 수 있는 컴포넌트 목록과 acceptance criteria
- 색상, spacing, typography, glass/blur 사용 기준
- 사각 아이콘 박스 대신 사용할 시각 표현 방식

확인한 현재 상태:
- `WebSocket/package.json`에는 `vue`, `chart.js`, `gsap`, `pixi.js`가 있고 `vue-router`는 아직 없다.
- 현재 `src/App.vue`는 `activePage` 상태값으로 `home`, `overview`, `flow`, `camera`, `robot`, `comm`, `history` 화면을 분기한다.
- 현재 `src/components/MainLanding.vue`는 Dobot, TurtleBot, 생산 라인, 클라우드, 디바이스 계층, 데이터 분석을 하나의 관제 장면으로 배치한다.
- 선행 리서치 카드는 이 문서 작성 시점에 완료 산출물이 없어, 현재 repo와 카드 본문 기준으로 설계한다.

## 2. 디자인 원칙

### 2.1 유지할 방향

- 메인 화면은 장비 나열이 아니라 흐름 중심 관제 그래프다.
- Dobot Magician, TurtleBot3 Waffle Pi, 힌지벨트/컨베이어, Raspberry Pi, RoboDK, Gateway/Server가 한 관제 흐름 안에서 보여야 한다.
- 배치는 넓고 명확해야 하며, 각 노드는 겹치지 않아야 한다.
- 투명/글래스 느낌은 배경 보조 수준으로만 사용한다.
- 마우스 hover, selected, active 상태는 위치 이동보다 밝기, 선 강조, 작은 elevation으로 표현한다.
- Chart.js는 `/telemetry`의 핵심 지표와 `/` 요약 미니차트 정도에만 제한한다.

### 2.2 금지할 방향

- 누운 3D 바닥판을 기본 구도로 쓰지 않는다.
- 요소가 서로 겹쳐 보이는 배치를 쓰지 않는다.
- 임시 패치처럼 보이는 UI 조각을 끼워 넣지 않는다.
- 정사각형 아이콘 박스, 두꺼운 테두리 아이콘 카드, 라벨 없는 아이콘 나열을 쓰지 않는다.
- 모든 페이지에 차트를 과하게 넣지 않는다.

## 3. Vue Router IA

구현 기준 route:

| route | 목적 | 주요 사용자 질문 |
|---|---|---|
| `/` | 메인 관제 그래프와 전체 상태 overview | 지금 라인이 정상인가? 어느 장비/서버가 막혔나? |
| `/devices` | 장비 목록과 장비별 상세 | Dobot/TurtleBot/컨베이어/Raspberry Pi가 어떤 상태인가? |
| `/simulation` | RoboDK / 디지털 트윈 상태 | 시뮬레이션과 실제 라인 상태가 어떻게 연결되는가? |
| `/telemetry` | Chart.js 기반 지표 | 처리량, 사이클, 품질, 지연이 어떻게 변하는가? |
| `/servers` | Gateway, WebSocket, Modbus, ROS2 bridge 상태 | 통신 계층 중 어디가 연결/지연/오류인가? |
| `/logs` | 이벤트 로그와 제어 기록 | 최근 알람, 명령, 상태 변화가 무엇인가? |
| `/settings` | 운영 설정과 제어 옵션 | 게이트웨이 주소, 모의/실시간 모드, 안전 옵션을 어디서 바꾸는가? |

권장 route 파일 구조:

```text
src/
  router/
    index.ts
    routes.ts
  layouts/
    DashboardLayout.vue
  pages/
    HomeOverviewPage.vue
    DevicesPage.vue
    SimulationPage.vue
    TelemetryPage.vue
    ServersPage.vue
    LogsPage.vue
    SettingsPage.vue
  components/
    dashboard/
      ControlGraph.vue
      StatusRibbon.vue
      NodeInspector.vue
      FlowLegend.vue
    devices/
      DeviceList.vue
      DeviceDetailPanel.vue
      DeviceHealthStrip.vue
    telemetry/
      MetricSummaryCards.vue
      MetricTrendChart.vue
    servers/
      ServerTopology.vue
      BridgeStatusTable.vue
    logs/
      EventTimeline.vue
      CommandAuditList.vue
```

현재 `activePage` 분기는 다음처럼 route로 매핑한다.

| 현재 page key | 새 route | 비고 |
|---|---|---|
| `home` | `/` | `MainLanding.vue`의 장면 구조를 `ControlGraph.vue`로 분리 |
| `overview` | `/` 또는 `/telemetry` 일부 | 요약 카드는 home 상단, 상세 차트는 telemetry로 이동 |
| `flow` | `/` 또는 `/devices` | 공정 흐름은 home graph의 중심 레이어로 흡수 |
| `camera` | `/devices?device=vision` | 비전 카메라는 장비 상세로 이동 |
| `robot` | `/devices?device=dobot` | Dobot/TurtleBot 상세는 devices로 이동 |
| `comm` | `/servers` | REST/WebSocket/Modbus/ROS2 bridge 상태로 확장 |
| `history` | `/logs` | 이벤트/알람/명령 이력으로 이동 |

## 4. 전역 레이아웃

`DashboardLayout.vue`는 모든 route에서 유지한다.

구성:
1. 상단 `StatusRibbon`
   - 라인 상태, 게이트웨이 연결, 최근 동기화, 알람 수
   - 페이지 이동 중에도 고정 위치 유지
2. 좌측 또는 상단 `RouteNav`
   - `/`, `/devices`, `/simulation`, `/telemetry`, `/servers`, `/logs`, `/settings`
   - 좁은 화면에서는 상단 pill navigation으로 전환
3. 본문 route outlet
   - 각 페이지는 `page-title`, `page-actions`, `page-body` 3영역을 기본으로 둔다.
4. 우측 `NodeInspector`는 `/`에서만 상시 노출하고, 다른 페이지에서는 선택 시 drawer로 표시한다.

레이아웃 기준:

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ StatusRibbon: line / gateway / websocket / modbus / latest sync / alarms   │
├──────────────┬───────────────────────────────────────────────┬─────────────┤
│ RouteNav     │ Route content                                  │ Context     │
│              │                                               │ panel       │
│ /            │                                               │             │
│ /devices     │                                               │             │
│ /simulation  │                                               │             │
│ /telemetry   │                                               │             │
│ /servers     │                                               │             │
│ /logs        │                                               │             │
│ /settings    │                                               │             │
└──────────────┴───────────────────────────────────────────────┴─────────────┘
```

## 5. `/` 메인 관제 그래프

### 5.1 화면 목표

`/`는 장비와 서버를 한 장의 관제 그래프로 보여준다. 사용자는 첫 화면에서 다음을 바로 알아야 한다.

- 물류 흐름: TurtleBot → 입고 → 컨베이어/힌지벨트 → 비전 → Dobot → 배출
- 제어 흐름: 사용자/관제센터 → Node Gateway → ROS2/Modbus bridge → 장비
- 데이터 흐름: 장비/Raspberry Pi/비전/RoboDK → Gateway/WebSocket → 대시보드/Telemetry
- 문제 위치: 장비, 통신, 서버, 시뮬레이션 중 어느 계층이 degraded인지

### 5.2 ASCII 와이어프레임

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Throughline Control Room                                   [모의/실시간] [동기화] │
│ Dobot · TurtleBot · Conveyor · Raspberry Pi · RoboDK · Gateway 상태 관제       │
├──────────────────────────────────────────────────────────────────────────────┤
│ [라인 상태 RUNNING] [처리량 00 ppm] [알람 0] [Gateway online] [Modbus mock]     │
├───────────────────────┬──────────────────────────────────────┬───────────────┤
│ 장비 상태 요약          │ 메인 관제 그래프                        │ 선택 노드       │
│                       │                                      │               │
│  TurtleBot  ready     │  TurtleBot                            │ Dobot Magician │
│  Dobot      running   │      │ 물류 흐름                         │ 상태: running  │
│  Conveyor   running   │      ▼                                 │ 최근 명령: pick │
│  RPi        online    │  ┌────────┐      ┌──────────┐          │ 지연: 00 ms    │
│  RoboDK     sync      │  │ 입고    │ ───▶ │ 컨베이어 │          │               │
│  Gateway    online    │  └────────┘      └────┬─────┘          │ [상세 열기]    │
│                       │                       ▼                │ [로그 보기]    │
│                       │               ┌─────────────┐          │               │
│ 흐름 범례              │               │ 비전/RPi     │          │ 관련 서버       │
│ ━ 물류                 │               └──────┬──────┘          │ Gateway        │
│ ━ 제어                 │                      ▼                 │ ROS2 bridge    │
│ ━ 데이터               │              ┌──────────────┐          │ Modbus bridge  │
│                       │              │ Dobot        │          │ WebSocket      │
│                       │              └──────┬───────┘          │               │
│                       │                     ▼                  │               │
│                       │              ┌──────────────┐          │               │
│                       │              │ 배출/분류     │          │               │
│                       │              └──────────────┘          │               │
│                       │                                      │               │
│                       │  Control Center ──▶ Node Gateway ──▶ Bridges         │
│                       │         ▲               │              ▲             │
│                       │         └──── WebSocket/Telemetry ◀────┘             │
├───────────────────────┴──────────────────────────────────────┴───────────────┤
│ 최근 이벤트: [INFO] Gateway snapshot loaded · [WARN] Modbus mock mode ...      │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 그래프 레이어

- `GraphCanvas`: 전체 SVG 또는 HTML absolute layout 컨테이너
- `MaterialFlowLayer`: TurtleBot, 입고, 컨베이어, 비전, Dobot, 배출 연결선
- `ControlFlowLayer`: 관제센터, Node Gateway, bridge, 장비 제어 연결선
- `DataFlowLayer`: Raspberry Pi, RoboDK, Telemetry, WebSocket 연결선
- `GraphNode`: 장비/서버 노드 공통 표현
- `GraphEdge`: 물류/제어/데이터 흐름선 공통 표현
- `NodeInspector`: 선택 노드 상세
- `FlowLegend`: 흐름선 색상과 의미

### 5.4 그래프 노드 기본 배치

| 노드 | 위치 기준 | 클릭 이동 |
|---|---|---|
| TurtleBot3 Waffle Pi | 왼쪽 상단, 입고 전 단계 | `/devices?device=turtlebot3` |
| 입고 스테이션 | 중앙 왼쪽 | `/devices?device=infeed` |
| 힌지벨트/컨베이어 | 중앙 | `/devices?device=conveyor` |
| Raspberry Pi + 비전 | 중앙 상단 또는 컨베이어 위 | `/devices?device=raspberry-pi` |
| Dobot Magician | 중앙 오른쪽 | `/devices?device=dobot-magician` |
| 배출/분류 | 오른쪽 하단 | `/devices?device=outfeed` |
| RoboDK | 오른쪽 상단, 디지털 트윈 계층 | `/simulation` |
| Node Gateway | 하단 중앙 | `/servers?server=gateway` |
| ROS2 bridge | 하단 오른쪽 | `/servers?server=ros2-bridge` |
| Modbus bridge | 하단 오른쪽 | `/servers?server=modbus-bridge` |
| WebSocket server | 하단 왼쪽 또는 Gateway 옆 | `/servers?server=websocket` |

### 5.5 `/` acceptance criteria

- 첫 viewport에서 모든 핵심 노드가 겹치지 않는다.
- 장비 흐름과 서버/통신 흐름이 색상과 선 스타일로 구분된다.
- 노드 hover 시 해당 노드와 연결선만 강조된다.
- 노드 click 시 `NodeInspector` 내용이 바뀌고 상세 route로 이동할 수 있다.
- 화면 폭이 좁아지면 그래프는 2열 카드형 흐름으로 접히며 텍스트가 겹치지 않는다.
- Chart.js는 요약 sparkline 또는 1개 미니 추이 정도만 쓴다.

## 6. `/devices` 장비 페이지

### 6.1 목적

Dobot, TurtleBot3, 컨베이어, Raspberry Pi, 비전, 배출부, 서버형 장치를 목록과 상세로 확인한다.

### 6.2 구성 컴포넌트

- `DeviceFilterTabs`: 전체, 로봇, 이송, 비전, 서버, 센서
- `DeviceList`: 장비 목록과 상태 pill
- `DeviceDetailPanel`: 선택 장비 상세
- `DeviceHealthStrip`: 연결, 전원, 마지막 갱신, 오류 상태
- `DeviceCommandPanel`: 허용된 mock/control 명령
- `DeviceEventMiniLog`: 선택 장비 이벤트

### 6.3 장비 기본 항목

| id | 표시명 | category | 핵심 필드 |
|---|---|---|---|
| `dobot-magician` | Dobot Magician | robot | pose, mode, command, error |
| `turtlebot3-waffle-pi` | TurtleBot3 Waffle Pi | mobile_robot | battery, nav_state, payload |
| `hinge-belt` | 힌지벨트/컨베이어 | conveyor | speed, direction, load |
| `raspberry-pi` | Raspberry Pi | edge | cpu, temp, camera_state |
| `vision-camera` | 비전 카메라 | vision | fps, inference_latency, result |
| `robodk` | RoboDK | simulation | sync_state, scenario, last_update |
| `gateway` | Node Gateway | server | rest, websocket, uptime |
| `modbus-bridge` | Modbus Bridge | server | mode, polling, register_error |
| `ros2-bridge` | ROS2 Bridge | server | topics, services, heartbeat |

### 6.4 `/devices` acceptance criteria

- 장비 목록에서 상태, 마지막 갱신, 담당 계층을 한 줄로 볼 수 있다.
- 장비를 선택하면 우측 상세가 즉시 바뀐다.
- Dobot, TurtleBot3, 컨베이어, Raspberry Pi는 최소 1개 이상의 장비별 상태 필드를 가진다.
- 서버류 장비는 `/servers` 상세로 이동하는 링크를 가진다.
- 제어 버튼은 mock/live 여부와 위험도를 명확히 표시한다.

## 7. `/simulation` RoboDK / 디지털 트윈

### 7.1 목적

RoboDK와 실제 공정 상태의 연결을 따로 보여준다. 실제 연동 전이라면 mock sync 상태를 명확히 표기한다.

### 7.2 구성 컴포넌트

- `SimulationStatusCard`: RoboDK 연결, 시나리오, 마지막 sync
- `TwinScenePreview`: 실제 3D 바닥판이 아니라 평면/등각 축소 미리보기
- `ScenarioTimeline`: 작업 단계와 시뮬레이션 단계 매핑
- `MismatchList`: 실제 상태와 twin 상태 차이

### 7.3 `/simulation` acceptance criteria

- RoboDK가 실제 제어 주체인지, 시뮬레이션/검증 계층인지 구분한다.
- 실제 연동이 없으면 `mock` 또는 `not connected`를 숨기지 않는다.
- 메인 그래프와 동일한 상태 색상을 쓴다.

## 8. `/telemetry` 지표 페이지

### 8.1 목적

Chart.js를 사용하는 지표 전용 페이지다. 생산량, 사이클, 품질, 연결 지연을 시간 흐름으로 본다.

### 8.2 구성 컴포넌트

- `MetricSummaryCards`: 처리량, 사이클, 품질, 알람 수
- `MetricTrendChart`: Chart.js line chart
- `LatencyChart`: Gateway/WebSocket/Modbus/ROS2 지연
- `QualityBreakdown`: 양품/불량/미판정 비율
- `MetricRangeSelector`: 최근 5분, 15분, 1시간, 전체 mock

### 8.3 차트 사용 기준

- home에는 핵심 상태 판단용 미니 차트만 둔다.
- telemetry에는 2~4개 차트까지 허용한다.
- 동일 데이터의 중복 차트는 만들지 않는다.
- 차트 색상은 status token과 연결하되, 너무 많은 색을 쓰지 않는다.

### 8.4 `/telemetry` acceptance criteria

- Chart.js canvas는 빈 데이터, mock 데이터, live 데이터 상태를 각각 표시한다.
- x축 단위와 마지막 갱신 시간이 보인다.
- 핵심 수치 카드는 차트보다 위에 있어야 한다.

## 9. `/servers` 서버/브리지 상태

### 9.1 목적

Gateway, WebSocket, Modbus, ROS2 bridge의 연결 상태를 통신 계층별로 보여준다.

### 9.2 구성 컴포넌트

- `ServerTopology`: dashboard → gateway → bridge → device 연결도
- `BridgeStatusTable`: REST, WebSocket, Modbus, ROS2 상태 표
- `EndpointCard`: endpoint, mode, heartbeat, last error
- `RegisterMapPreview`: Modbus register 요약
- `RosTopicPreview`: ROS2 topic/service 요약

### 9.3 `/servers` acceptance criteria

- Gateway/WebSocket/Modbus/ROS2 bridge가 한 화면에서 구분된다.
- mock/live 모드가 숨겨지지 않는다.
- 연결 실패는 빨간색만이 아니라 원인 텍스트와 마지막 성공 시각을 함께 보여준다.
- `/logs`로 이어지는 오류 로그 링크가 있다.

## 10. `/logs` 이벤트 로그

### 10.1 목적

알람, 명령, 상태 변경을 시간순으로 추적한다.

### 10.2 구성 컴포넌트

- `EventTimeline`: 시간순 이벤트
- `SeverityFilter`: INFO/WARN/ERROR
- `SourceFilter`: gateway, websocket, modbus, ros2, device, command
- `CommandAuditList`: 사용자가 누른 제어 명령 기록
- `AlarmAcknowledgePanel`: 확인 처리 상태

### 10.3 `/logs` acceptance criteria

- 이벤트는 시간, source, severity, message를 반드시 가진다.
- 필터 변경 시 결과 수가 보인다.
- 제어 명령 이벤트와 장비 상태 이벤트를 구분한다.

## 11. `/settings` 설정

### 11.1 목적

운영 중 바꿔야 하는 값만 좁게 제공한다.

### 11.2 구성 컴포넌트

- `GatewaySettingsForm`: gateway base URL
- `RuntimeModeToggle`: mock/live 표시와 전환
- `SafetyOptions`: 위험 명령 확인 옵션
- `DisplayPreferences`: density, motion reduce

### 11.3 `/settings` acceptance criteria

- 위험한 제어 옵션은 기본 off 또는 확인 절차를 둔다.
- URL 입력은 현재 `gatewayUrl` 흐름과 호환되어야 한다.
- 설정 변경 결과는 `/logs`에 이벤트로 남긴다.

## 12. 디자인 토큰

### 12.1 색상

현재 `src/styles.css`의 방향을 유지하되, token 이름을 구현에서 명확히 쓴다.

```css
:root {
  --color-bg: #eef3f6;
  --color-bg-soft: #f7fafc;
  --color-panel: rgba(255, 255, 255, 0.90);
  --color-panel-strong: #ffffff;
  --color-text: #172033;
  --color-muted: #667085;
  --color-border: rgba(31, 46, 70, 0.12);
  --color-navy: #16324f;
  --color-accent-cyan: #0f9db3;
  --color-accent-green: #1aa987;
  --color-good: #15936f;
  --color-warn: #c7831c;
  --color-danger: #c84d42;
  --color-neutral: #64748b;

  --flow-material: #1aa987;
  --flow-control: #0f9db3;
  --flow-data: #4866d6;
}
```

상태 색상 기준:

| 상태 | token | 용도 |
|---|---|---|
| normal/running/online | `--color-good` | 정상, 실시간 연결 |
| warning/degraded/mock | `--color-warn` | 지연, mock, 주의 |
| error/offline/fault | `--color-danger` | 장애, 연결 실패 |
| idle/unknown | `--color-neutral` | 대기, 미확정 |

### 12.2 spacing

```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
}
```

적용 기준:
- 카드 내부 padding: `--space-5` 또는 `--space-6`
- 페이지 간 gap: `--space-4` 이상
- 그래프 노드 간 최소 여백: desktop 28px, tablet 20px, mobile 14px
- 상단 header와 본문 간격: `--space-4`

### 12.3 typography

```css
:root {
  --font-sans: Pretendard, Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-md: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.35rem;
  --text-2xl: clamp(1.7rem, 2.4vw, 2.7rem);
  --tracking-tight: -0.04em;
}
```

적용 기준:
- 한국어 라벨은 굵기만으로 과하게 강조하지 않는다.
- 숫자 지표는 `font-variant-numeric: tabular-nums;`를 쓴다.
- route 제목은 한 줄, 설명은 1~2줄로 제한한다.

### 12.4 radius / shadow / blur

```css
:root {
  --radius-sm: 12px;
  --radius-md: 18px;
  --radius-lg: 28px;
  --shadow-panel: 0 24px 70px rgba(31, 46, 70, 0.12);
  --shadow-hover: 0 28px 82px rgba(31, 46, 70, 0.16);
  --blur-panel: 14px;
}
```

사용 기준:
- glass panel은 `background: rgba(255,255,255,0.86~0.94)` 범위에서만 사용한다.
- `backdrop-filter`는 주요 panel에만 쓰고, nested card에는 반복하지 않는다.
- hover elevation은 2px 이동 또는 shadow 변화 정도로 제한한다.

## 13. 사각 아이콘 박스 금지의 대체 표현

금지:
- 모든 장비를 같은 정사각형 테두리 안에 넣는 방식
- 아이콘만 있고 기능/상태가 바로 읽히지 않는 방식
- 테두리 두께와 그림자만으로 계층을 나누는 방식

대체:
1. 장비 실루엣
   - Dobot: base, joint, arm, gripper를 단순 shape로 표현
   - TurtleBot: 원형/타원형 body와 lidar cap으로 표현
   - 컨베이어: belt line, roller dot, moving pallet으로 표현
   - Raspberry Pi/비전: board dot, camera lens, signal pulse로 표현
2. 상태 pill
   - 노드 내부가 아니라 노드 옆 작은 pill로 `online`, `mock`, `fault` 표시
3. 흐름선 중심 표현
   - 노드보다 edge를 더 중요한 정보로 본다.
   - 물류/제어/데이터 흐름은 선 색상, dash, marker로 구분한다.
4. 텍스트 우선
   - 라벨과 상태 문구를 아이콘보다 먼저 읽히게 한다.
5. 카드 대신 앵커 노드
   - 배경은 투명에 가깝게 두고, 작은 glow/underline/rail로 활성 상태를 표현한다.

권장 node shape 예:

```text
Dobot       : base + 2-segment arm + gripper
TurtleBot   : rounded capsule + lidar cap + soft shadow
Conveyor    : horizontal belt + moving pallet dots
RaspberryPi : small board silhouette + camera lens + signal rings
Gateway     : stacked server lines + pulse dot
RoboDK      : twin outline + sync ring
```

## 14. 데이터 모델 기준

route와 컴포넌트는 mock/live를 같은 shape로 받아야 한다.

```ts
export type HealthState = 'running' | 'ready' | 'warning' | 'error' | 'offline' | 'mock';

export interface DashboardNode {
  id: string;
  label: string;
  kind: 'robot' | 'mobile_robot' | 'conveyor' | 'vision' | 'edge' | 'server' | 'simulation' | 'sensor';
  state: HealthState;
  route: string;
  summary: string;
  updatedAt: string;
}

export interface DashboardEdge {
  id: string;
  source: string;
  target: string;
  kind: 'material' | 'control' | 'data';
  state: HealthState;
  label?: string;
}
```

## 15. 구현 순서 제안

1. `vue-router` 추가 및 `src/router/index.ts` 생성
2. `DashboardLayout.vue` 생성
3. 기존 `activePage` 화면을 route page로 분리
4. `MainLanding.vue`의 그래프 장면을 `ControlGraph.vue`로 분리
5. 장비/서버/telemetry mock data shape를 `shared/telemetry`와 맞춤
6. `/devices`, `/servers`, `/telemetry`부터 구현
7. `/simulation`, `/logs`, `/settings` 구현
8. 반응형과 reduced-motion 처리

## 16. 구현 카드용 acceptance criteria 요약

공통:
- 모든 route는 직접 URL 접근이 가능해야 한다.
- 상단 status ribbon은 route 변경 후에도 유지된다.
- mock/live 상태는 숨기지 않는다.
- 기존 Gateway REST/WebSocket 흐름과 충돌하지 않는다.
- `npm run build`가 통과해야 한다.

`/`:
- 핵심 장비와 서버 노드가 한 관제 그래프 안에 표시된다.
- 물류/제어/데이터 흐름선이 구분된다.
- 선택 노드 inspector가 동작한다.

`/devices`:
- Dobot, TurtleBot3, 컨베이어, Raspberry Pi, RoboDK, Gateway/Bridge 항목이 보인다.
- 각 장비는 상태, 마지막 갱신, 상세 필드를 가진다.

`/simulation`:
- RoboDK 상태와 실제 라인 상태의 관계가 보인다.
- 실제 연동 전 mock/not connected 상태를 표시한다.

`/telemetry`:
- Chart.js 기반 핵심 지표가 표시된다.
- 빈 데이터와 mock 데이터를 구분한다.

`/servers`:
- Gateway, WebSocket, Modbus, ROS2 bridge 상태가 분리되어 보인다.
- endpoint와 마지막 오류/성공 시각을 표시한다.

`/logs`:
- 이벤트 source/severity/time 필터가 동작한다.
- 제어 명령 기록과 장비 이벤트가 구분된다.

`/settings`:
- gateway URL과 runtime mode를 안전하게 변경할 수 있다.
- 변경 이벤트가 logs로 이어진다.

## 17. 하지 말아야 할 구현

- React reference를 새 Vue 구조 안에 직접 섞지 않는다.
- 페이지 전환을 `activePage` 상태값만으로 계속 확장하지 않는다.
- 그래프 노드를 화면 중앙에 모두 겹쳐 배치하지 않는다.
- Chart.js를 상태 카드 대체물처럼 모든 화면에 넣지 않는다.
- 실제 연결이 없는데 online처럼 보이게 하지 않는다.
- 외부 배포, push, commit은 사용자 승인 없이 하지 않는다.
