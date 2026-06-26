<template>
  <section class="panel event-panel surface-rise">
    <div class="panel-header">
      <div>
        <p class="eyebrow">이벤트 로그</p>
        <h2>실시간 메시지 흐름</h2>
      </div>
      <button class="secondary small" type="button" @click="$emit('clear')">로그 비우기</button>
    </div>

    <div class="event-table">
      <div v-for="event in events" :key="event.id" class="event-row">
        <span class="event-time">{{ formatTime(event.timestamp) }}</span>
        <span class="chip" :class="severityChip(event.severity)">{{ event.severity }}</span>
        <span class="event-source">{{ event.source }}</span>
        <span class="event-message">{{ event.message }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { TelemetryEvent } from '../../shared/telemetry';

defineProps<{
  events: TelemetryEvent[];
}>();

defineEmits<{
  (event: 'clear'): void;
}>();

function severityChip(severity: TelemetryEvent['severity']) {
  if (severity === 'CRITICAL') return 'chip-bad';
  if (severity === 'ERROR') return 'chip-warn';
  if (severity === 'WARN') return 'chip-neutral';
  return 'chip-good';
}

function formatTime(timestamp: string) {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}
</script>
