<template>
  <div class="zdnix-scale-viewport">
    <main class="app-shell zdnix-shell" :style="shellScaleStyle">
    <header class="zdnix-topbar panel" aria-label="ZDnix 상단 내비게이션">
      <RouterLink to="/" class="zdnix-brand" aria-label="대시보드 홈으로 이동">
        <span class="zdnix-brand__mark">
          <img :src="logoIcon" alt="ZDnix" />
        </span>
        <span class="zdnix-brand__copy" aria-hidden="true">
          <strong>ZDnix</strong>
        </span>
      </RouterLink>

      <nav class="zdnix-nav" aria-label="주요 화면">
        <RouterLink
          v-for="routeItem in APP_ROUTES"
          :key="routeItem.name"
          :to="routeItem.path"
          class="zdnix-nav__link"
          :class="{ active: activeRoute.name === routeItem.name }"
        >
          <img :src="routeIcon(routeItem.name)" :alt="`${routeItem.label} 아이콘`" />
          <span>{{ routeItem.label }}</span>
        </RouterLink>
      </nav>

      <div class="zdnix-topbar__actions">
        <div class="zdnix-alert-menu">
          <button type="button" class="zdnix-icon-button" aria-label="알림" @click="notificationOpen = !notificationOpen">
            <img :src="bellIcon" alt="" aria-hidden="true" />
            <span v-if="alertCount" class="zdnix-badge">{{ alertCount }}</span>
          </button>
          <div v-if="notificationOpen" class="zdnix-alert-drawer" role="dialog" aria-label="최근 알림">
            <div class="zdnix-alert-drawer__head">
              <strong>최근 WARN/ERROR</strong>
              <button type="button" @click="notificationOpen = false">닫기</button>
            </div>
            <div class="zdnix-alert-list">
              <article v-for="event in drawerEvents" :key="event.id" class="zdnix-alert-row" :class="`zdnix-alert-row--${toneClass(event.severity)}`">
                <span>{{ event.severity }}</span>
                <div>
                  <p>{{ eventMessage(event) }}</p>
                  <small>{{ event.source }} · {{ formatClock(event.timestamp) }}</small>
                </div>
              </article>
              <p v-if="!drawerEvents.length" class="zdnix-alert-empty">최근 경고/오류 없음</p>
            </div>
            <RouterLink class="zdnix-drawer-link" to="/telemetry" @click="notificationOpen = false">알림/로그 보기</RouterLink>
          </div>
        </div>
        <button type="button" class="zdnix-icon-button" aria-label="도움말">
          <img :src="helpIcon" alt="" aria-hidden="true" />
        </button>

        <details class="zdnix-gateway-menu">
          <summary>
            <img :src="userIcon" alt="" aria-hidden="true" />
            <span>관리자</span>
            <img :src="chevronIcon" alt="" aria-hidden="true" />
          </summary>
          <div class="zdnix-gateway-menu__body">
            <span class="chip" :class="toneClass(connectionState)">{{ connectionStateLabel(connectionState) }}</span>
            <label class="gateway-field">
              <span>게이트웨이 주소</span>
              <input v-model="gatewayUrl" type="text" spellcheck="false" inputmode="url" placeholder="http://localhost:8765" />
            </label>
            <div class="tool-buttons">
              <button class="secondary" type="button" @click="connectGateway">연결 다시 시도</button>
              <button class="secondary" type="button" @click="refreshFromGateway">스냅샷 새로고침</button>
            </div>
            <p>{{ statusNote }}</p>
            <div class="zdnix-admin-links">
              <RouterLink to="/servers">관리자 진단</RouterLink>
              <RouterLink to="/telemetry">알림/로그</RouterLink>
            </div>
          </div>
        </details>
      </div>
    </header>

    <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, provide, ref } from 'vue';
import { RouterLink, RouterView, useRoute } from 'vue-router';
import { fetchDevicesSnapshot, fetchGatewayEvents, fetchGatewaySnapshot, getGatewayBaseUrl, openGatewaySocket, sendGatewayCommand } from './lib/dashboardClient';
import { applyMockCommand, createMockRuntime, createMockSnapshot } from '../shared/mockTelemetry';
import { APP_ROUTE_MAP, APP_ROUTES, type AppRouteName } from '../shared/navigation';
import { dashboardContextKey } from './components/dashboardContext';
import { createFallbackDevicesSnapshot, type DeviceDetail, type DeviceEvent, type DeviceId, type DeviceNode, type DeviceStream, type DevicesSnapshot, type VirtualModelState } from '../shared/devices';
import type { CommandName, ConnectionState, DashboardSnapshot, GatewayMessage, TelemetryEvent } from '../shared/telemetry';

import logoIcon from './assets/dashboard/brand/zdnix-symbol.png';
import homeIcon from './assets/dashboard/ui/Home.png';
import serverIcon from './assets/dashboard/ui/Server.png';
import networkIcon from './assets/dashboard/ui/Network.png';
import bellIcon from './assets/dashboard/ui/Bell.png';
import databaseIcon from './assets/dashboard/ui/Database.png';
import helpIcon from './assets/dashboard/ui/HelpCircle.png';
import userIcon from './assets/dashboard/ui/UserCircle.png';
import chevronIcon from './assets/dashboard/ui/ChevronDown.png';

const route = useRoute();
const gatewayUrl = ref(getGatewayBaseUrl());
const connectionState = ref<ConnectionState>('connecting');
const statusNote = ref('게이트웨이 로딩 중');
const snapshot = ref<DashboardSnapshot>(createMockSnapshot(createMockRuntime()));
const devicesSnapshot = ref<DevicesSnapshot>(createFallbackDevicesSnapshot());
const events = ref<TelemetryEvent[]>(snapshot.value.events);
const busyCommand = ref<CommandName | null>(null);
const lastSyncLabel = ref('모의 데이터');
const socket = ref<WebSocket | null>(null);
const localRuntime = ref(createMockRuntime());
const shellScale = ref(1);
const notificationOpen = ref(false);

const DASHBOARD_BASE_WIDTH = 1840;
const DASHBOARD_BASE_HEIGHT = 1020;
const DASHBOARD_MARGIN = 20;

const shellScaleStyle = computed(() => ({
  width: `${DASHBOARD_BASE_WIDTH}px`,
  height: `${DASHBOARD_BASE_HEIGHT}px`,
  transform: `translate(-50%, -50%) scale(${shellScale.value})`,
}));

const activeRoute = computed(() => {
  const name = route.name;
  if (typeof name === 'string' && name in APP_ROUTE_MAP) {
    return APP_ROUTE_MAP[name as AppRouteName];
  }
  return APP_ROUTE_MAP.home;
});

const lineCode = computed(() => snapshot.value.line.name.replace(/^(Line|라인)\s+/i, ''));
const onlineDeviceCount = computed(() => snapshot.value.devices.filter((device) => device.online).length);
const websocketLabel = computed(() => {
  if (connectionState.value === 'online') return '정상';
  if (connectionState.value === 'mock') return '모의';
  if (connectionState.value === 'degraded') return '지연';
  if (connectionState.value === 'offline') return '오프라인';
  return '연결 중';
});
const drawerEvents = computed(() =>
  [...snapshot.value.alarms, ...events.value]
    .filter((event) => event.severity === 'WARN' || event.severity === 'ERROR' || event.severity === 'CRITICAL')
    .slice(0, 6),
);
const alertCount = computed(() => drawerEvents.value.length);

const routeIcons: Record<AppRouteName, string> = {
  home: homeIcon,
  devices: serverIcon,
  simulation: networkIcon,
  telemetry: bellIcon,
  servers: databaseIcon,
};

provide(dashboardContextKey, {
  snapshot,
  devicesSnapshot,
  events,
  connectionState,
  gatewayUrl,
  busyCommand,
  statusNote,
  lastSyncLabel,
  lineCode,
  onlineDeviceCount,
  websocketLabel,
  connectGateway,
  refreshFromGateway,
  runCommand,
  clearEvents,
});

onMounted(async () => {
  syncShellScale();
  window.addEventListener('resize', syncShellScale);
  await connectGateway();
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', syncShellScale);
  closeSocket();
});

function routeIcon(name: AppRouteName) {
  return routeIcons[name];
}

function syncShellScale() {
  const widthScale = (window.innerWidth - DASHBOARD_MARGIN) / DASHBOARD_BASE_WIDTH;
  const heightScale = (window.innerHeight - DASHBOARD_MARGIN) / DASHBOARD_BASE_HEIGHT;
  shellScale.value = Math.min(1, Math.max(0.45, widthScale, 0), Math.max(0.45, heightScale, 0));
}

async function connectGateway() {
  closeSocket();
  connectionState.value = 'connecting';
  statusNote.value = '게이트웨이 로딩 중';

  try {
    const [remoteSnapshot, remoteEvents, remoteDevicesSnapshot] = await Promise.all([
      fetchGatewaySnapshot(gatewayUrl.value),
      fetchGatewayEvents(gatewayUrl.value),
      fetchDevicesSnapshot(gatewayUrl.value),
    ]);
    snapshot.value = remoteSnapshot;
    devicesSnapshot.value = remoteDevicesSnapshot;
    events.value = remoteEvents.slice(0, 120);
    connectionState.value = 'online';
    lastSyncLabel.value = `동기화 ${formatClock(remoteSnapshot.timestamp)}`;
    statusNote.value = 'REST 스냅샷 수신';
    addEvent('INFO', 'gateway', '초기 스냅샷 수신');
    openSocket();
  } catch {
    useLocalMock();
  }
}

async function refreshFromGateway() {
  try {
    const [remoteSnapshot, remoteDevicesSnapshot] = await Promise.all([
      fetchGatewaySnapshot(gatewayUrl.value),
      fetchDevicesSnapshot(gatewayUrl.value),
    ]);
    snapshot.value = remoteSnapshot;
    devicesSnapshot.value = remoteDevicesSnapshot;
    connectionState.value = 'online';
    lastSyncLabel.value = `동기화 ${formatClock(remoteSnapshot.timestamp)}`;
    statusNote.value = '스냅샷 새로고침';
    addEvent('INFO', 'gateway', '게이트웨이 스냅샷 새로고침');
  } catch {
    useLocalMock();
  }
}

async function runCommand(command: CommandName) {
  if (requiresConfirmation(command)) {
    const allowed = typeof window === 'undefined' || window.confirm(`${commandLabel(command)} 명령을 실행할까요?`);
    if (!allowed) return;
  }

  busyCommand.value = command;

  try {
    if (snapshot.value.gatewayMode === 'live') {
      const result = await sendGatewayCommand(gatewayUrl.value, command);
      devicesSnapshot.value = await fetchDevicesSnapshot(gatewayUrl.value).catch(() => devicesSnapshot.value);
      addEvent(result.accepted ? 'INFO' : 'ERROR', 'command', translateCommandResult(result.command, result.accepted));
      statusNote.value = result.accepted
        ? `${commandLabel(result.command)} 명령 처리 완료`
        : `${commandLabel(result.command)} 명령 거부`;
      return;
    }

    applyMockCommand(localRuntime.value, command);
    const fallbackSnapshot = createMockSnapshot(localRuntime.value);
    snapshot.value = fallbackSnapshot;
    lastSyncLabel.value = `동기화 ${formatClock(fallbackSnapshot.timestamp)}`;
    addEvent('INFO', 'command', `${commandLabel(command)} 모의 명령 반영`);
    statusNote.value = '모의 텔레메트리 갱신';
  } catch {
    addEvent('ERROR', 'command', '명령 처리 실패');
    statusNote.value = '명령 처리 실패';
  } finally {
    busyCommand.value = null;
  }
}

function openSocket() {
  socket.value = openGatewaySocket(gatewayUrl.value, {
    onOpen: () => {
      connectionState.value = 'online';
      statusNote.value = 'WebSocket 연결';
      addEvent('INFO', 'websocket', '실시간 텔레메트리 연결');
    },
    onClose: () => {
      connectionState.value = 'degraded';
      statusNote.value = 'WebSocket 연결 종료';
      addEvent('WARN', 'websocket', '실시간 스트림 종료');
    },
    onError: () => {
      connectionState.value = 'degraded';
      statusNote.value = '실시간 스트림 오류';
      addEvent('ERROR', 'websocket', '실시간 스트림 오류');
    },
    onMessage: handleGatewayMessage,
  });
}

function handleGatewayMessage(message: GatewayMessage) {
  if (message.type === 'snapshot') {
    snapshot.value = message.snapshot;
    lastSyncLabel.value = `동기화 ${formatClock(message.snapshot.timestamp)}`;
    connectionState.value = 'online';
    return;
  }

  if (message.type === 'devices_snapshot') {
    devicesSnapshot.value = message.snapshot;
    return;
  }

  if (message.type === 'device_update') {
    upsertDeviceNode(message.device);
    return;
  }

  if (message.type === 'device_detail_update') {
    upsertDeviceDetail(message.detail);
    return;
  }

  if (message.type === 'virtual_model_update') {
    upsertVirtualModel(message.model);
    return;
  }

  if (message.type === 'stream_status') {
    upsertDeviceStream(message.stream);
    return;
  }

  if (message.type === 'device_event') {
    addDeviceEvent(message.event);
    return;
  }

  if (message.type === 'event') {
    addEvent(message.event.severity, message.event.source, eventMessage(message.event));
    return;
  }

  if (message.type !== 'command_result') {
    return;
  }

  addEvent(message.result.accepted ? 'INFO' : 'ERROR', 'command', translateCommandResult(message.result.command, message.result.accepted));
}

function upsertDeviceNode(device: DeviceNode) {
  devicesSnapshot.value = {
    ...devicesSnapshot.value,
    devices: devicesSnapshot.value.devices.some((item) => item.id === device.id)
      ? devicesSnapshot.value.devices.map((item) => (item.id === device.id ? device : item))
      : [...devicesSnapshot.value.devices, device],
  };
}

function upsertDeviceDetail(detail: DeviceDetail) {
  devicesSnapshot.value = {
    ...devicesSnapshot.value,
    details: {
      ...devicesSnapshot.value.details,
      [detail.id]: detail,
    },
  };
}

function upsertVirtualModel(model: VirtualModelState) {
  devicesSnapshot.value = {
    ...devicesSnapshot.value,
    virtualModels: {
      ...devicesSnapshot.value.virtualModels,
      [model.deviceId]: model,
    },
  };
}

function upsertDeviceStream(stream: DeviceStream) {
  devicesSnapshot.value = {
    ...devicesSnapshot.value,
    streams: devicesSnapshot.value.streams.some((item) => item.id === stream.id)
      ? devicesSnapshot.value.streams.map((item) => (item.id === stream.id ? stream : item))
      : [...devicesSnapshot.value.streams, stream],
  };
}

function addDeviceEvent(event: DeviceEvent) {
  devicesSnapshot.value = {
    ...devicesSnapshot.value,
    events: [event, ...devicesSnapshot.value.events].slice(0, 100),
  };
  addEvent(event.severity, event.source, event.message, event.timestamp);
}

function addEvent(severity: TelemetryEvent['severity'], source: string, message: string, timestamp = new Date().toISOString()) {
  events.value = [
    {
      id: `evt-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      timestamp,
      severity,
      source,
      message,
    },
    ...events.value,
  ].slice(0, 120);
}

function clearEvents() {
  events.value = [];
}

function closeSocket() {
  socket.value?.close();
  socket.value = null;
}

function useLocalMock() {
  localRuntime.value = createMockRuntime();
  snapshot.value = createMockSnapshot(localRuntime.value);
  devicesSnapshot.value = createFallbackDevicesSnapshot();
  events.value = snapshot.value.events;
  connectionState.value = 'mock';
  lastSyncLabel.value = '모의 데이터';
  statusNote.value = '모의 텔레메트리 전환';
  addEvent('WARN', 'fallback', '모의 텔레메트리 사용');
  closeSocket();
}

function requiresConfirmation(command: CommandName) {
  return command === 'process.stop' || command === 'process.reset_error' || command === 'robot.home';
}

function commandLabel(command: CommandName) {
  const map: Record<CommandName, string> = {
    'process.start': '공정 시작',
    'process.pause': '일시 정지',
    'process.resume': '재개',
    'process.stop': '공정 정지',
    'process.reset_error': '오류 초기화',
    'robot.home': '로봇 홈 복귀',
    'system.refresh': '새로고침',
  };
  return map[command];
}

function translateCommandResult(command: CommandName, accepted: boolean) {
  return accepted ? `${commandLabel(command)} 명령 승인` : `${commandLabel(command)} 명령 거부`;
}

function toneClass(value: ConnectionState | string) {
  const normalized = String(value).toUpperCase();
  if (normalized.includes('OFFLINE') || normalized.includes('ERROR') || normalized.includes('CRITICAL') || normalized.includes('FAULT')) {
    return 'danger';
  }
  if (normalized.includes('DEGRADED') || normalized.includes('WARN') || normalized.includes('PAUSED') || normalized.includes('CONNECTING')) {
    return 'warn';
  }
  if (normalized.includes('ONLINE') || normalized.includes('MOCK') || normalized.includes('READY') || normalized.includes('RUNNING') || normalized.includes('INFO')) {
    return 'good';
  }
  return 'neutral';
}

function connectionStateLabel(state: ConnectionState) {
  const map: Record<ConnectionState, string> = {
    connecting: '연결 중',
    online: '실시간 연결',
    degraded: '지연 상태',
    offline: '오프라인',
    mock: '모의 모드',
  };
  return map[state];
}

function eventMessage(event: TelemetryEvent) {
  if (/[가-힣]/.test(event.message)) {
    return event.message;
  }

  if (event.source === 'gateway' && /connected/i.test(event.message)) return '게이트웨이 정상';
  if (event.source === 'modbus') return 'Modbus 로컬 텔레메트리';
  if (event.source === 'fallback') return '모의 텔레메트리 사용';
  return '상태 갱신';
}

function formatClock(timestamp: string) {
  return new Intl.DateTimeFormat('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(timestamp));
}
</script>
