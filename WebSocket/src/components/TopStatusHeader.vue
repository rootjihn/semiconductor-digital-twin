<template>
  <header class="top-header panel surface-rise">
    <div class="header-copy">
      <p class="eyebrow">Throughline 공정 관제 / 로봇 모니터링</p>
      <h1>산업용 관제실 대시보드</h1>
      <p class="subtitle">
        라인 상태와 게이트웨이 연결 요약
      </p>
    </div>

    <div class="header-actions">
      <label class="field">
        <span>게이트웨이 주소</span>
        <input :value="gatewayUrl" type="text" spellcheck="false" @input="onGatewayInput" />
      </label>

      <div class="status-row">
        <span class="chip" :class="chipClass(snapshot.gatewayState)">게이트웨이: {{ snapshot.gatewayState }}</span>
        <span class="chip" :class="chipClass(connectionState)">연결: {{ connectionState }}</span>
        <span class="chip">라인: {{ snapshot.line.state }}</span>
        <span class="chip">사이클: {{ snapshot.line.cycleTimeMs }} ms</span>
      </div>

      <div class="button-row">
        <button class="primary" type="button" @click="$emit('connect')">연결</button>
        <button class="secondary" type="button" @click="$emit('refresh')">새로고침</button>
      </div>
    </div>

    <div class="header-footer">
      <div class="mini-stat">
        <span>작업</span>
        <strong>{{ snapshot.line.jobId }}</strong>
      </div>
      <div class="mini-stat">
        <span>주문</span>
        <strong>{{ snapshot.line.orderId }}</strong>
      </div>
      <div class="mini-stat">
        <span>마지막 동기화</span>
        <strong>{{ lastSyncLabel }}</strong>
      </div>
      <div class="mini-stat wide">
        <span>상태</span>
        <strong>{{ statusNote }}</strong>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import type { ConnectionState, DashboardSnapshot } from '../../shared/telemetry';

defineProps<{
  snapshot: DashboardSnapshot;
  connectionState: ConnectionState;
  gatewayUrl: string;
  lastSyncLabel: string;
  statusNote: string;
}>();

const emit = defineEmits<{
  (event: 'update:gatewayUrl', value: string): void;
  (event: 'connect'): void;
  (event: 'refresh'): void;
}>();

function onGatewayInput(event: Event) {
  emit('update:gatewayUrl', (event.target as HTMLInputElement).value);
}

function chipClass(state: string) {
  if (state === 'online' || state === 'RUNNING') {
    return 'chip-good';
  }

  if (state === 'mock' || state === 'degraded') {
    return 'chip-warn';
  }

  if (state === 'offline') {
    return 'chip-bad';
  }

  return 'chip-neutral';
}
</script>
