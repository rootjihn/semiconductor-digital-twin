# 02. 도메인 비주얼 브리프

## 목적

메인 관제 그래프에서 실제 장비와 시스템을 추상 아이콘이 아니라 `장비 정체성이 바로 읽히는 SVG/컴포넌트`로 표현하기 위한 지시서다.

이 문서는 다음 5개 노드를 기준으로 작성한다.
- Dobot Magician
- TurtleBot3 Waffle Pi
- RoboDK
- 힌지벨트 컨베이어 + Raspberry Pi 비전
- Server / Gateway / Bridge

## 먼저 확정할 점

### 1) TurtleBot3 Waffle Pi는 `원형 AMR`보다 `사각 적층형 모바일 로봇`에 가깝다

공식 e-Manual의 Waffle Pi 하드웨어 사양과 시각 자료 기준으로, Waffle Pi의 인상은 원형 로봇청소기형이 아니라 `사각 플레이트 2~3단 적층 + 상단 LiDAR + 좌우 노출 휠`이다.

즉 메인 그래프에서는 다음처럼 수정하는 것이 맞다.
- 금지: 완전 원판형 AMR, 매끈한 원통형 자율주행 로봇
- 권장: 사각 플랫폼 위에 센서 타워가 올라간 ROS 모바일 로봇

### 2) RoboDK는 `장비`가 아니라 `시뮬레이션/오프라인 프로그래밍 노드`

RoboDK는 실제 하드웨어 아이콘처럼 그리면 안 된다. 공식 설명상 핵심은 아래다.
- robot simulation
- offline programming
- digital twin
- post processor 기반 프로그램 생성

즉 그래프에서는 `모니터/디지털 트윈 보드` 또는 `가상 셀`로 표현해야 한다.

### 3) 힌지벨트는 물류 컨베이어가 아니라 `산업용 메탈 힌지 슬랫 벨트` 인상이 중요하다

일반 러버 벨트보다 `금속 판이 힌지로 이어진 벨트`, `충격/스크랩 대응`, `수평+상승 구간 연결 가능` 이미지가 핵심이다.

## 공통 시각 규칙

### 공통 상태 색상
- RUNNING / ONLINE / OK: `#22c55e`
- IDLE / STANDBY: `#94a3b8`
- WARNING / DEGRADED: `#f59e0b`
- ERROR / FAULT / DISCONNECTED: `#ef4444`
- SIMULATION / VIRTUAL / DIGITAL-TWIN: `#8b5cf6`
- DATA STREAM / TELEMETRY: `#21c6ff`
- CONTROL / COMMAND: `#5dff8f`
- MATERIAL FLOW / PHYSICAL TRANSFER: `#ffd166`

### 연결선 의미
- 실선 파랑: telemetry / sensor / state stream
- 실선 초록: control / command / ack
- 굵은 황색 또는 amber 라인: material flow / physical handoff
- 보라 점선: simulation sync / offline program / digital twin link
- 빨강 점선: alarm / fault propagation / safety interlock

### hover 카드 공통 포맷
모든 노드는 hover 시 최소 아래 4줄을 보여준다.
- 장비명 / 시스템명
- 현재 상태
- 핵심 입출력 1~2개
- 최근 이벤트 또는 최근 갱신 시각

예시:
- `Dobot Magician`
- `RUNNING · Cycle 2.4s`
- `Tool: Gripper / Target: Infeed Tray`
- `Last update: 14:32:08`

## 1. Dobot Magician

### 출처 기반 핵심 사실
- Dobot 공식 페이지는 Magician을 `desktop grade 4-axis robot`로 설명한다.
- 공식 사양에는 `4 axis`, `payload 500 g`, `max reach 320 mm`, `repeatability ±0.2 mm`가 명시돼 있다.
- 공식 페이지는 gripper, rail, conveyor belt, mobility, vision module 같은 액세서리 확장을 명시한다.

### SVG 형태 지시
필수 형태 요소:
- 낮고 넓은 테이블형 베이스
- 베이스 위 중앙 기둥 1개
- 2단 링크 암
- 링크 사이 원형 관절 포인트 3개가 보이게 표현
- 끝단에 작은 vertical tool head 또는 gripper head
- 전체 실루엣은 `소형 4축 교육용 로봇 암`

권장 단순화:
- 베이스: 둥근 사각형 또는 낮은 원통
- shoulder link 1개 + forearm link 1개 + 짧은 wrist/tool 1개
- 병렬 링크 느낌을 얇은 보조 바 1개로만 암시

금지:
- 6축 산업용 협동로봇처럼 굵고 매끈한 대형 암
- 사람형 팔 비율
- 용접 로봇 같은 과도한 관절 수 표현

### 노드 라벨
- 기본 라벨: `DOBOT MAGICIAN`
- 보조 라벨: `Pick & Place / Teaching Arm`

### 상태 표현
- RUNNING: 베이스 halo 초록 + tool 끝단 미세 pulse
- IDLE: 본체 저채도 회색 + 관절 LED만 점등
- WARNING: elbow 관절 근처 amber 링
- ERROR: tool head 및 base outline 빨강 점멸
- MANUAL_TEACH: cyan outline + 손끌기 아이콘 보조 뱃지

### 연결선 의미
- 컨베이어로 향하는 황색 라인: physical pick/place 대상
- Gateway/Server로 향하는 초록 라인: command/control
- 분석/이력 쪽 파랑 라인: cycle time, job status, fault log
- RoboDK와의 보라 점선: path/program sync

### hover 정보
- Mode: Auto / Manual Teach / Idle
- Tool: Gripper / Suction / Pen / None
- Payload usage 또는 현재 작업 대상
- Repeatability/Reach는 상세 패널에서만 노출

## 2. TurtleBot3 Waffle Pi

### 출처 기반 핵심 사실
- ROBOTIS e-Manual의 Hardware Specifications에 Waffle Pi는 `Maximum payload 30kg`, `Size 281mm x 306mm x 141mm`, `SBC Raspberry Pi 4`, `LDS-02`, `Raspberry Pi Camera Module v2.1`가 명시돼 있다.
- 공식 이미지 인상은 원형 AMR이 아니라 `사각 적층 플랫폼 + 상단 LiDAR + 좌우 휠 노출`이다.

### SVG 형태 지시
필수 형태 요소:
- 사각 또는 정사각형에 가까운 하부 플레이트
- 상하 2단 적층 구조
- 각 층을 연결하는 수직 standoff 4개
- 최상단 중앙의 납작한 원통형 LiDAR
- 좌우에 일부 노출된 큰 바퀴 2개
- 전면 또는 상부 내부에 작은 카메라/보드 포인트

권장 단순화:
- 하부 plate 1장, 상부 plate 1장, 중앙 LiDAR 1개, 측면 wheel 반원 2개
- Raspberry Pi는 외부 메인 형상보다 `내부 보드가 실장된 플랫폼` 느낌으로 처리
- 전면 카메라는 작은 lens dot 또는 slim camera bar 정도만 표시

금지:
- 로봇청소기형 원판
- 자동차형 AGV 바디
- 드론형 센서 마스트

### 노드 라벨
- 기본 라벨: `TURTLEBOT3 WAFFLE PI`
- 보조 라벨: `AMR / ROS2 Mobile Robot`

### 상태 표현
- RUNNING: 상단 LiDAR 링이 천천히 sweep
- NAVIGATING: 전면 진행 방향에 cyan sweep arc
- DOCKED / IDLE: wheel area low glow only
- WARNING: LiDAR ring amber, battery badge amber
- ERROR: body outline red + route line broken

### 연결선 의미
- 생산라인/입고 스테이션으로 가는 황색 라인: material supply route
- ROS2 bridge/gateway로 가는 파랑 라인: robot state, pose, sensor topics
- command center로 가는 초록 라인: mission dispatch, pause/resume, docking command

### hover 정보
- Mission: Supply / Dock / Wait
- Pose or Zone: A-01 / Infeed / Dock
- Battery
- Sensor summary: LiDAR / Camera / Comm

## 3. RoboDK

### 출처 기반 핵심 사실
- RoboDK 공식 사이트는 제품을 `Robot Simulation Software`로 소개한다.
- 공식 설명은 `simulate and program robot arms offline`, `Digital Twin`, `Post Processors`, `Support 3D Models`, `Avoid Singularities and Collisions`를 핵심 기능으로 제시한다.
- 따라서 메인 그래프에서 RoboDK는 실제 설비 노드가 아니라 `가상 셀 / 오프라인 프로그래밍 / 시뮬레이션 검증` 노드다.

### SVG 형태 지시
필수 형태 요소:
- 모니터 또는 floating display panel
- 패널 내부에 작은 로봇 셀 와이어프레임
- 한쪽에는 로봇 암 outline, 다른 쪽에는 경로(path) 또는 격자 grid
- 3D 좌표축 또는 박스형 workcell frame 1개
- 보라/청록 계열 발광 포인트

권장 단순화:
- 직사각형 모니터 프레임
- 내부에 와이어프레임 로봇 암 + 점선 경로 + grid floor 한 줄
- 우측 상단에 `SIM` 뱃지

금지:
- 서버 랙처럼 표현
- 일반 데이터 대시보드 카드처럼 평면 박스만 표현
- 실제 로봇 장비와 동일한 하드웨어 실루엣

### 노드 라벨
- 기본 라벨: `ROBODK`
- 보조 라벨: `Simulation / Offline Programming`

### 상태 표현
- READY: 보라 halo + grid 안정 발광
- SYNCING: path line이 cyan으로 좌우 이동
- WARNING: collision badge amber
- ERROR: workcell outline red + broken path
- OFFLINE: muted purple + panel dim

### 연결선 의미
- Dobot으로 가는 보라 점선: robot program / path sync
- 서버/저장소 쪽 파랑 라인: CAD/model/job data
- command center 쪽 초록 라인: simulation job request / validation result

### hover 정보
- Program: pick_place_v3
- Sync: In Sync / Drift / Not Deployed
- Last simulation result
- Collision / singularity / reachability summary

## 4. 힌지벨트 컨베이어 + Raspberry Pi 비전

### 출처 기반 핵심 사실
- Titan Conveyors의 Hinged Steel Belt Conveyors 페이지는 이 타입을 `nearly every kind of part and all types of scrap`, `chip removal`, `forging`, `stamping` 등에 쓰는 매우 범용적인 steel belt conveyor로 설명한다.
- 또한 `horizontal and elevated movements`를 한 런에 결합할 수 있다고 명시한다.
- Raspberry Pi 공식 카메라 문서는 `Camera Module 3`를 `12-megapixel`, `standard/NoIR`, `standard/wide FoV` 4개 변형으로 설명한다.
- 즉 이 노드는 `일반 검은 고무벨트`보다 `금속 힌지 슬랫 + 산업용 이송 + 상부 시각 센서` 조합이 읽혀야 한다.

### SVG 형태 지시
필수 형태 요소:
- 측면에서 보이는 직선 또는 완만한 상승 컨베이어 프레임
- 벨트 표면은 연속 띠가 아니라 짧은 직사각 슬랫이 연속 힌지로 이어진 패턴
- 프레임 측면 또는 하부에 구동 스프로킷/롤러 느낌 1개
- 상부 또는 측면 브래킷에 Raspberry Pi 보드 박스 1개
- Pi 보드와 연결된 소형 카메라 모듈 1개
- 검사 포인트를 나타내는 얇은 cyan vision beam 또는 focus frame

권장 단순화:
- 컨베이어 본체는 20~30도 상승 가능한 1선 프레임
- 벨트는 6~8개의 짧은 금속 슬랫 반복
- Raspberry Pi는 녹색 보드 대신 `작은 SBC 박스 + 연결 케이블 + lens dot` 정도로 절제

금지:
- 단순 택배 롤러 컨베이어처럼 원통 롤러만 나열
- 식품용 러버 벨트처럼 매끈한 단일 띠
- 카메라만 크고 컨베이어 존재감이 사라지는 구성

### 노드 라벨
- 기본 라벨: `HINGED BELT + RPI VISION`
- 보조 라벨: `Inspection / Transfer`

### 상태 표현
- RUNNING: 벨트 슬랫의 방향성 이동 애니메이션
- VISION_ACTIVE: 카메라 beam 또는 frame pulse cyan
- JAM_WARNING: 벨트 중간 amber segment
- FAULT: 구동부 red + material flow line 차단
- CAMERA_OFFLINE: 컨베이어는 회색 유지, 카메라 badge만 red

### 연결선 의미
- TurtleBot/Infeed에서 들어오는 황색 라인: 자재 유입
- Dobot 또는 Outfeed로 향하는 황색 라인: 자재 배출
- Gateway/Server로 가는 파랑 라인: frame metadata / count / inspection result
- command center로 가는 초록 라인: start/stop/reset / inspection profile command

### hover 정보
- Conveyor: Running / Stop / Jam
- Vision: Camera OK / Offline / Inferencing
- Item count or inspection result
- Last frame timestamp or reject count

## 5. Server / Gateway / Bridge

### 출처 기반 핵심 사실
- MDN은 WebSocket API를 `two-way interactive communication session`으로 설명한다.
- ROS 2 Topics 문서는 topics를 `continuous data streams, like sensor data, robot state`에 쓰며, `publishers`와 `subscribers`가 topic 이름으로 통신한다고 설명한다.
- Modbus Organization은 Modbus TCP/IP 문서를 `client, server and gateway implementation`을 포함하는 messaging guide로 설명한다.
- 현재 프로젝트 전제상 이 계층은 API, WebSocket, Modbus/TCP, ROS2 bridge를 묶는 관제 허브다.

### SVG 형태 지시
이 계층은 한 덩어리로 그리지 말고 최소 3레이어로 나눈다.

#### A. Gateway Node
필수 형태 요소:
- 육각형 또는 둥근 사각 허브
- 좌우로 여러 라인이 모이는 집중점
- 내부에 bidirectional arrows 2개

라벨:
- `GATEWAY`
- `Protocol Hub`

#### B. API / WebSocket Node
필수 형태 요소:
- 얇은 서버 카드 또는 네트워크 패널
- `API` 와 `WS`를 분리한 dual badge
- 실시간 스트림을 암시하는 파형 또는 양방향 화살표

라벨:
- `API / WS`
- `Command + Telemetry`

#### C. ROS2 Bridge / Modbus Node
필수 형태 요소:
- 좌측 `ROS2` 토픽 버스 배지
- 우측 `Modbus/TCP` 포트/패킷 배지
- 가운데 변환 화살표 또는 bridge glyph

라벨:
- `ROS2 BRIDGE`
- `MODBUS/TCP`

### 상태 표현
- ONLINE: 초록 core + 파랑 telemetry blink
- HIGH_LATENCY: amber outline + 간헐 pulse
- PARTIAL_DEGRADED: 한 프로토콜 뱃지만 amber/red
- DISCONNECTED: 붉은 X, 연결선 일부 끊김
- BACKPRESSURE / QUEUE_HEAVY: WS 패널에 적체 bar

### 연결선 의미
- Waffle Pi ↔ ROS2 Bridge: sensor topics / pose / mission state
- 컨베이어/PLC ↔ Modbus/TCP: register read/write / device I/O
- Gateway ↔ API/WS: browser/client-facing session
- Gateway ↔ RoboDK: sim job / program artifact / validation result
- Gateway ↔ Dobot: command dispatch / job state / completion ack

### hover 정보
- WS: Connected clients / stream rate
- ROS2: topics or bridge status
- Modbus: register poll state / PLC online
- API: last command / last response latency

## 메인 관제 그래프 배치 권장

### 중앙 물리 공정
중앙에는 실제 물리 흐름이 먼저 읽혀야 한다.
- 좌하 또는 좌측: TurtleBot3 Waffle Pi
- 중앙 하단~중앙: Hinged Belt Conveyor + RPi Vision
- 중앙 우측: Dobot Magician
- 우상단 또는 우측 상부: Outfeed / next station

### 상부 관제/가상 계층
- 좌상단: Command Center
- 우상단: RoboDK
- 상단 또는 우측 외곽: API / WS / Gateway / ROS2 / Modbus 허브

### 읽기 우선순위
1. 노란 물류 흐름으로 실제 공정이 읽혀야 함
2. 초록 제어 흐름으로 누가 누구를 제어하는지 보여야 함
3. 파랑 데이터 흐름으로 상태 수집 경로가 보여야 함
4. 보라 점선으로 가상/시뮬레이션 계층을 분리해야 함

## 구현용 요약 스펙

### Dobot 핵심 shape token
- `base_round_rect`
- `joint_circle x3`
- `arm_link x2`
- `tool_head_small`
- `accent_glow_green`

### Waffle Pi 핵심 shape token
- `plate_rect_bottom`
- `plate_rect_top`
- `standoff x4`
- `lidar_disc_top`
- `wheel_half_exposed x2`
- `camera_dot_small`

### RoboDK 핵심 shape token
- `monitor_frame`
- `wire_robot_arm`
- `grid_floor`
- `path_dashed`
- `sim_badge`

### Hinged Belt + RPi 핵심 shape token
- `belt_frame_incline`
- `hinged_slat_repeat`
- `drive_sprocket`
- `sbc_box`
- `camera_module`
- `vision_beam`

### Gateway 계층 핵심 shape token
- `hub_hex`
- `ws_badge`
- `api_card`
- `ros2_bus`
- `modbus_badge`
- `bi_arrow`

## 출처

### Dobot
1. DOBOT Magician 공식 페이지
   https://www.dobot-robots.com/products/education/magician.html

### TurtleBot3
2. ROBOTIS TurtleBot3 Features / Hardware Specifications
   https://emanual.robotis.com/docs/en/platform/turtlebot3/features/

### RoboDK
3. RoboDK 공식 사이트
   https://robodk.com/
4. RoboDK Offline Programming
   https://robodk.com/offline-programming

### Hinged Steel Belt Conveyor
5. Titan Conveyors - Hinged Steel Belt Conveyors
   https://www.titanconveyors.com/products/hinged-steel-belt/

### Raspberry Pi Vision
6. Raspberry Pi Camera documentation
   https://www.raspberrypi.com/documentation/accessories/camera.html

### Protocol / Server / Gateway 표현 근거
7. MDN WebSocket API
   https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API
8. ROS 2 Topics
   https://docs.ros.org/en/rolling/Concepts/Basic/About-Topics.html
9. Modbus Specifications / Modbus TCP/IP
   https://www.modbus.org/modbus-specifications

## 불확실하거나 추가 확인이 필요한 부분
- 힌지벨트 실제 현장 장비의 폭, 가드 형상, 센서 브래킷 위치는 현장 하드웨어 사진이 있으면 더 정확히 고정 가능하다.
- TurtleBot3를 원형으로 그리고 싶다는 초기 인상과 달리, 공식 Waffle Pi 외형은 사각 적층 플랫폼이다. 실제성 우선이면 현재 문서 지시를 따르는 편이 맞다.
- Dobot의 실제 엔드이펙터가 gripper인지 suction인지가 확정되면 hover 정보와 상태 아이콘을 더 정확히 좁힐 수 있다.
