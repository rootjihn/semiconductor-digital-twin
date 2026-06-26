<template>
  <section ref="rootRef" class="zdnix-home" aria-label="ZDnix 반도체 후공정 관제 대시보드">
    <header class="zdnix-home__header zd-card">
      <div>
        <p class="zd-eyebrow">DASHBOARD</p>
        <h1>반도체 후공정 관제 대시보드</h1>
      </div>
      <div class="zd-status-chip-row" aria-label="운영 상태">
        <span class="zd-status-chip" :class="connectionToneClass"><i></i>Gateway: {{ gatewayModeLabel }}</span>
        <span class="zd-status-chip" :class="lineToneClass"><i></i>전체 라인: {{ lineStateLabel }}</span>
        <span class="zd-status-chip zd-status-chip--alarm"><img :src="alertIcon" alt="" />알람: {{ activeAlarmCount }}건</span>
        <span class="zd-status-chip"><img :src="clockIcon" alt="" />마지막 갱신: {{ lastSyncTime }}</span>
      </div>
    </header>

    <section class="zdnix-main-grid">
      <aside class="zdnix-left-rail" aria-label="좌측 상태 요약">
        <article class="zd-card zd-side-card">
          <div class="zd-card-title">
            <span><img :src="checkIcon" alt="" />장비 상태 요약</span>
          </div>
          <div class="zd-state-list">
            <div v-for="item in stateSummary" :key="item.label" class="zd-state-row">
              <span><i :class="`zd-dot--${item.tone}`"></i>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
        </article>

        <article class="zd-card zd-side-card zd-side-card--comm">
          <div class="zd-card-title">
            <span><img :src="wifiIcon" alt="" />통신 응답 상태</span>
          </div>
          <div class="zd-comm-summary zd-comm-summary--compact">
            <div class="zd-comm-metric zd-comm-metric--blue"><span>응답 평균</span><strong>{{ networkSummary.overall }} ms</strong></div>
            <div class="zd-comm-metric zd-comm-metric--green"><span>최대 지연</span><strong>{{ networkSummary.max }} ms</strong></div>
          </div>
          <div class="zd-comm-pill-row" aria-label="통신 상태 요약">
            <span class="zd-comm-pill zd-comm-pill--good"><i></i>정상 {{ communicationHealthyCount }}/{{ communicationRows.length }}</span>
            <span class="zd-comm-pill zd-comm-pill--warn"><i></i>Retry {{ networkSummary.retry }}</span>
            <span class="zd-comm-pill" :class="networkSummary.timeout > 0 ? 'zd-comm-pill--danger' : 'zd-comm-pill--good'"><i></i>Timeout {{ networkSummary.timeout }}</span>
          </div>
        </article>

        <article class="zd-card zd-side-card zd-side-card--events">
          <div class="zd-card-title">
            <span><img :src="activityIcon" alt="" />최근 알람 / 이벤트</span>
          </div>
          <div class="zd-event-list">
            <article v-for="event in recentEvents" :key="event.id" class="zd-event-row">
              <img :src="event.icon" alt="" />
              <div>
                <p>{{ event.message }}</p>
                <small>{{ event.source }} · {{ event.time }}</small>
              </div>
            </article>
          </div>
          <button type="button" class="zd-link-button" @click="navigate('telemetry')">
            전체 이벤트 보기 <img :src="arrowIcon" alt="" />
          </button>
        </article>
      </aside>

      <section class="zdnix-center-column" aria-label="중앙 라인 맵과 KPI">
      <main class="zd-card zd-map-card" aria-label="라인 구성 맵">
        <div class="zd-map-card__title">
          <div>
            <p class="zd-eyebrow">NETWORK TOPOLOGY</p>
            <h2>라인 구성 맵</h2>
          </div>
          <span class="zd-map-card__legend"><i></i>Live Link</span>
        </div>

        <section class="zd-network-map" aria-label="장비 네트워크 맵">
          <img class="zd-network-map__pattern" :src="networkPattern" alt="" aria-hidden="true" />
          <svg class="zd-connection-layer" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <marker id="zd-arrow-green" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
                <path d="M0 0 L6 3 L0 6 Z" fill="#22a981" />
              </marker>
              <marker id="zd-arrow-blue" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
                <path d="M0 0 L6 3 L0 6 Z" fill="#2384d5" />
              </marker>
            </defs>
            <path class="zd-link zd-link--good" d="M49 41 C47 33 45 24 43 16" marker-end="url(#zd-arrow-green)" />
            <path class="zd-link zd-link--good" d="M39 53 C35 52 33 51 31 51" marker-end="url(#zd-arrow-green)" />
            <path class="zd-link zd-link--good" d="M41 62 C38 70 35 78 33 84" marker-end="url(#zd-arrow-green)" />
            <path class="zd-link zd-link--blue" d="M61 53 C65 52 67 51 69 51" marker-end="url(#zd-arrow-blue)" />
            <path class="zd-link zd-link--good" d="M59 62 C62 70 65 78 67 84" marker-end="url(#zd-arrow-green)" />
          </svg>

          <button
            v-for="node in mapNodes"
            :key="node.id"
            type="button"
            class="zd-node"
            :class="[`zd-node--${node.id}`, { 'zd-node--selected': selectedNodeId === node.id }]"
            @click="selectedNodeId = node.id"
          >
            <span class="zd-node__image" :class="`zd-node__image--${node.tone}`">
              <img :src="node.image" :alt="node.label" />
            </span>
            <span class="zd-node__info">
              <strong>{{ node.label }}</strong>
              <small>{{ node.ip }}</small>
              <em><i :class="`zd-dot--${node.tone}`"></i>{{ node.statusLabel }}</em>
            </span>
          </button>

          <button
            type="button"
            class="zd-node zd-node--gateway"
            :class="{ 'zd-node--selected': selectedNodeId === 'gateway' }"
            @click="selectedNodeId = 'gateway'"
          >
            <span class="zd-node__image zd-node__image--server" :class="`zd-node__image--${gatewayNode.tone}`">
              <img :src="gatewayNode.image" :alt="gatewayNode.label" />
            </span>
            <span class="zd-node__info zd-node__info--server">
              <strong>Gateway / Server</strong>
              <small>Gateway · Modbus Server · WebSocket/API</small>
              <em><i :class="`zd-dot--${gatewayNode.tone}`"></i>{{ gatewayNode.statusLabel }}</em>
            </span>
          </button>
        </section>
      </main>

      <section class="zd-kpi-row" aria-label="핵심 KPI">
        <article class="zd-card zd-kpi-card">
          <img :src="eyeIcon" alt="" />
          <span>현재 단계</span>
          <strong>{{ activeStageLabel }}</strong>
        </article>
        <article class="zd-card zd-kpi-card">
          <img :src="clockIcon" alt="" />
          <span>사이클 시간</span>
          <strong>{{ snapshot.line.cycleTimeMs }} ms / 목표 {{ snapshot.line.targetCycleTimeMs }} ms</strong>
        </article>
        <article class="zd-card zd-kpi-card zd-kpi-card--alarm">
          <img :src="alertIcon" alt="" />
          <span>활성 알람</span>
          <strong>{{ activeAlarmCount }}건</strong>
        </article>
      </section>
      </section>

      <aside class="zdnix-right-rail" aria-label="우측 상세 정보">
        <article class="zd-card zd-selected-panel">
          <div class="zd-card-title">
            <span><img :src="shieldIcon" alt="" />선택 노드</span>
            <span class="zd-mini-chip" :class="`zd-mini-chip--${selectedNode.tone}`">{{ selectedNode.statusLabel }}</span>
          </div>
          <div class="zd-selected-node">
            <span class="zd-selected-node__image">
              <img :src="selectedNode.image" :alt="selectedNode.label" />
            </span>
            <div>
              <h3>{{ selectedNode.label }}</h3>
              <p>{{ selectedNode.subtitle }}</p>
            </div>
          </div>
          <div class="zd-detail-list">
            <div><span>상태</span><strong><i :class="`zd-dot--${selectedNode.tone}`"></i>{{ selectedNode.statusLabel }}</strong></div>
            <div><span>통신</span><strong>{{ selectedNode.communication }}</strong></div>
            <div><span>최근 값</span><strong>{{ selectedNode.lastValue }}</strong></div>
            <div><span>응답 기준</span><strong>{{ selectedNode.responseBasis }}</strong></div>
          </div>

          <div class="zd-panel-section-title">최근 알람 / 이벤트</div>
          <div class="zd-alarm-list">
            <article v-for="event in panelEvents" :key="event.id" class="zd-alarm-row">
              <span :class="`zd-severity zd-severity--${event.tone}`">{{ event.severity }}</span>
              <div>
                <p>{{ event.source }}: {{ event.message }}</p>
                <small>{{ event.time }}</small>
              </div>
            </article>
          </div>
          <button type="button" class="zd-link-button zd-link-button--full" @click="navigate('devices')">
            상세 정보 보기 <img :src="arrowIcon" alt="" />
          </button>
        </article>

        <article class="zd-card zd-gateway-card">
          <div class="zd-card-title">
            <span><img :src="serverIcon" alt="" />Gateway 상태</span>
          </div>
          <div class="zd-detail-list zd-detail-list--compact">
            <div><span>상태</span><strong><i :class="`zd-dot--${gatewayTone}`"></i>{{ gatewayModeLabel }}</strong></div>
            <div><span>마지막 수신</span><strong>{{ lastSyncTime }}</strong></div>
            <div><span>WebSocket</span><strong>{{ websocketLabel }}</strong></div>
            <div><span>Adapter Mode</span><strong>{{ snapshot.gatewayMode === 'live' ? 'LIVE' : 'MOCK' }}</strong></div>
            <div><span>Timeout</span><strong>{{ networkSummary.timeout }}</strong></div>
            <div><span>Retry</span><strong>{{ networkSummary.retry }}</strong></div>
          </div>
        </article>
      </aside>
    </section>

  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import gsap from 'gsap';
import { useDashboardContext } from '../components/dashboardContext';
import type { AppRouteName } from '../../shared/navigation';
import type { DeviceState, LineState, Severity, TelemetryEvent } from '../../shared/telemetry';

import dobotImage from '../assets/dashboard/devices/device-dobot-magician.png';
import turtlebotImage from '../assets/dashboard/devices/device-turtlebot3-waffle-pi.png';
import conveyorImage from '../assets/dashboard/devices/device-conveyor-rpi5.png';
import realsenseImage from '../assets/dashboard/devices/device-realsense-camera.png';
import robodkImage from '../assets/dashboard/devices/device-robodk-monitor.png';
import serverImage from '../assets/dashboard/devices/device-server-rack.png';
import networkPattern from '../assets/dashboard/backgrounds/network-pattern.png';

import activityIcon from '../assets/dashboard/ui/Activity.png';
import alertIcon from '../assets/dashboard/ui/AlertTriangle.png';
import arrowIcon from '../assets/dashboard/ui/ArrowRight.png';
import checkIcon from '../assets/dashboard/ui/CheckCircle.png';
import clockIcon from '../assets/dashboard/ui/Clock.png';
import eyeIcon from '../assets/dashboard/ui/Eye.png';
import refreshIcon from '../assets/dashboard/ui/RefreshCw.png';
import serverIcon from '../assets/dashboard/ui/Server.png';
import shieldIcon from '../assets/dashboard/ui/Shield.png';
import wifiIcon from '../assets/dashboard/ui/Wifi.png';

const router = useRouter();
const { snapshot, connectionState, lastSyncLabel, events, websocketLabel } = useDashboardContext();

const rootRef = ref<HTMLElement | null>(null);
const selectedNodeId = ref<NodeId>('dobot');
let animationContext: gsap.Context | undefined;

type NodeId = 'dobot' | 'turtlebot3' | 'conveyor' | 'vision' | 'robodk' | 'gateway';
type Tone = 'good' | 'warn' | 'danger' | 'neutral';

interface VisualNode {
  id: NodeId;
  label: string;
  subtitle: string;
  ip: string;
  image: string;
  statusLabel: string;
  state: DeviceState | 'READY';
  tone: Tone;
  communication: string;
  responseBasis: string;
  lastValue: string;
  latencyMs: number;
}

onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || !rootRef.value) return;
  animationContext = gsap.context(() => {
    gsap.from('.zd-card', { opacity: 0, y: 10, duration: 0.42, stagger: 0.035, ease: 'power2.out' });
    gsap.to('.zd-link', { strokeDashoffset: -24, repeat: -1, duration: 1.8, ease: 'none' });
  }, rootRef.value);
});

onBeforeUnmount(() => {
  animationContext?.revert();
});

const activeAlarmCount = computed(() => snapshot.value.alarms.filter((alarm) => !alarm.acknowledged || alarm.severity !== 'INFO').length);

const activeStage = computed(() => snapshot.value.process.stages.find((stage) => stage.id === snapshot.value.process.activeStage));
const activeStageLabel = computed(() => activeStage.value?.detail ?? activeStage.value?.label ?? '비전 검사');

const gatewayModeLabel = computed(() => (snapshot.value.gatewayMode === 'live' ? 'Live' : 'Mock'));
const lastSyncTime = computed(() => {
  if (lastSyncLabel.value !== '모의 데이터') return lastSyncLabel.value.replace('동기화 ', '');
  return formatTime(snapshot.value.timestamp);
});

const lineStateLabel = computed(() => {
  const map: Record<LineState, string> = {
    RUNNING: '가동',
    PAUSED: '일시 정지',
    STOPPED: '정지',
    FAULT: '장애',
  };
  return map[snapshot.value.line.state];
});

const lineToneClass = computed(() => `zd-status-chip--${toneFromLineState(snapshot.value.line.state)}`);
const gatewayTone = computed<Tone>(() => toneFromConnection(connectionState.value));
const connectionToneClass = computed(() => `zd-status-chip--${gatewayTone.value}`);

const stateSummary = computed(() => {
  const devices = snapshot.value.devices;
  const count = (...states: DeviceState[]) => devices.filter((device) => states.includes(device.state)).length;
  return [
    { label: '정상 대기', value: count('READY', 'IDLE'), tone: 'good' as Tone },
    { label: '작업 중', value: count('RUNNING', 'BUSY'), tone: 'good' as Tone },
    { label: '대기/인터락', value: count('WAITING'), tone: 'neutral' as Tone },
    { label: '경고', value: count('WARNING'), tone: 'warn' as Tone },
    { label: '오류', value: count('FAULT'), tone: 'danger' as Tone },
    { label: '오프라인', value: devices.filter((device) => !device.online || device.state === 'OFFLINE').length, tone: 'neutral' as Tone },
  ];
});

const visualNodes = computed<Record<NodeId, VisualNode>>(() => {
  const dobot = findDevice('dobot-arm');
  const conveyor = findDevice('conveyor-drive');
  const vision = findDevice('vision-camera');
  const edge = findDevice('edge-pc');
  const lineTone = toneFromLineState(snapshot.value.line.state);

  return {
    dobot: {
      id: 'dobot',
      label: 'Dobot Magician',
      subtitle: 'ROS 제어 / 케이블 연결',
      ip: '192.168.1.21',
      image: dobotImage,
      statusLabel: statusLabel(dobot?.state ?? 'READY'),
      state: dobot?.state ?? 'READY',
      tone: toneFromDeviceState(dobot?.state ?? 'READY'),
      communication: 'Dobot ROS 정상',
      responseBasis: 'ROS heartbeat',
      lastValue: dobot?.value ?? 'Home position',
      latencyMs: 3,
    },
    turtlebot3: {
      id: 'turtlebot3',
      label: 'TurtleBot3 Waffle Pi',
      subtitle: 'ROS bridge / Raspberry Pi 4',
      ip: '192.168.1.31',
      image: turtlebotImage,
      statusLabel: snapshot.value.line.state === 'RUNNING' ? 'READY' : lineStateLabel.value,
      state: 'READY',
      tone: lineTone === 'danger' ? 'warn' : 'good',
      communication: 'ROS bridge 정상',
      responseBasis: 'ROS heartbeat',
      lastValue: 'Heartbeat 수신',
      latencyMs: 8,
    },
    conveyor: {
      id: 'conveyor',
      label: 'Conveyor Belt / Raspberry Pi 5',
      subtitle: 'Raspberry Pi 5 / Modbus Client',
      ip: '192.168.1.41',
      image: conveyorImage,
      statusLabel: statusLabel(conveyor?.state ?? 'READY'),
      state: conveyor?.state ?? 'READY',
      tone: toneFromDeviceState(conveyor?.state ?? 'READY'),
      communication: 'Conveyor Pi 정상',
      responseBasis: 'Modbus read',
      lastValue: conveyor?.value ?? '셀 정상 응답',
      latencyMs: 4,
    },
    vision: {
      id: 'vision',
      label: 'Realsense / Vision',
      subtitle: 'Vision Stream / 검사 결과',
      ip: '192.168.1.51',
      image: realsenseImage,
      statusLabel: statusLabel(vision?.state ?? 'READY'),
      state: vision?.state ?? 'READY',
      tone: toneFromDeviceState(vision?.state ?? 'READY'),
      communication: 'Vision stream 정상',
      responseBasis: 'Frame timestamp',
      lastValue: vision?.value ?? '검사 결과 갱신',
      latencyMs: 7,
    },
    robodk: {
      id: 'robodk',
      label: 'RoboDK Simulation',
      subtitle: 'Digital Twin / 경로 검증',
      ip: '127.0.0.1',
      image: robodkImage,
      statusLabel: 'READY',
      state: 'READY',
      tone: 'good',
      communication: 'Simulation link 정상',
      responseBasis: 'API health',
      lastValue: '경로 대기',
      latencyMs: 12,
    },
    gateway: {
      id: 'gateway',
      label: 'Gateway / Server',
      subtitle: 'Gateway · Modbus Server · WebSocket/API',
      ip: '192.168.1.10',
      image: serverImage,
      statusLabel: gatewayModeLabel.value,
      state: 'READY',
      tone: gatewayTone.value,
      communication: websocketLabel.value,
      responseBasis: 'Gateway health',
      lastValue: edge?.value ?? '스냅샷 갱신',
      latencyMs: 6,
    },
  };
});

const mapNodes = computed(() => [
  visualNodes.value.dobot,
  visualNodes.value.turtlebot3,
  visualNodes.value.conveyor,
  visualNodes.value.vision,
  visualNodes.value.robodk,
]);
const gatewayNode = computed(() => visualNodes.value.gateway);
const selectedNode = computed(() => visualNodes.value[selectedNodeId.value]);

const communicationRows = computed(() => [
  { id: 'dobot', label: 'Dobot ROS', tone: visualNodes.value.dobot.tone, latencyMs: visualNodes.value.dobot.latencyMs },
  { id: 'turtlebot3', label: 'TurtleBot3 ROS', tone: visualNodes.value.turtlebot3.tone, latencyMs: visualNodes.value.turtlebot3.latencyMs },
  { id: 'conveyor', label: 'Conveyor Pi / Modbus', tone: visualNodes.value.conveyor.tone, latencyMs: visualNodes.value.conveyor.latencyMs },
  { id: 'vision', label: 'Vision Stream', tone: visualNodes.value.vision.tone, latencyMs: visualNodes.value.vision.latencyMs },
]);

const communicationHealthyCount = computed(() => communicationRows.value.filter((row) => row.tone === 'good').length);

const networkSummary = computed(() => {
  const latencies = communicationRows.value.map((row) => row.latencyMs);
  return {
    overall: Math.round(latencies.reduce((sum, item) => sum + item, 0) / latencies.length),
    max: Math.max(...latencies),
    timeout: snapshot.value.gatewayState === 'offline' ? 1 : 0,
    retry: connectionState.value === 'degraded' ? 2 : 1,
  };
});

const recentEvents = computed(() => normalizedEvents(events.value).slice(0, 5).map((event) => ({
  ...event,
  icon: event.tone === 'danger' ? alertIcon : event.source.includes('vision') ? eyeIcon : event.source.includes('gateway') ? refreshIcon : activityIcon,
})));

const panelEvents = computed(() => normalizedEvents([...snapshot.value.alarms, ...events.value]).slice(0, 3));

function navigate(page: AppRouteName) {
  void router.push({ name: page });
}

function findDevice(id: string) {
  return snapshot.value.devices.find((device) => device.id === id);
}

function normalizedEvents(sourceEvents: TelemetryEvent[]) {
  return sourceEvents.map((event) => ({
    id: event.id,
    severity: severityLabel(event.severity),
    source: sourceLabel(event.source),
    message: safeEventMessage(event),
    time: formatTime(event.timestamp),
    tone: toneFromSeverity(event.severity),
  }));
}

function safeEventMessage(event: TelemetryEvent) {
  if (event.source === 'production') return '생산 카운터 갱신';
  if (/양품|불량/.test(event.message)) return '생산 카운터 갱신';
  if (/throughput|처리량/i.test(event.message)) return '운영 속도 갱신';
  return event.message;
}

function sourceLabel(source: string) {
  const map: Record<string, string> = {
    gateway: 'gateway',
    websocket: 'websocket',
    command: 'command',
    fallback: 'fallback',
    mock: 'mock',
    control: 'control',
    safety: 'safety',
    vision: 'vision',
    health: 'health',
    production: 'production',
    cell: 'cell',
    modbus: 'modbus',
  };
  return map[source] ?? source;
}

function statusLabel(state: DeviceState) {
  const map: Record<DeviceState, string> = {
    READY: 'READY',
    RUNNING: 'RUNNING',
    BUSY: 'BUSY',
    WAITING: 'WAITING',
    WARNING: 'WARNING',
    FAULT: 'FAULT',
    OFFLINE: 'OFFLINE',
    IDLE: 'IDLE',
  };
  return map[state];
}

function severityLabel(severity: Severity) {
  const map: Record<Severity, string> = {
    INFO: 'INFO',
    WARN: 'WARN',
    ERROR: 'ERROR',
    CRITICAL: 'CRIT',
  };
  return map[severity];
}

function toneFromDeviceState(state: DeviceState): Tone {
  if (state === 'FAULT' || state === 'OFFLINE') return 'danger';
  if (state === 'WARNING' || state === 'WAITING') return 'warn';
  return 'good';
}

function toneFromLineState(state: LineState): Tone {
  if (state === 'FAULT') return 'danger';
  if (state === 'PAUSED' || state === 'STOPPED') return 'warn';
  return 'good';
}

function toneFromConnection(state: string): Tone {
  if (state === 'offline') return 'danger';
  if (state === 'degraded' || state === 'connecting') return 'warn';
  return 'good';
}

function toneFromSeverity(severity: Severity): Tone {
  if (severity === 'ERROR' || severity === 'CRITICAL') return 'danger';
  if (severity === 'WARN') return 'warn';
  return 'good';
}

function formatTime(timestamp: string) {
  return new Intl.DateTimeFormat('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(timestamp));
}
</script>
