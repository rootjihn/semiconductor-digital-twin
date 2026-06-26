<template>
  <section class="page-grid page-grid--detail server-page--diagnostic">
    <section class="panel surface-rise route-summary-panel server-overview-banner" :class="`server-overview-banner--${connectionState}`">
      <div>
        <p class="eyebrow">GATEWAY DIAGNOSTICS</p>
        <h2>관리자 진단</h2>
        <p class="subtitle">서버 운영 화면이 아니라 Gateway / WebSocket / Mock adapter 상태만 확인하는 숨김 진단 화면입니다.</p>
      </div>
      <div class="banner-meta">
        <span class="chip" :class="toneClass(connectionState)">{{ connectionLabel }}</span>
        <span class="chip chip-soft">Adapter: {{ adapterMode }}</span>
        <span class="chip chip-soft">{{ lastSyncLabel }}</span>
      </div>
    </section>

    <div class="diagnostic-grid">
      <article class="panel surface-rise detail-panel diagnostic-card">
        <div class="panel-header">
          <div>
            <p class="eyebrow">GATEWAY</p>
            <h2>Gateway / API</h2>
          </div>
          <span class="chip" :class="toneClass(connectionState)">{{ snapshot.gatewayState.toUpperCase() }}</span>
        </div>
        <div class="server-grid server-grid--compact">
          <article class="mini-stat">
            <span>Gateway 주소</span>
            <strong>{{ gatewayUrl }}</strong>
            <small>현재 접속 대상</small>
          </article>
          <article class="mini-stat">
            <span>API Health</span>
            <strong>{{ apiHealth }}</strong>
            <small>{{ statusNote }}</small>
          </article>
          <article class="mini-stat">
            <span>마지막 Snapshot</span>
            <strong>{{ snapshotTime }}</strong>
            <small>{{ lastSyncLabel }}</small>
          </article>
          <article class="mini-stat">
            <span>Adapter Mode</span>
            <strong>{{ adapterMode }}</strong>
            <small>Mock/virtual adapter 기준</small>
          </article>
        </div>
      </article>

      <article class="panel surface-rise detail-panel diagnostic-card">
        <div class="panel-header">
          <div>
            <p class="eyebrow">STREAM</p>
            <h2>WebSocket / 이벤트 버퍼</h2>
          </div>
          <span class="chip" :class="toneClass(connectionState)">{{ websocketLabel }}</span>
        </div>
        <div class="server-grid server-grid--compact">
          <article class="mini-stat">
            <span>WebSocket</span>
            <strong>{{ websocketLabel }}</strong>
            <small>{{ connectionLabel }}</small>
          </article>
          <article class="mini-stat">
            <span>Clients</span>
            <strong>{{ devicesSnapshot.gateway.websocketClients }}</strong>
            <small>gateway snapshot 기준</small>
          </article>
          <article class="mini-stat">
            <span>RTT</span>
            <strong>{{ devicesSnapshot.communication.avgRttMs }} / {{ devicesSnapshot.communication.maxRttMs }} ms</strong>
            <small>평균 / 최대</small>
          </article>
          <article class="mini-stat">
            <span>Timeout / Retry</span>
            <strong>{{ devicesSnapshot.communication.timeoutCount }} / {{ devicesSnapshot.communication.retryCount }}</strong>
            <small>간단 통신 지표</small>
          </article>
        </div>
      </article>
    </div>

    <EventLog :events="gatewayEvents" @clear="clearEvents" />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import EventLog from '../components/EventLog.vue';
import { useDashboardContext } from '../components/dashboardContext';
import type { ConnectionState, TelemetryEvent } from '../../shared/telemetry';

const {
  snapshot,
  devicesSnapshot,
  events,
  connectionState,
  gatewayUrl,
  statusNote,
  lastSyncLabel,
  websocketLabel,
  clearEvents,
} = useDashboardContext();

const gatewayEvents = computed(() =>
  events.value.filter((event) => ['gateway', 'websocket', 'fallback', 'modbus', 'mock'].includes(event.source)).slice(0, 20),
);

const adapterMode = computed(() => devicesSnapshot.value.gateway.mode === 'live' || snapshot.value.gatewayMode === 'live' ? 'LIVE' : 'MOCK');
const apiHealth = computed(() => (connectionState.value === 'offline' ? '확인 필요' : '정상'));
const snapshotTime = computed(() => formatTime(snapshot.value.timestamp));

const connectionLabel = computed(() => {
  const map: Record<ConnectionState, string> = {
    connecting: '연결 중',
    online: '실시간 연결',
    degraded: '지연 상태',
    offline: '오프라인',
    mock: '모의 모드',
  };
  return map[connectionState.value];
});

function toneClass(value: TelemetryEvent['severity'] | ConnectionState | string) {
  const normalized = String(value).toUpperCase();
  if (normalized.includes('OFFLINE') || normalized.includes('ERROR') || normalized.includes('CRITICAL')) return 'danger';
  if (normalized.includes('DEGRADED') || normalized.includes('WARN') || normalized.includes('CONNECTING')) return 'warn';
  if (normalized.includes('ONLINE') || normalized.includes('MOCK') || normalized.includes('INFO') || normalized.includes('정상')) return 'good';
  return 'neutral';
}

function formatTime(timestamp: string) {
  return new Intl.DateTimeFormat('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(timestamp));
}
</script>
