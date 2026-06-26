<template>
  <section class="panel surface-rise">
    <div class="panel-header">
      <div>
        <p class="eyebrow">장비 상태</p>
        <h2>필드버스 및 엣지 노드</h2>
      </div>
      <span class="chip chip-neutral">{{ devices.length }}개 노드</span>
    </div>

    <div class="device-grid">
      <article v-for="device in devices" :key="device.id" class="device-card" :class="stateClass(device.state)">
        <div class="device-heading">
          <strong>{{ device.label }}</strong>
          <span class="chip" :class="device.online ? 'chip-good' : 'chip-bad'">{{ device.online ? '온라인' : '오프라인' }}</span>
        </div>
        <p class="device-value">{{ device.value }}</p>
        <p class="device-detail">{{ device.detail }}</p>
        <div class="device-footer">
          <span>상태: {{ device.state }}</span>
          <span>신호: {{ device.signal }}%</span>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { DeviceStatus } from '../../shared/telemetry';

defineProps<{
  devices: DeviceStatus[];
}>();

function stateClass(state: DeviceStatus['state']) {
  if (state === 'RUNNING' || state === 'BUSY') return 'state-running';
  if (state === 'READY') return 'state-ready';
  if (state === 'WAITING' || state === 'IDLE') return 'state-waiting';
  if (state === 'WARNING') return 'state-warning';
  if (state === 'FAULT') return 'state-fault';
  return 'state-offline';
}
</script>
