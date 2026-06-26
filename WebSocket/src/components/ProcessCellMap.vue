<template>
  <section class="panel cell-panel surface-rise">
    <div class="panel-header">
      <div>
        <p class="eyebrow">공정 셀 지도</p>
        <h2>입고 → 컨베이어 → 비전 → Dobot → 배출</h2>
      </div>
      <span class="chip chip-neutral">활성 단계: {{ snapshot.process.activeStage }}</span>
    </div>

    <svg viewBox="0 0 980 320" class="cell-svg" role="img" aria-label="공정 셀 흐름도">
      <defs>
        <linearGradient id="cellLine" x1="0%" x2="100%">
          <stop offset="0%" stop-color="#2dd4bf" />
          <stop offset="100%" stop-color="#38bdf8" />
        </linearGradient>
        <linearGradient id="cellGlow" x1="0%" x2="100%">
          <stop offset="0%" stop-color="rgba(56, 189, 248, 0.1)" />
          <stop offset="100%" stop-color="rgba(45, 212, 191, 0.1)" />
        </linearGradient>
      </defs>

      <rect x="18" y="18" width="944" height="284" rx="28" class="cell-backplate" />

      <line v-for="connector in connectors" :key="connector.id" :x1="connector.x1" :y1="connector.y1" :x2="connector.x2" :y2="connector.y2" class="cell-link" :class="{ active: connector.active }" />

      <g v-for="node in nodes" :key="node.id" class="cell-node" :class="node.stateClass">
        <rect :x="node.x" :y="node.y" :width="node.width" :height="node.height" rx="24" class="node-card" />
        <circle :cx="node.dotX" :cy="node.dotY" r="10" class="node-dot" />
        <text :x="node.x + 20" :y="node.y + 30" class="node-label">{{ node.label }}</text>
        <text :x="node.x + 20" :y="node.y + 54" class="node-detail">{{ node.detail }}</text>
        <text :x="node.x + 20" :y="node.y + 80" class="node-value">{{ node.value }}</text>
        <text :x="node.x + 20" :y="node.y + 104" class="node-state">{{ node.state }}</text>
      </g>

      <g class="cell-overlay">
        <text x="48" y="270" class="overlay-label">라인 상태</text>
        <text x="156" y="270" class="overlay-value">{{ snapshot.line.state }}</text>
        <text x="48" y="294" class="overlay-label">가동률</text>
        <text x="156" y="294" class="overlay-value">{{ snapshot.line.uptimePct.toFixed(1) }}%</text>
        <text x="328" y="270" class="overlay-label">처리량</text>
        <text x="468" y="270" class="overlay-value">{{ snapshot.line.throughput }} ppm</text>
        <text x="328" y="294" class="overlay-label">온도</text>
        <text x="468" y="294" class="overlay-value">{{ snapshot.line.temperatureC.toFixed(1) }} °C</text>
      </g>
    </svg>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { DashboardSnapshot, DeviceState } from '../../shared/telemetry';

const props = defineProps<{
  snapshot: DashboardSnapshot;
}>();

const nodes = computed(() =>
  props.snapshot.process.stages.map((stage, index) => {
    const x = 52 + index * 176;
    const y = index % 2 === 0 ? 52 : 164;

    return {
      id: stage.id,
      label: stage.label,
      detail: stage.detail,
      value: stage.value,
      state: stage.state,
      stateClass: stateClass(stage.state),
      x,
      y,
      width: 150,
      height: 112,
      dotX: x + 130,
      dotY: y + 20,
    };
  }),
);

const connectors = computed(() =>
  nodes.value.slice(0, -1).map((node, index) => {
    const next = nodes.value[index + 1];
    return {
      id: `${node.id}-${next.id}`,
      x1: node.x + node.width,
      y1: node.y + node.height / 2,
      x2: next.x,
      y2: next.y + next.height / 2,
      active: node.id === props.snapshot.process.activeStage || next.id === props.snapshot.process.activeStage,
    };
  }),
);

function stateClass(state: DeviceState) {
  if (state === 'RUNNING' || state === 'BUSY') return 'state-running';
  if (state === 'READY') return 'state-ready';
  if (state === 'WAITING' || state === 'IDLE') return 'state-waiting';
  if (state === 'WARNING') return 'state-warning';
  if (state === 'FAULT') return 'state-fault';
  return 'state-offline';
}
</script>
