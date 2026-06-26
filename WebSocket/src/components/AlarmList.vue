<template>
  <section class="panel surface-rise">
    <div class="panel-header">
      <div>
        <p class="eyebrow">Alarms</p>
        <h2>Active alarms and exceptions</h2>
      </div>
      <span class="chip chip-neutral">{{ alarms.length }}</span>
    </div>

    <div class="alarm-stack">
      <article v-for="alarm in alarms" :key="alarm.id" class="alarm-card" :class="alarmClass(alarm.severity)">
        <div class="alarm-heading">
          <strong>{{ alarm.source }}</strong>
          <span class="alarm-time">{{ formatTime(alarm.timestamp) }}</span>
        </div>
        <p>{{ alarm.message }}</p>
        <div class="alarm-footer">
          <span class="chip" :class="severityChip(alarm.severity)">{{ alarm.severity }}</span>
          <span class="alarm-ack">{{ alarm.acknowledged ? 'acknowledged' : 'unacked' }}</span>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { TelemetryAlarm } from '../../shared/telemetry';

defineProps<{
  alarms: TelemetryAlarm[];
}>();

function alarmClass(severity: TelemetryAlarm['severity']) {
  if (severity === 'CRITICAL') return 'alarm-critical';
  if (severity === 'ERROR') return 'alarm-error';
  if (severity === 'WARN') return 'alarm-warn';
  return 'alarm-info';
}

function severityChip(severity: TelemetryAlarm['severity']) {
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
