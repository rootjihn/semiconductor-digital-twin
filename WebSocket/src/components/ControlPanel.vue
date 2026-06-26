<template>
  <section class="panel surface-rise">
    <div class="panel-header">
      <div>
        <p class="eyebrow">제어 패널</p>
        <h2>운전 명령</h2>
      </div>
      <span class="chip" :class="chipClass(connectionState)">{{ connectionState }}</span>
    </div>

    <div class="command-grid">
      <button
        v-for="command in commands"
        :key="command.name"
        type="button"
        class="command-button"
        :class="{ danger: command.danger, active: busyCommand === command.name }"
        :disabled="busyCommand === command.name"
        @click="$emit('command', command.name)"
      >
        <strong>{{ command.label }}</strong>
        <span>{{ command.description }}</span>
      </button>
    </div>

    <p class="hint">
      게이트웨이 명령 전송 / 모의 모드 지원
    </p>
  </section>
</template>

<script setup lang="ts">
import { COMMAND_LIBRARY, type CommandName, type ConnectionState, type DashboardSnapshot } from '../../shared/telemetry';

defineProps<{
  snapshot: DashboardSnapshot;
  connectionState: ConnectionState;
  busyCommand: CommandName | null;
}>();

defineEmits<{
  (event: 'command', command: CommandName): void;
}>();

const commands = COMMAND_LIBRARY;

function chipClass(state: ConnectionState) {
  if (state === 'online') return 'chip-good';
  if (state === 'mock') return 'chip-warn';
  if (state === 'degraded') return 'chip-neutral';
  return 'chip-bad';
}
</script>
