<template>
  <svg class="server-sparkline" viewBox="0 0 120 36" preserveAspectRatio="none" aria-hidden="true">
    <defs>
      <linearGradient :id="gradientId" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" :stop-color="fillTopColor" />
        <stop offset="100%" :stop-color="fillBottomColor" />
      </linearGradient>
    </defs>
    <path :d="areaPath" :fill="`url(#${gradientId})`" />
    <polyline :points="polylinePoints" fill="none" :stroke="strokeColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  values: number[];
  tone?: 'good' | 'warn' | 'danger' | 'neutral';
}>();

const tone = computed(() => props.tone ?? 'neutral');
const gradientId = computed(() => `spark-${tone.value}-${Math.random().toString(36).slice(2, 8)}`);

const normalizedValues = computed(() => (props.values.length ? props.values : [0, 0]));

const polylinePoints = computed(() => {
  const values = normalizedValues.value;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = Math.max(max - min, 1);
  return values
    .map((value, index) => {
      const x = values.length === 1 ? 60 : (index / (values.length - 1)) * 120;
      const y = 30 - ((value - min) / range) * 24;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(' ');
});

const areaPath = computed(() => {
  const points = polylinePoints.value.split(' ');
  const first = points[0] ?? '0,30';
  const last = points[points.length - 1] ?? '120,30';
  return `M ${first} L ${points.join(' L ')} L ${last.split(',')[0]},34 L ${first.split(',')[0]},34 Z`;
});

const strokeColor = computed(() => {
  if (tone.value === 'good') return '#15936f';
  if (tone.value === 'warn') return '#c7831c';
  if (tone.value === 'danger') return '#c84d42';
  return '#64748b';
});

const fillTopColor = computed(() => {
  if (tone.value === 'good') return 'rgba(21, 147, 111, 0.28)';
  if (tone.value === 'warn') return 'rgba(199, 131, 28, 0.24)';
  if (tone.value === 'danger') return 'rgba(200, 77, 66, 0.24)';
  return 'rgba(100, 116, 139, 0.22)';
});

const fillBottomColor = computed(() => 'rgba(255,255,255,0)');
</script>
