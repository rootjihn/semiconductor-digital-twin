<template>
  <section
    ref="rootRef"
    class="control-hero"
    :style="sceneStyle"
    aria-label="Throughline 메인 관제 그래프"
    @mousemove="handlePointerMove"
    @mouseleave="resetTilt"
  >
    <div class="control-hero__bg control-hero__bg--grid" aria-hidden="true"></div>
    <div class="control-hero__bg control-hero__bg--glow-a" aria-hidden="true"></div>
    <div class="control-hero__bg control-hero__bg--glow-b" aria-hidden="true"></div>

    <header class="control-hero__header surface-rise">
      <div>
        <p class="control-hero__eyebrow">THROUGHLINE CONTROL ROOM</p>
        <h2>로봇·라인·게이트웨이 통합 관제 그래프</h2>
        <p class="control-hero__summary">
          TurtleBot3, 힌지벨트 컨베이어, Raspberry Pi 비전, Dobot Magician, RoboDK, Gateway/Server 흐름을
          물류·제어·데이터 레이어로 분리해 첫 화면에서 바로 읽을 수 있게 구성했습니다.
        </p>
      </div>

      <div class="control-hero__status">
        <span :class="['control-pill', `control-pill--${connectionTone}`]">{{ connectionStateLabel }}</span>
        <span :class="['control-pill', `control-pill--${lineStateTone}`]">라인 {{ lineStateLabel }}</span>
        <span class="control-pill control-pill--neutral">{{ gatewayModeLabel }}</span>
        <span class="control-pill control-pill--neutral">{{ lastSyncLabel }}</span>
      </div>
    </header>

    <div class="control-hero__viewport">
      <section class="control-scene panel surface-rise" aria-label="관제 그래프 캔버스">
        <div class="control-scene__hud">
          <div class="control-kpis">
            <article class="control-kpi">
              <span>처리량</span>
              <strong>{{ snapshot.line.throughput }} ppm</strong>
              <small>실시간 생산 속도</small>
            </article>
            <article class="control-kpi">
              <span>사이클</span>
              <strong>{{ snapshot.line.cycleTimeMs }} ms</strong>
              <small>목표 {{ snapshot.line.targetCycleTimeMs }} ms</small>
            </article>
            <article class="control-kpi">
              <span>알람</span>
              <strong>{{ alarms.length }}</strong>
              <small>미확인 이벤트 포함</small>
            </article>
            <article class="control-kpi">
              <span>장비 온라인</span>
              <strong>{{ onlineCount }}/{{ snapshot.devices.length }}</strong>
              <small>필드 디바이스 기준</small>
            </article>
          </div>

          <div class="control-flow-legend" aria-label="흐름 범례">
            <span><i class="control-flow-legend__line control-flow-legend__line--material"></i>물류</span>
            <span><i class="control-flow-legend__line control-flow-legend__line--control"></i>제어</span>
            <span><i class="control-flow-legend__line control-flow-legend__line--data"></i>데이터</span>
            <span><i class="control-flow-legend__line control-flow-legend__line--digital"></i>시뮬레이션</span>
          </div>
        </div>

        <div class="control-scene__board">
          <svg class="control-scene__edges" viewBox="0 0 1000 620" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <marker id="arrow-amber" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
                <path d="M0 0 L10 5 L0 10 Z" fill="#ffd166" />
              </marker>
              <marker id="arrow-green" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
                <path d="M0 0 L10 5 L0 10 Z" fill="#5dff8f" />
              </marker>
              <marker id="arrow-blue" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
                <path d="M0 0 L10 5 L0 10 Z" fill="#21c6ff" />
              </marker>
              <marker id="arrow-purple" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
                <path d="M0 0 L10 5 L0 10 Z" fill="#8b5cf6" />
              </marker>
            </defs>

            <path
              v-for="edge in edges"
              :key="edge.id"
              :d="edge.path"
              :class="[
                'control-edge',
                `control-edge--${edge.kind}`,
                isHighlighted(edge.nodes) ? 'control-edge--active' : '',
              ]"
              :marker-end="edge.marker"
            />
          </svg>

          <div class="control-zone control-zone--top">
            <button
              v-for="node in topNodes"
              :key="node.id"
              type="button"
              :class="nodeClass(node.id, node.state)"
              @mouseenter="hoveredNodeId = node.id"
              @mouseleave="hoveredNodeId = null"
              @focus="hoveredNodeId = node.id"
              @blur="hoveredNodeId = null"
              @click="selectNode(node.id)"
            >
              <div class="control-node__status">
                <i :class="['control-node__status-dot', `control-node__status-dot--${node.tone}`]"></i>
                <span>{{ node.stateLabel }}</span>
              </div>
              <div :class="['control-node__icon', `control-node__icon--${node.icon}`]" aria-hidden="true">
                <span></span><span></span><span></span><span></span>
              </div>
              <strong>{{ node.label }}</strong>
              <small>{{ node.subtitle }}</small>
              <div class="control-node__metric">{{ node.metric }}</div>
            </button>
          </div>

          <div class="control-zone control-zone--middle">
            <button
              type="button"
              :class="nodeClass('turtlebot', turtlebotNode.state, 'control-node--side')"
              @mouseenter="hoveredNodeId = 'turtlebot'"
              @mouseleave="hoveredNodeId = null"
              @focus="hoveredNodeId = 'turtlebot'"
              @blur="hoveredNodeId = null"
              @click="selectNode('turtlebot')"
            >
              <div class="control-node__status">
                <i :class="['control-node__status-dot', `control-node__status-dot--${turtlebotNode.tone}`]"></i>
                <span>{{ turtlebotNode.stateLabel }}</span>
              </div>
              <div class="control-node__icon control-node__icon--turtlebot" aria-hidden="true">
                <span></span><span></span><span></span><span></span>
              </div>
              <strong>{{ turtlebotNode.label }}</strong>
              <small>{{ turtlebotNode.subtitle }}</small>
              <div class="control-node__metric">{{ turtlebotNode.metric }}</div>
            </button>

            <button
              type="button"
              :class="nodeClass('conveyor', conveyorNode.state, 'control-node--center')"
              @mouseenter="hoveredNodeId = 'conveyor'"
              @mouseleave="hoveredNodeId = null"
              @focus="hoveredNodeId = 'conveyor'"
              @blur="hoveredNodeId = null"
              @click="selectNode('conveyor')"
            >
              <div class="control-node__status">
                <i :class="['control-node__status-dot', `control-node__status-dot--${conveyorNode.tone}`]"></i>
                <span>{{ conveyorNode.stateLabel }}</span>
              </div>
              <div class="control-conveyor-art" aria-hidden="true">
                <span class="control-conveyor-art__belt"></span>
                <span class="control-conveyor-art__plate control-conveyor-art__plate--a"></span>
                <span class="control-conveyor-art__plate control-conveyor-art__plate--b"></span>
                <span class="control-conveyor-art__plate control-conveyor-art__plate--c"></span>
                <span class="control-conveyor-art__vision"></span>
                <span class="control-conveyor-art__pi"></span>
              </div>
              <strong>{{ conveyorNode.label }}</strong>
              <small>{{ conveyorNode.subtitle }}</small>
              <div class="control-node__metric">{{ conveyorNode.metric }}</div>
            </button>

            <button
              type="button"
              :class="nodeClass('dobot', dobotNode.state, 'control-node--side')"
              @mouseenter="hoveredNodeId = 'dobot'"
              @mouseleave="hoveredNodeId = null"
              @focus="hoveredNodeId = 'dobot'"
              @blur="hoveredNodeId = null"
              @click="selectNode('dobot')"
            >
              <div class="control-node__status">
                <i :class="['control-node__status-dot', `control-node__status-dot--${dobotNode.tone}`]"></i>
                <span>{{ dobotNode.stateLabel }}</span>
              </div>
              <div class="control-node__icon control-node__icon--dobot" aria-hidden="true">
                <span></span><span></span><span></span><span></span>
              </div>
              <strong>{{ dobotNode.label }}</strong>
              <small>{{ dobotNode.subtitle }}</small>
              <div class="control-node__metric">{{ dobotNode.metric }}</div>
            </button>
          </div>

          <div class="control-zone control-zone--bottom">
            <button
              v-for="node in bottomNodes"
              :key="node.id"
              type="button"
              :class="nodeClass(node.id, node.state, 'control-node--bottom')"
              @mouseenter="hoveredNodeId = node.id"
              @mouseleave="hoveredNodeId = null"
              @focus="hoveredNodeId = node.id"
              @blur="hoveredNodeId = null"
              @click="selectNode(node.id)"
            >
              <div class="control-node__status">
                <i :class="['control-node__status-dot', `control-node__status-dot--${node.tone}`]"></i>
                <span>{{ node.stateLabel }}</span>
              </div>
              <div :class="['control-node__icon', `control-node__icon--${node.icon}`]" aria-hidden="true">
                <span></span><span></span><span></span><span></span>
              </div>
              <strong>{{ node.label }}</strong>
              <small>{{ node.subtitle }}</small>
              <div class="control-node__metric">{{ node.metric }}</div>
            </button>
          </div>
        </div>
      </section>

      <aside class="control-inspector panel surface-rise">
        <div class="control-inspector__header">
          <div>
            <p class="eyebrow">선택 노드</p>
            <h3>{{ selectedNode.label }}</h3>
          </div>
          <span :class="['chip', selectedNodeChipClass]">{{ selectedNode.stateLabel }}</span>
        </div>

        <p class="control-inspector__detail">{{ selectedNode.detail }}</p>

        <div class="control-inspector__meta">
          <article>
            <span>핵심 입출력</span>
            <strong>{{ selectedNode.metric }}</strong>
          </article>
          <article>
            <span>최근 갱신</span>
            <strong>{{ lastSyncShort }}</strong>
          </article>
          <article>
            <span>연결 라우트</span>
            <strong>{{ selectedNode.pageLabel }}</strong>
          </article>
          <article>
            <span>현재 초점</span>
            <strong>{{ selectedNode.focus }}</strong>
          </article>
        </div>

        <div class="control-inspector__events">
          <div class="control-inspector__subhead">
            <strong>최근 이벤트</strong>
            <span>{{ activeFeed.length }}건</span>
          </div>
          <article v-for="item in activeFeed" :key="item.id" class="control-feed-item">
            <div>
              <p>{{ item.message }}</p>
              <small>{{ item.source }} · {{ item.time }}</small>
            </div>
            <span :class="['chip', severityChip(item.severity)]">{{ item.severityLabel }}</span>
          </article>
        </div>

        <div class="control-inspector__actions">
          <button type="button" class="secondary" @click="emit('navigate', selectedNode.page)">
            {{ selectedNode.pageLabel }} 열기
          </button>
          <button type="button" class="secondary" @click="selectNode(snapshot.process.activeStage)">
            현재 공정 포커스
          </button>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue';
import gsap from 'gsap';
import type { AppRouteName } from '../../shared/navigation';
import type { ConnectionState, DashboardSnapshot, DeviceState, ProcessStageKey } from '../../shared/telemetry';

type LandingFeedItem = {
  id: string;
  time: string;
  source: string;
  severity: string;
  severityLabel: string;
  message: string;
};

type LandingAlarm = LandingFeedItem & {
  acknowledged: boolean;
  tone: string;
};

type NodeId =
  | ProcessStageKey
  | 'turtlebot'
  | 'dobot'
  | 'gateway'
  | 'cloud'
  | 'robodk'
  | 'websocket'
  | 'ros2'
  | 'modbus';

type GraphNode = {
  id: NodeId;
  label: string;
  subtitle: string;
  state: DeviceState | ConnectionState | 'SIMULATION';
  stateLabel: string;
  tone: 'good' | 'warn' | 'danger' | 'neutral' | 'simulation';
  metric: string;
  detail: string;
  page: AppRouteName;
  pageLabel: string;
  focus: string;
  icon: 'gateway' | 'cloud' | 'robodk' | 'websocket' | 'bridge' | 'turtlebot';
  eventSources: string[];
};

type GraphEdge = {
  id: string;
  kind: 'material' | 'control' | 'data' | 'digital';
  nodes: NodeId[];
  path: string;
  marker: string;
};

const props = defineProps<{
  snapshot: DashboardSnapshot;
  connectionState: ConnectionState;
  lastSyncLabel: string;
  events: LandingFeedItem[];
  alarms: LandingAlarm[];
}>();

const emit = defineEmits<{
  (event: 'navigate', page: AppRouteName): void;
}>();

const rootRef = ref<HTMLElement | null>(null);
const hoveredNodeId = ref<NodeId | null>(null);
const selectedNodeId = ref<NodeId>(props.snapshot.process.activeStage);
const pointerX = ref(0);
const pointerY = ref(0);

const deviceMap = computed(() => Object.fromEntries(props.snapshot.devices.map((device) => [device.id, device])));
const stageMap = computed(() => Object.fromEntries(props.snapshot.process.stages.map((stage) => [stage.id, stage])) as Partial<Record<ProcessStageKey, DashboardSnapshot['process']['stages'][number]>>);

const connectionStateLabel = computed(() => {
  const map: Record<ConnectionState, string> = {
    connecting: '연결 중',
    online: '실시간 연결',
    degraded: '지연 상태',
    offline: '오프라인',
    mock: '모의 모드',
  };
  return map[props.connectionState];
});

const connectionTone = computed<'good' | 'warn' | 'danger' | 'neutral'>(() => {
  if (props.connectionState === 'online') return 'good';
  if (props.connectionState === 'offline') return 'danger';
  if (props.connectionState === 'mock') return 'neutral';
  return 'warn';
});

const lineStateLabel = computed(() => lineStateText(props.snapshot.line.state));
const lineStateTone = computed<'good' | 'warn' | 'danger'>(() => {
  if (props.snapshot.line.state === 'RUNNING') return 'good';
  if (props.snapshot.line.state === 'FAULT') return 'danger';
  return 'warn';
});
const gatewayModeLabel = computed(() => (props.snapshot.gatewayMode === 'live' ? '실시간 게이트웨이' : '모의 게이트웨이'));
const onlineCount = computed(() => props.snapshot.devices.filter((device) => device.online).length);
const lastSyncShort = computed(() => props.lastSyncLabel.replace('최근 동기화 ', ''));

const turtlebotNode = computed<GraphNode>(() => ({
  id: 'turtlebot',
  label: 'TurtleBot3 Waffle Pi',
  subtitle: 'AMR / 자재 투입',
  state: 'RUNNING',
  stateLabel: stageMap.value.infeed?.state === 'RUNNING' ? '공급 중' : '대기 중',
  tone: stageMap.value.infeed?.state === 'RUNNING' ? 'good' : 'neutral',
  metric: `${stageMap.value.infeed?.value ?? '자재 대기'} · Dock A-01`,
  detail: '모바일 로봇이 입고 스테이션으로 자재를 공급하고 ROS2 상태를 게이트웨이로 전달합니다.',
  page: 'devices',
  pageLabel: '디바이스',
  focus: '미션·배터리·포즈',
  icon: 'turtlebot',
  eventSources: ['cell', 'control', 'gateway'],
}));

const conveyorNode = computed<GraphNode>(() => {
  const conveyor = deviceMap.value['conveyor-drive'];
  const vision = deviceMap.value['vision-camera'];
  return {
    id: 'conveyor',
    label: '힌지벨트 컨베이어 + Raspberry Pi',
    subtitle: 'Material Flow / Vision Node',
    state: conveyor?.state ?? stageMap.value.conveyor?.state ?? 'READY',
    stateLabel: deviceStateText(conveyor?.state ?? stageMap.value.conveyor?.state ?? 'READY'),
    tone: stateTone(conveyor?.state ?? stageMap.value.conveyor?.state ?? 'READY'),
    metric: `${conveyor?.value ?? stageMap.value.conveyor?.value ?? '이송 중'} · ${vision?.value ?? '프레임 분석'}`,
    detail: '메탈 힌지 슬랫 벨트와 상부 비전/Raspberry Pi가 자재 이송, 검사, 데이터 수집을 동시에 담당합니다.',
    page: 'devices',
    pageLabel: '디바이스',
    focus: '이송 속도·비전 프레임',
    icon: 'bridge',
    eventSources: ['vision', 'production', 'modbus'],
  };
});

const dobotNode = computed<GraphNode>(() => {
  const dobot = deviceMap.value['dobot-arm'];
  return {
    id: 'dobot',
    label: 'Dobot Magician',
    subtitle: 'Pick & Place / Teaching Arm',
    state: dobot?.state ?? stageMap.value.pick?.state ?? 'READY',
    stateLabel: deviceStateText(dobot?.state ?? stageMap.value.pick?.state ?? 'READY'),
    tone: stateTone(dobot?.state ?? stageMap.value.pick?.state ?? 'READY'),
    metric: `${dobot?.value ?? '대기'} · Repeatability ±0.2 mm`,
    detail: '소형 4축 로봇 암이 비전 결과를 받아 집기/이송 작업을 수행하고, 프로그램은 RoboDK와 동기화됩니다.',
    page: 'devices',
    pageLabel: '디바이스',
    focus: 'Tool·Cycle·작업 대상',
    icon: 'bridge',
    eventSources: ['control', 'production', 'safety'],
  };
});

const topNodes = computed<GraphNode[]>(() => [
  {
    id: 'websocket',
    label: 'WebSocket Server',
    subtitle: 'State Stream / Event Relay',
    state: props.connectionState,
    stateLabel: connectionStateLabel.value,
    tone: connectionTone.value,
    metric: props.snapshot.gatewayState === 'mock' ? 'mock feed' : 'live stream',
    detail: '대시보드와 게이트웨이 사이의 상태 스트림, 이벤트, 명령 결과를 중계합니다.',
    page: 'servers',
    pageLabel: '서버',
    focus: '연결 지연·이벤트 스트림',
    icon: 'websocket',
    eventSources: ['websocket', 'gateway'],
  },
  {
    id: 'gateway',
    label: 'Node Gateway',
    subtitle: 'Command / Bridge Hub',
    state: props.snapshot.gatewayState,
    stateLabel: connectionStateLabel.value,
    tone: connectionTone.value,
    metric: `${gatewayModeLabel.value} · ${props.snapshot.line.jobId}`,
    detail: '명령, 스냅샷, 브리지 연결 상태를 묶는 중앙 허브입니다.',
    page: 'servers',
    pageLabel: '서버',
    focus: '명령 라우팅·브리지 상태',
    icon: 'gateway',
    eventSources: ['gateway', 'command', 'health'],
  },
  {
    id: 'cloud',
    label: 'Cloud / API Hub',
    subtitle: 'Data Hub / External API',
    state: props.connectionState === 'offline' ? 'offline' : 'online',
    stateLabel: props.connectionState === 'offline' ? '연동 지연' : 'API 연동',
    tone: props.connectionState === 'offline' ? 'warn' : 'good',
    metric: `${props.snapshot.line.orderId} · 저장/조회`,
    detail: '외부 서비스, 저장소, 운영 API가 게이트웨이와 비동기 연동되는 계층입니다.',
    page: 'servers',
    pageLabel: '서버',
    focus: '외부 연동·저장 상태',
    icon: 'cloud',
    eventSources: ['gateway', 'health', 'fallback'],
  },
  {
    id: 'robodk',
    label: 'RoboDK',
    subtitle: 'Simulation / Offline Programming',
    state: 'SIMULATION',
    stateLabel: '디지털 트윈 동기화',
    tone: 'simulation',
    metric: `${props.snapshot.process.activeStage} · program sync`,
    detail: '실장비가 아니라 디지털 트윈/오프라인 프로그래밍 계층으로, Dobot 경로와 셀 상태를 검증합니다.',
    page: 'simulation',
    pageLabel: '시뮬레이션',
    focus: '프로그램 버전·sync drift',
    icon: 'robodk',
    eventSources: ['mock', 'gateway', 'command'],
  },
]);

const bottomNodes = computed<GraphNode[]>(() => [
  {
    id: 'ros2',
    label: 'ROS2 Bridge',
    subtitle: 'Pose / Mission Topics',
    state: props.connectionState === 'offline' ? 'offline' : 'online',
    stateLabel: props.connectionState === 'offline' ? '토픽 지연' : '토픽 중계',
    tone: props.connectionState === 'offline' ? 'warn' : 'good',
    metric: 'pose · battery · mission',
    detail: 'TurtleBot3 상태와 미션 제어를 게이트웨이에 연결하는 ROS2 브리지입니다.',
    page: 'servers',
    pageLabel: '서버',
    focus: 'mission dispatch·pose stream',
    icon: 'bridge',
    eventSources: ['gateway', 'control', 'health'],
  },
  {
    id: 'modbus',
    label: 'Modbus Bridge',
    subtitle: 'PLC / Conveyor I/O',
    state: props.snapshot.gatewayMode === 'mock' ? 'mock' : props.connectionState,
    stateLabel: props.snapshot.gatewayMode === 'mock' ? '모의 I/O' : '필드 I/O',
    tone: props.snapshot.gatewayMode === 'mock' ? 'neutral' : connectionTone.value,
    metric: 'drive · sensor · gate',
    detail: '컨베이어, 센서, 배출 게이트와의 PLC/I/O 신호를 중계합니다.',
    page: 'servers',
    pageLabel: '서버',
    focus: 'I/O 지연·드라이브 상태',
    icon: 'bridge',
    eventSources: ['modbus', 'production', 'safety'],
  },
  {
    id: 'vision',
    label: 'Vision Node',
    subtitle: 'Frame Analysis / Quality',
    state: deviceMap.value['vision-camera']?.state ?? stageMap.value.vision?.state ?? 'READY',
    stateLabel: deviceStateText(deviceMap.value['vision-camera']?.state ?? stageMap.value.vision?.state ?? 'READY'),
    tone: stateTone(deviceMap.value['vision-camera']?.state ?? stageMap.value.vision?.state ?? 'READY'),
    metric: `${deviceMap.value['vision-camera']?.detail ?? '프레임 분석'} · ${stageMap.value.vision?.value ?? '검사 중'}`,
    detail: '카메라 프레임 검사, 품질 판정, 좌표 산출을 담당하는 비전 처리 계층입니다.',
    page: 'devices',
    pageLabel: '디바이스',
    focus: '프레임률·검출 품질',
    icon: 'bridge',
    eventSources: ['vision', 'production', 'health'],
  },
]);

const nodeMap = computed<Record<NodeId, GraphNode>>(() => ({
  turtlebot: turtlebotNode.value,
  conveyor: conveyorNode.value,
  dobot: dobotNode.value,
  infeed: {
    id: 'infeed',
    label: '입고 스테이션',
    subtitle: 'Infeed / Supply Gate',
    state: stageMap.value.infeed?.state ?? 'READY',
    stateLabel: deviceStateText(stageMap.value.infeed?.state ?? 'READY'),
    tone: stateTone(stageMap.value.infeed?.state ?? 'READY'),
    metric: `${stageMap.value.infeed?.value ?? '자재 대기'} · 투입 준비`,
    detail: stageMap.value.infeed?.detail ?? '입고 센서가 자재 유입을 확인합니다.',
    page: 'simulation',
    pageLabel: '시뮬레이션',
    focus: '입고 감지·투입 대기',
    icon: 'bridge',
    eventSources: ['production', 'cell', 'control'],
  },
  outfeed: {
    id: 'outfeed',
    label: '배출 게이트',
    subtitle: 'Outfeed / Sort Gate',
    state: stageMap.value.outfeed?.state ?? 'READY',
    stateLabel: deviceStateText(stageMap.value.outfeed?.state ?? 'READY'),
    tone: stateTone(stageMap.value.outfeed?.state ?? 'READY'),
    metric: `${deviceMap.value['outfeed-gate']?.value ?? '원활'} · 분류 라인`,
    detail: stageMap.value.outfeed?.detail ?? '양품/불량 분류와 다음 공정 전달을 담당합니다.',
    page: 'simulation',
    pageLabel: '시뮬레이션',
    focus: '배출 분기·적체 상태',
    icon: 'bridge',
    eventSources: ['production', 'safety', 'health'],
  },
  pick: dobotNode.value,
  vision: bottomNodes.value[2]!,
  gateway: topNodes.value[1]!,
  cloud: topNodes.value[2]!,
  robodk: topNodes.value[3]!,
  websocket: topNodes.value[0]!,
  ros2: bottomNodes.value[0]!,
  modbus: bottomNodes.value[1]!,
}));

const selectedNode = computed(() => nodeMap.value[selectedNodeId.value] ?? nodeMap.value[props.snapshot.process.activeStage]);

const selectedNodeChipClass = computed(() => {
  if (selectedNode.value.tone === 'danger') return 'chip-danger';
  if (selectedNode.value.tone === 'warn') return 'chip-warn';
  if (selectedNode.value.tone === 'good') return 'chip-good';
  return 'chip-neutral';
});

const activeFeed = computed(() => {
  const sourceSet = new Set(selectedNode.value.eventSources);
  const merged = [...props.alarms, ...props.events];
  return merged
    .filter((item) => sourceSet.has(item.source))
    .slice(0, 4)
    .map((item) => ({
      id: item.id,
      message: item.message,
      time: item.time,
      source: sourceLabel(item.source),
      severity: item.severity,
      severityLabel: item.severityLabel,
    }));
});

const sceneStyle = computed(() => ({
  '--pointer-x': `${pointerX.value}px`,
  '--pointer-y': `${pointerY.value}px`,
}));

const edges = computed<GraphEdge[]>(() => [
  { id: 'material-1', kind: 'material', nodes: ['turtlebot', 'infeed'], path: 'M160 360 C220 330 255 315 320 300', marker: 'url(#arrow-amber)' },
  { id: 'material-2', kind: 'material', nodes: ['infeed', 'conveyor'], path: 'M338 298 C410 298 450 304 500 312', marker: 'url(#arrow-amber)' },
  { id: 'material-3', kind: 'material', nodes: ['conveyor', 'dobot'], path: 'M610 320 C700 320 760 316 840 300', marker: 'url(#arrow-amber)' },
  { id: 'material-4', kind: 'material', nodes: ['dobot', 'outfeed'], path: 'M846 326 C892 360 904 386 900 452', marker: 'url(#arrow-amber)' },
  { id: 'control-1', kind: 'control', nodes: ['gateway', 'turtlebot'], path: 'M500 132 C380 140 280 198 206 280', marker: 'url(#arrow-green)' },
  { id: 'control-2', kind: 'control', nodes: ['gateway', 'conveyor'], path: 'M500 144 C500 190 500 226 500 270', marker: 'url(#arrow-green)' },
  { id: 'control-3', kind: 'control', nodes: ['gateway', 'dobot'], path: 'M500 146 C620 152 744 212 824 276', marker: 'url(#arrow-green)' },
  { id: 'data-1', kind: 'data', nodes: ['conveyor', 'vision'], path: 'M540 350 C562 398 596 424 658 480', marker: 'url(#arrow-blue)' },
  { id: 'data-2', kind: 'data', nodes: ['vision', 'websocket'], path: 'M660 500 C590 430 532 312 342 146', marker: 'url(#arrow-blue)' },
  { id: 'data-3', kind: 'data', nodes: ['gateway', 'cloud'], path: 'M548 106 C652 82 738 82 824 104', marker: 'url(#arrow-blue)' },
  { id: 'data-4', kind: 'data', nodes: ['gateway', 'ros2'], path: 'M510 150 C560 260 604 344 640 462', marker: 'url(#arrow-blue)' },
  { id: 'digital-1', kind: 'digital', nodes: ['robodk', 'dobot'], path: 'M758 114 C818 140 854 198 876 274', marker: 'url(#arrow-purple)' },
  { id: 'digital-2', kind: 'digital', nodes: ['robodk', 'gateway'], path: 'M700 120 C642 122 594 124 544 126', marker: 'url(#arrow-purple)' },
  { id: 'control-4', kind: 'control', nodes: ['modbus', 'conveyor'], path: 'M392 504 C404 430 430 380 470 344', marker: 'url(#arrow-green)' },
]);

onMounted(async () => {
  await nextTick();
  if (!rootRef.value) return;
  gsap.fromTo(
    rootRef.value.querySelectorAll('.control-hero__header, .control-scene, .control-inspector, .control-node'),
    { opacity: 0, y: 24, scale: 0.98 },
    { opacity: 1, y: 0, scale: 1, duration: 0.72, stagger: 0.04, ease: 'power3.out' },
  );
});

function nodeClass(id: NodeId, state: GraphNode['state'], extra?: string) {
  return [
    'control-node',
    extra,
    stateClass(state),
    selectedNodeId.value === id ? 'is-selected' : '',
    hoveredNodeId.value === id ? 'is-hovered' : '',
  ];
}

function isHighlighted(nodeIds: NodeId[]) {
  const active = hoveredNodeId.value ?? selectedNodeId.value;
  return nodeIds.includes(active);
}

function selectNode(id: NodeId) {
  selectedNodeId.value = id;
}

function handlePointerMove(event: MouseEvent) {
  const target = event.currentTarget as HTMLElement;
  const rect = target.getBoundingClientRect();
  pointerX.value = Number((((event.clientX - rect.left) / rect.width) * 14 - 7).toFixed(2));
  pointerY.value = Number((((event.clientY - rect.top) / rect.height) * 10 - 5).toFixed(2));
}

function resetTilt() {
  pointerX.value = 0;
  pointerY.value = 0;
}

function lineStateText(state: string) {
  const map: Record<string, string> = {
    RUNNING: '가동 중',
    PAUSED: '일시 정지',
    STOPPED: '정지',
    FAULT: '장애',
  };
  return map[state] ?? state;
}

function deviceStateText(state: string) {
  const map: Record<string, string> = {
    READY: '준비 완료',
    RUNNING: '가동 중',
    BUSY: '작업 중',
    WAITING: '대기 중',
    WARNING: '주의',
    FAULT: '오류',
    OFFLINE: '오프라인',
    IDLE: '유휴',
    online: '온라인',
    offline: '오프라인',
    connecting: '연결 중',
    degraded: '지연',
    mock: '모의',
    SIMULATION: '시뮬레이션',
  };
  return map[state] ?? state;
}

function stateTone(state: string): GraphNode['tone'] {
  if (state === 'RUNNING' || state === 'BUSY' || state === 'READY' || state === 'online') return 'good';
  if (state === 'WARNING' || state === 'WAITING' || state === 'connecting' || state === 'degraded') return 'warn';
  if (state === 'FAULT' || state === 'OFFLINE' || state === 'offline') return 'danger';
  if (state === 'SIMULATION') return 'simulation';
  return 'neutral';
}

function stateClass(state: string) {
  const tone = stateTone(state);
  return `control-node--${tone}`;
}

function sourceLabel(source: string) {
  const map: Record<string, string> = {
    gateway: '게이트웨이',
    websocket: 'WebSocket',
    command: '명령',
    fallback: '대체 경로',
    mock: '모의',
    control: '제어',
    safety: '안전',
    vision: '비전',
    health: '상태',
    production: '생산',
    cell: '셀',
    modbus: 'Modbus',
  };
  return map[source] ?? source;
}

function severityChip(severity: string) {
  if (severity === 'CRITICAL' || severity === 'ERROR') return 'danger';
  if (severity === 'WARN') return 'warn';
  return 'good';
}
</script>

<style scoped>
.control-hero {
  position: relative;
  overflow: hidden;
  display: grid;
  gap: 18px;
  min-height: 720px;
  padding: 22px;
  border-radius: 34px;
  background:
    radial-gradient(circle at 14% 12%, rgba(33, 198, 255, 0.12), transparent 28%),
    radial-gradient(circle at 88% 10%, rgba(139, 92, 246, 0.12), transparent 22%),
    linear-gradient(180deg, rgba(246, 250, 252, 0.98), rgba(236, 243, 247, 0.98));
  border: 1px solid rgba(31, 46, 70, 0.08);
  box-shadow: 0 32px 80px rgba(23, 32, 51, 0.1);
}

.control-hero__bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.control-hero__bg--grid {
  background-image:
    linear-gradient(rgba(15, 23, 42, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 23, 42, 0.05) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: linear-gradient(180deg, rgba(0,0,0,0.44), transparent 92%);
}

.control-hero__bg--glow-a {
  left: -6%;
  top: 28%;
  width: 320px;
  height: 320px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(34, 197, 94, 0.16), transparent 68%);
}

.control-hero__bg--glow-b {
  right: -4%;
  top: 8%;
  width: 340px;
  height: 340px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(33, 198, 255, 0.18), transparent 68%);
}

.control-hero__header,
.control-scene,
.control-inspector {
  position: relative;
  z-index: 1;
}

.control-hero__header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
  padding: 24px 28px;
  border: 1px solid rgba(255, 255, 255, 0.68);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.74);
  backdrop-filter: blur(12px);
}

.control-hero__eyebrow {
  margin: 0;
  color: #0f9db3;
  font-size: 0.75rem;
  font-weight: 900;
  letter-spacing: 0.16em;
}

.control-hero__header h2 {
  margin: 8px 0 0;
  max-width: 18ch;
  color: #16324f;
  font-size: clamp(1.9rem, 3vw, 3rem);
  line-height: 1.08;
  letter-spacing: -0.05em;
}

.control-hero__summary {
  max-width: 68ch;
  margin-top: 12px;
  color: #55657c;
  line-height: 1.6;
}

.control-hero__status {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
  max-width: 430px;
}

.control-pill {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 0.55rem 0.85rem;
  border-radius: 999px;
  border: 1px solid rgba(31, 46, 70, 0.12);
  background: rgba(255, 255, 255, 0.88);
  color: #16324f;
  font-size: 0.82rem;
  font-weight: 900;
  white-space: nowrap;
}

.control-pill--good { color: #0f6f57; background: rgba(34, 197, 94, 0.1); border-color: rgba(34, 197, 94, 0.24); }
.control-pill--warn { color: #9a6515; background: rgba(245, 158, 11, 0.12); border-color: rgba(245, 158, 11, 0.24); }
.control-pill--danger { color: #a13232; background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.22); }
.control-pill--neutral { color: #475569; background: rgba(226, 232, 240, 0.76); }

.control-hero__viewport {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.72fr);
  gap: 16px;
  align-items: start;
}

.control-scene,
.control-inspector {
  min-height: 100%;
  padding: 22px;
}

.control-scene {
  overflow: hidden;
  border-radius: 32px;
}

.control-scene__hud {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.control-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  flex: 1;
}

.control-kpi {
  padding: 14px 16px;
  border-radius: 20px;
  border: 1px solid rgba(31, 46, 70, 0.08);
  background: rgba(255, 255, 255, 0.76);
}

.control-kpi span,
.control-inspector__meta span,
.control-feed-item small {
  display: block;
  color: #64748b;
  font-size: 0.77rem;
  font-weight: 800;
}

.control-kpi strong,
.control-inspector__meta strong {
  display: block;
  margin-top: 6px;
  color: #16324f;
  font-size: 1.1rem;
}

.control-kpi small {
  display: block;
  margin-top: 4px;
  color: #64748b;
}

.control-flow-legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
  max-width: 310px;
}

.control-flow-legend span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  padding: 0.48rem 0.78rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(31, 46, 70, 0.08);
  color: #334155;
  font-size: 0.8rem;
  font-weight: 800;
}

.control-flow-legend__line {
  width: 28px;
  height: 0;
  border-top-width: 3px;
  border-top-style: solid;
}

.control-flow-legend__line--material { border-color: #ffd166; }
.control-flow-legend__line--control { border-color: #5dff8f; }
.control-flow-legend__line--data { border-color: #21c6ff; }
.control-flow-legend__line--digital { border-color: #8b5cf6; border-top-style: dashed; }

.control-scene__board {
  position: relative;
  min-height: 620px;
  padding: 12px 8px 4px;
  border-radius: 28px;
  background:
    radial-gradient(circle at calc(50% + var(--pointer-x)) calc(42% + var(--pointer-y)), rgba(33, 198, 255, 0.08), transparent 24%),
    linear-gradient(180deg, rgba(255,255,255,0.9), rgba(244, 248, 250, 0.82));
  border: 1px solid rgba(31, 46, 70, 0.08);
}

.control-scene__edges {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.control-edge {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.38;
  transition: opacity 180ms ease, stroke-width 180ms ease, filter 180ms ease;
}

.control-edge--material {
  stroke: #ffd166;
  stroke-width: 5;
}

.control-edge--control {
  stroke: #5dff8f;
  stroke-width: 3.5;
}

.control-edge--data {
  stroke: #21c6ff;
  stroke-width: 3.5;
  stroke-dasharray: 10 12;
}

.control-edge--digital {
  stroke: #8b5cf6;
  stroke-width: 3.2;
  stroke-dasharray: 8 10;
}

.control-edge--active {
  opacity: 0.96;
  filter: drop-shadow(0 0 8px rgba(33, 198, 255, 0.3));
}

.control-zone {
  position: absolute;
  left: 20px;
  right: 20px;
  display: grid;
  gap: 16px;
}

.control-zone--top {
  top: 28px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.control-zone--middle {
  top: 215px;
  grid-template-columns: minmax(220px, 1fr) minmax(320px, 1.2fr) minmax(220px, 1fr);
  align-items: center;
}

.control-zone--bottom {
  bottom: 22px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.control-node {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 10px;
  padding: 16px 16px 18px;
  border: 1px solid rgba(31, 46, 70, 0.1);
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 18px 42px rgba(31, 46, 70, 0.08);
  text-align: left;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease, background 180ms ease;
}

.control-node:hover,
.control-node.is-hovered,
.control-node.is-selected {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.97);
  box-shadow: 0 24px 56px rgba(31, 46, 70, 0.14);
}

.control-node.is-selected {
  border-color: rgba(15, 157, 179, 0.34);
}

.control-node strong {
  color: #16324f;
  font-size: 1rem;
  letter-spacing: -0.02em;
}

.control-node small {
  color: #64748b;
  line-height: 1.45;
}

.control-node__status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #475569;
  font-size: 0.76rem;
  font-weight: 900;
}

.control-node__status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  box-shadow: 0 0 0 6px rgba(148, 163, 184, 0.08);
}

.control-node__status-dot--good { background: #22c55e; box-shadow: 0 0 0 6px rgba(34, 197, 94, 0.1); }
.control-node__status-dot--warn { background: #f59e0b; box-shadow: 0 0 0 6px rgba(245, 158, 11, 0.12); }
.control-node__status-dot--danger { background: #ef4444; box-shadow: 0 0 0 6px rgba(239, 68, 68, 0.1); }
.control-node__status-dot--neutral { background: #94a3b8; }
.control-node__status-dot--simulation { background: #8b5cf6; box-shadow: 0 0 0 6px rgba(139, 92, 246, 0.1); }

.control-node__metric {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0.45rem 0.7rem;
  width: fit-content;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.045);
  color: #334155;
  font-size: 0.8rem;
  font-weight: 800;
}

.control-node__icon {
  position: relative;
  width: 82px;
  height: 66px;
}

.control-node__icon span {
  position: absolute;
  display: block;
}

.control-node__icon--gateway span:nth-child(1) {
  inset: 10px 8px 12px;
  border-radius: 18px;
  background: linear-gradient(135deg, #1e3a5f, #0f9db3);
}

.control-node__icon--gateway span:nth-child(2),
.control-node__icon--gateway span:nth-child(3) {
  left: 20px;
  right: 20px;
  height: 4px;
  border-radius: 999px;
  background: rgba(255,255,255,0.85);
}

.control-node__icon--gateway span:nth-child(2) { top: 24px; }
.control-node__icon--gateway span:nth-child(3) { top: 36px; }
.control-node__icon--gateway span:nth-child(4) {
  right: 10px;
  top: 16px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #5dff8f;
}

.control-node__icon--cloud span:nth-child(1),
.control-node__icon--cloud span:nth-child(2),
.control-node__icon--cloud span:nth-child(3) {
  border-radius: 50%;
  background: linear-gradient(180deg, #0f9db3, #21c6ff);
}

.control-node__icon--cloud span:nth-child(1) { left: 12px; top: 26px; width: 28px; height: 22px; }
.control-node__icon--cloud span:nth-child(2) { left: 28px; top: 16px; width: 30px; height: 28px; }
.control-node__icon--cloud span:nth-child(3) { left: 48px; top: 24px; width: 24px; height: 20px; }
.control-node__icon--cloud span:nth-child(4) {
  right: 4px;
  top: 8px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid rgba(15, 157, 179, 0.4);
}

.control-node__icon--websocket span:nth-child(1) {
  inset: 10px 14px 18px;
  border-radius: 18px;
  border: 3px solid #21c6ff;
}
.control-node__icon--websocket span:nth-child(2) {
  left: 22px;
  right: 22px;
  top: 28px;
  height: 3px;
  background: #21c6ff;
}
.control-node__icon--websocket span:nth-child(3) {
  left: 38px;
  top: 18px;
  width: 6px;
  height: 30px;
  background: #21c6ff;
}
.control-node__icon--websocket span:nth-child(4) {
  right: 12px;
  bottom: 10px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #5dff8f;
}

.control-node__icon--robodk span:nth-child(1) {
  inset: 10px 10px 14px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.08), rgba(139, 92, 246, 0.18));
  border: 2px solid rgba(139, 92, 246, 0.54);
}
.control-node__icon--robodk span:nth-child(2) {
  left: 20px;
  top: 18px;
  width: 34px;
  height: 22px;
  border-left: 2px solid #8b5cf6;
  border-bottom: 2px solid #8b5cf6;
  transform: skew(-22deg);
}
.control-node__icon--robodk span:nth-child(3) {
  left: 44px;
  top: 18px;
  width: 18px;
  height: 18px;
  border-right: 2px dashed #21c6ff;
  border-top: 2px dashed #21c6ff;
}
.control-node__icon--robodk span:nth-child(4) {
  right: 12px;
  top: 14px;
  width: 18px;
  height: 18px;
  border-radius: 999px;
  background: rgba(139, 92, 246, 0.18);
  color: #8b5cf6;
}

.control-node__icon--bridge span:nth-child(1) {
  left: 8px;
  top: 24px;
  width: 22px;
  height: 16px;
  border-radius: 12px;
  background: linear-gradient(180deg, #1e293b, #334155);
}
.control-node__icon--bridge span:nth-child(2) {
  right: 8px;
  top: 24px;
  width: 22px;
  height: 16px;
  border-radius: 12px;
  background: linear-gradient(180deg, #0f9db3, #21c6ff);
}
.control-node__icon--bridge span:nth-child(3) {
  left: 24px;
  right: 24px;
  top: 30px;
  height: 4px;
  border-radius: 999px;
  background: linear-gradient(90deg, #5dff8f, #21c6ff);
}
.control-node__icon--bridge span:nth-child(4) {
  left: 34px;
  top: 18px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 3px solid #f59e0b;
}

.control-node__icon--turtlebot span:nth-child(1) {
  inset: 26px 16px 8px;
  border-radius: 18px;
  background: linear-gradient(180deg, #dce8ef, #a7bcc9);
  border: 1px solid rgba(15, 23, 42, 0.08);
}
.control-node__icon--turtlebot span:nth-child(2) {
  inset: 10px 22px 26px;
  border-radius: 14px;
  background: linear-gradient(180deg, #eff6fb, #d1e0e8);
  border: 1px solid rgba(15, 23, 42, 0.08);
}
.control-node__icon--turtlebot span:nth-child(3) {
  left: 31px;
  top: 4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: radial-gradient(circle, #94f7ff 35%, #0f9db3 36%, #0f9db3 64%, transparent 65%);
}
.control-node__icon--turtlebot span:nth-child(4) {
  left: 8px;
  right: 8px;
  bottom: 10px;
  height: 8px;
  border-radius: 999px;
  background: linear-gradient(90deg, #334155 12%, transparent 12%, transparent 88%, #334155 88%);
}

.control-node--side {
  min-height: 202px;
  align-content: start;
}

.control-node--center {
  min-height: 250px;
  padding-bottom: 22px;
}

.control-node--bottom {
  min-height: 186px;
}

.control-conveyor-art {
  position: relative;
  height: 96px;
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(226, 232, 240, 0.68), rgba(255, 255, 255, 0.68));
}

.control-conveyor-art__belt {
  position: absolute;
  left: 10px;
  right: 10px;
  top: 44px;
  height: 16px;
  border-radius: 999px;
  background: linear-gradient(90deg, #64748b, #94a3b8, #64748b);
}

.control-conveyor-art__plate {
  position: absolute;
  top: 40px;
  width: 46px;
  height: 24px;
  border-radius: 8px;
  background: linear-gradient(180deg, #d5dde5, #94a3b8);
  animation: conveyor-slide 5.2s linear infinite;
}

.control-conveyor-art__plate--a { left: 16px; animation-delay: 0s; }
.control-conveyor-art__plate--b { left: 74px; animation-delay: 1.2s; }
.control-conveyor-art__plate--c { left: 132px; animation-delay: 2.4s; }

.control-conveyor-art__vision {
  position: absolute;
  right: 24px;
  top: 12px;
  width: 44px;
  height: 20px;
  border-radius: 12px;
  background: linear-gradient(180deg, #0f172a, #334155);
}

.control-conveyor-art__vision::after {
  content: '';
  position: absolute;
  left: 16px;
  top: 5px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #21c6ff;
}

.control-conveyor-art__pi {
  position: absolute;
  right: 38px;
  top: 34px;
  width: 28px;
  height: 22px;
  border-radius: 10px;
  background: linear-gradient(180deg, #22c55e, #15803d);
}

.control-inspector {
  display: grid;
  gap: 18px;
  border-radius: 32px;
}

.control-inspector__header {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.control-inspector__header h3 {
  margin: 6px 0 0;
  color: #16324f;
  font-size: 1.5rem;
  letter-spacing: -0.03em;
}

.control-inspector__detail {
  color: #55657c;
  line-height: 1.65;
}

.control-inspector__meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.control-inspector__meta article,
.control-feed-item {
  padding: 14px;
  border-radius: 20px;
  border: 1px solid rgba(31, 46, 70, 0.08);
  background: rgba(255, 255, 255, 0.72);
}

.control-inspector__events {
  display: grid;
  gap: 10px;
}

.control-inspector__subhead {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  color: #16324f;
}

.control-feed-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.control-feed-item p {
  margin: 0;
  color: #1e293b;
  line-height: 1.45;
}

.control-inspector__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.control-node--good { --node-accent: rgba(34, 197, 94, 0.24); }
.control-node--warn { --node-accent: rgba(245, 158, 11, 0.22); }
.control-node--danger { --node-accent: rgba(239, 68, 68, 0.2); }
.control-node--neutral { --node-accent: rgba(148, 163, 184, 0.18); }
.control-node--simulation { --node-accent: rgba(139, 92, 246, 0.2); }

.control-node::after {
  content: '';
  position: absolute;
  inset: 10px;
  border-radius: 22px;
  border: 1px solid var(--node-accent);
  opacity: 0;
  transition: opacity 180ms ease;
}

.control-node:hover::after,
.control-node.is-selected::after {
  opacity: 1;
}

@keyframes conveyor-slide {
  0% { transform: translateX(0); opacity: 0.45; }
  50% { transform: translateX(12px); opacity: 1; }
  100% { transform: translateX(24px); opacity: 0.45; }
}

@media (max-width: 1400px) {
  .control-hero {
    gap: 12px;
    padding: 14px;
  }

  .control-hero__header,
  .control-scene,
  .control-inspector {
    padding: 14px;
  }

  .control-hero__header {
    gap: 12px;
    padding: 14px 16px;
  }

  .control-hero__header h2 {
    margin-top: 6px;
    font-size: clamp(1.28rem, 2vw, 1.72rem);
    max-width: 28ch;
  }

  .control-hero__summary {
    display: none;
  }

  .control-hero__status {
    gap: 8px;
    max-width: 360px;
  }

  .control-pill {
    min-height: 30px;
    padding: 0.36rem 0.66rem;
    font-size: 0.74rem;
  }

  .control-hero__viewport {
    grid-template-columns: minmax(0, 1.42fr) minmax(280px, 0.62fr);
    gap: 12px;
    align-items: stretch;
  }

  .control-inspector {
    order: 0;
    max-height: 100%;
    overflow: auto;
  }

  .control-scene__hud {
    gap: 10px;
    margin-bottom: 10px;
  }

  .control-kpis {
    gap: 8px;
  }

  .control-kpi {
    padding: 9px 12px;
  }

  .control-kpi strong {
    margin-top: 3px;
    font-size: 0.98rem;
  }

  .control-kpi small {
    display: none;
  }

  .control-flow-legend {
    gap: 8px;
    max-width: 320px;
  }

  .control-flow-legend span {
    min-height: 30px;
    padding: 0.34rem 0.58rem;
    font-size: 0.72rem;
  }

  .control-flow-legend__line {
    width: 22px;
  }

  .control-scene__board {
    min-height: 392px;
    padding: 8px 6px 4px;
    background:
      radial-gradient(circle at calc(50% + var(--pointer-x)) calc(42% + var(--pointer-y)), rgba(33, 198, 255, 0.06), transparent 22%),
      linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(247, 250, 252, 0.94));
  }

  .control-edge {
    opacity: 0.24;
  }

  .control-zone {
    left: 14px;
    right: 14px;
    gap: 12px;
  }

  .control-zone--top {
    top: 14px;
  }

  .control-zone--middle {
    top: 140px;
    grid-template-columns: minmax(190px, 1fr) minmax(280px, 1.18fr) minmax(190px, 1fr);
  }

  .control-zone--bottom {
    bottom: 8px;
  }

  .control-node {
    gap: 4px;
    padding: 9px 11px;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.94);
    border-color: rgba(31, 46, 70, 0.14);
    box-shadow: 0 14px 30px rgba(31, 46, 70, 0.08);
  }

  .control-node strong {
    font-size: 0.9rem;
    line-height: 1.14;
  }

  .control-node small {
    display: none;
  }

  .control-node__status {
    gap: 6px;
    font-size: 0.7rem;
  }

  .control-node__icon {
    width: 82px;
    height: 66px;
    zoom: 0.58;
  }

  .control-node__metric {
    display: none;
  }

  .control-node--side,
  .control-node--center,
  .control-node--bottom {
    min-height: 96px;
  }

  .control-conveyor-art {
    height: 38px;
    border-radius: 14px;
  }

  .control-conveyor-art__belt {
    top: 18px;
    height: 7px;
  }

  .control-conveyor-art__plate {
    top: 15px;
    width: 26px;
    height: 12px;
  }

  .control-conveyor-art__plate--a { left: 14px; }
  .control-conveyor-art__plate--b { left: 58px; }
  .control-conveyor-art__plate--c { left: 102px; }

  .control-conveyor-art__vision {
    top: 5px;
    right: 14px;
    width: 24px;
    height: 12px;
  }

  .control-conveyor-art__vision::after {
    left: 9px;
    top: 3px;
    width: 6px;
    height: 6px;
  }

  .control-conveyor-art__pi {
    top: 20px;
    right: 20px;
    width: 16px;
    height: 12px;
    border-radius: 6px;
  }
}

@media (max-width: 1100px) {
  .control-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .control-hero__viewport { grid-template-columns: 1fr; }
  .control-inspector { order: -1; }
}

@media (max-width: 1024px) {
  .control-hero { min-height: auto; }
  .control-hero__header,
  .control-scene,
  .control-inspector {
    padding: 18px;
    height: auto;
    min-height: 0;
  }
  .control-hero__header { flex-direction: column; }
  .control-hero__status { justify-content: flex-start; max-width: none; }
  .control-scene__hud { flex-direction: column; }
  .control-flow-legend { justify-content: flex-start; max-width: none; }
  .control-scene__board {
    min-height: auto;
    display: grid;
    gap: 14px;
    padding: 14px;
  }
  .control-scene__edges {
    display: none;
  }
  .control-zone {
    position: static;
    left: auto;
    right: auto;
  }
  .control-zone--top,
  .control-zone--bottom { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .control-zone--middle { grid-template-columns: 1fr; }
  .control-inspector { overflow: visible; }
}

@media (max-width: 760px) {
  .control-hero { padding: 14px; border-radius: 24px; }
  .control-hero__header h2 { max-width: none; font-size: 1.7rem; }
  .control-kpis,
  .control-zone--top,
  .control-zone--bottom,
  .control-inspector__meta { grid-template-columns: 1fr; }
  .control-feed-item,
  .control-inspector__header { flex-direction: column; }
}
</style>
