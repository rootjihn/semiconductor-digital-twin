<template>
  <section class="page-grid page-grid--detail telemetry-page telemetry-page--simple">
    <section class="panel surface-rise route-summary-panel telemetry-status-rail" :class="`telemetry-status-rail--${connectionState}`">
      <div>
        <p class="eyebrow">ALERTS / LOG</p>
        <h2>알림 / 로그</h2>
        <p class="subtitle">이벤트는 독립 운영 탭이 아니라 공정·장비 화면을 보조하는 최근 WARN/ERROR 확인 영역입니다.</p>
      </div>
      <div class="telemetry-status-rail__chips">
        <span class="chip" :class="connectionToneClass">{{ connectionLabel }}</span>
        <span class="chip" :class="alertToneClass">WARN/ERROR {{ importantEvents.length }}건</span>
        <span class="chip chip-soft">{{ lastSyncLabel }}</span>
      </div>
    </section>

    <div class="alert-log-grid">
      <article class="panel surface-rise detail-panel alert-log-panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">RECENT ALERTS</p>
            <h2>최근 경고 / 오류</h2>
          </div>
          <span class="chip" :class="alertToneClass">{{ importantEvents.length }}건</span>
        </div>
        <div class="stack-list stack-list--compact">
          <article v-for="event in importantEvents" :key="event.id" class="mini-stat mini-stat--event">
            <span>{{ formatTime(event.timestamp) }} · {{ event.source }}</span>
            <strong>{{ event.message }}</strong>
            <small>{{ event.severity }}</small>
          </article>
          <article v-if="!importantEvents.length" class="mini-stat mini-stat--event">
            <span>상태</span>
            <strong>최근 경고/오류 없음</strong>
            <small>모의 adapter 기준 정상 범위</small>
          </article>
        </div>
      </article>

      <article class="panel surface-rise detail-panel alert-log-panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">GATEWAY SNAPSHOT</p>
            <h2>Gateway 수신 상태</h2>
          </div>
          <span class="chip" :class="connectionToneClass">{{ websocketLabel }}</span>
        </div>
        <div class="server-grid server-grid--compact">
          <article class="mini-stat">
            <span>Gateway</span>
            <strong>{{ snapshot.gatewayMode === 'live' ? 'LIVE' : 'MOCK' }}</strong>
            <small>{{ statusNote }}</small>
          </article>
          <article class="mini-stat">
            <span>WebSocket</span>
            <strong>{{ websocketLabel }}</strong>
            <small>{{ connectionLabel }}</small>
          </article>
          <article class="mini-stat">
            <span>현재 공정</span>
            <strong>{{ activeStageLabel }}</strong>
            <small>snapshot 기반</small>
          </article>
          <article class="mini-stat">
            <span>이벤트 버퍼</span>
            <strong>{{ events.length }}건</strong>
            <small>최근 수신 로그</small>
          </article>
        </div>
      </article>
    </div>

    <EventLog :events="recentEvents" @clear="clearEvents" />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import EventLog from '../components/EventLog.vue';
import { useDashboardContext } from '../components/dashboardContext';

const { snapshot, events, clearEvents, connectionState, lastSyncLabel, websocketLabel, statusNote } = useDashboardContext();

const recentEvents = computed(() => [...snapshot.value.alarms, ...events.value].slice(0, 30));
const importantEvents = computed(() => recentEvents.value.filter((event) => event.severity === 'WARN' || event.severity === 'ERROR' || event.severity === 'CRITICAL').slice(0, 10));

const activeStageLabel = computed(() => snapshot.value.process.stages.find((stage) => stage.id === snapshot.value.process.activeStage)?.label ?? snapshot.value.process.activeStage);

const alertToneClass = computed(() => {
  if (importantEvents.value.some((event) => event.severity === 'CRITICAL' || event.severity === 'ERROR')) return 'danger';
  if (importantEvents.value.length) return 'warn';
  return 'good';
});

const connectionToneClass = computed(() => {
  if (connectionState.value === 'online' || connectionState.value === 'mock') return 'good';
  if (connectionState.value === 'connecting' || connectionState.value === 'degraded') return 'warn';
  return 'danger';
});

const connectionLabel = computed(() => {
  const map = {
    connecting: '연결 중',
    online: '실시간 연결',
    degraded: '지연 상태',
    offline: '오프라인',
    mock: '모의 모드',
  } as const;
  return map[connectionState.value];
});

function formatTime(timestamp: string) {
  return new Intl.DateTimeFormat('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(timestamp));
}
</script>
