<template>
  <div class="telemetry-chart-grid">
    <section class="panel chart-panel surface-rise telemetry-chart-card">
      <div class="panel-header telemetry-chart-card__header">
        <div>
          <p class="eyebrow">처리량 추이</p>
          <h2>분당 처리량과 목표선</h2>
        </div>
        <span class="chip chip-soft">현재 {{ snapshot.line.throughput }}/min</span>
      </div>
      <canvas ref="throughputCanvasRef" class="metrics-canvas telemetry-chart-card__canvas" />
    </section>

    <section class="panel chart-panel surface-rise telemetry-chart-card">
      <div class="panel-header telemetry-chart-card__header">
        <div>
          <p class="eyebrow">사이클 안정성</p>
          <h2>사이클 시간과 목표 편차</h2>
        </div>
        <span class="chip" :class="snapshot.line.cycleTimeMs <= snapshot.line.targetCycleTimeMs ? 'good' : 'warn'">
          {{ snapshot.line.cycleTimeMs - snapshot.line.targetCycleTimeMs >= 0 ? '+' : '' }}{{ snapshot.line.cycleTimeMs - snapshot.line.targetCycleTimeMs }} ms
        </span>
      </div>
      <canvas ref="cycleCanvasRef" class="metrics-canvas telemetry-chart-card__canvas" />
    </section>

    <section class="panel chart-panel surface-rise telemetry-chart-card">
      <div class="panel-header telemetry-chart-card__header">
        <div>
          <p class="eyebrow">품질 / 알람</p>
          <h2>양품률과 알람 분포</h2>
        </div>
        <span class="chip" :class="qualityYield >= 99 ? 'good' : qualityYield >= 97 ? 'warn' : 'danger'">
          양품률 {{ qualityYield.toFixed(1) }}%
        </span>
      </div>
      <canvas ref="qualityCanvasRef" class="metrics-canvas telemetry-chart-card__canvas" />
    </section>
  </div>
</template>

<script setup lang="ts">
import Chart from 'chart.js/auto';
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import type { DashboardSnapshot } from '../../shared/telemetry';

const props = defineProps<{
  snapshot: DashboardSnapshot;
}>();

const throughputCanvasRef = ref<HTMLCanvasElement | null>(null);
const cycleCanvasRef = ref<HTMLCanvasElement | null>(null);
const qualityCanvasRef = ref<HTMLCanvasElement | null>(null);

let throughputChart: Chart<'line'> | null = null;
let cycleChart: Chart<'line'> | null = null;
let qualityChart: Chart<'bar' | 'line'> | null = null;

const qualityYield = computed(() => {
  const total = props.snapshot.line.outputCount;
  if (!total) return 100;
  return (props.snapshot.line.goodCount / total) * 100;
});

onMounted(() => {
  renderCharts();
});

onBeforeUnmount(() => {
  destroyCharts();
});

watch(
  () => props.snapshot,
  () => {
    renderCharts();
  },
  { deep: true },
);

function destroyCharts() {
  throughputChart?.destroy();
  cycleChart?.destroy();
  qualityChart?.destroy();
  throughputChart = null;
  cycleChart = null;
  qualityChart = null;
}

function renderCharts() {
  renderThroughputChart();
  renderCycleChart();
  renderQualityChart();
}

function renderThroughputChart() {
  const ctx = throughputCanvasRef.value?.getContext('2d');
  if (!ctx) return;

  const labels = props.snapshot.metrics.labels;
  const throughputSeries = props.snapshot.metrics.cycleTimes.map((cycleTime) => Math.max(0, Math.round(60000 / cycleTime)));
  const targetSeries = throughputSeries.map(() => Math.max(0, Math.round(60000 / props.snapshot.line.targetCycleTimeMs)));

  if (!throughputChart) {
    throughputChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: '실처리량',
            data: throughputSeries,
            tension: 0.32,
            borderColor: '#1098ad',
            backgroundColor: 'rgba(16, 152, 173, 0.14)',
            fill: true,
            pointRadius: 2,
          },
          {
            label: '목표 처리량',
            data: targetSeries,
            tension: 0,
            borderColor: '#16324f',
            borderDash: [6, 6],
            pointRadius: 0,
          },
        ],
      },
      options: baseLineOptions('units/min'),
    });
    return;
  }

  throughputChart.data.labels = labels;
  throughputChart.data.datasets[0]!.data = throughputSeries;
  throughputChart.data.datasets[1]!.data = targetSeries;
  throughputChart.update();
}

function renderCycleChart() {
  const ctx = cycleCanvasRef.value?.getContext('2d');
  if (!ctx) return;

  const labels = props.snapshot.metrics.labels;
  const targetSeries = props.snapshot.metrics.labels.map(() => props.snapshot.line.targetCycleTimeMs);

  if (!cycleChart) {
    cycleChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: '사이클 시간',
            data: props.snapshot.metrics.cycleTimes,
            tension: 0.35,
            borderColor: '#0f6f8f',
            backgroundColor: 'rgba(15, 111, 143, 0.16)',
            fill: true,
            pointRadius: 3,
          },
          {
            label: '목표',
            data: targetSeries,
            tension: 0,
            borderColor: '#c7831c',
            borderDash: [7, 5],
            pointRadius: 0,
          },
        ],
      },
      options: baseLineOptions('ms'),
    });
    return;
  }

  cycleChart.data.labels = labels;
  cycleChart.data.datasets[0]!.data = props.snapshot.metrics.cycleTimes;
  cycleChart.data.datasets[1]!.data = targetSeries;
  cycleChart.update();
}

function renderQualityChart() {
  const ctx = qualityCanvasRef.value?.getContext('2d');
  if (!ctx) return;

  const labels = props.snapshot.metrics.labels;
  const qualitySeries = props.snapshot.metrics.goodCounts.map((goodCount, index) => {
    const badCount = props.snapshot.metrics.badCounts[index] ?? 0;
    const total = goodCount + badCount;
    return total > 0 ? Number(((goodCount / total) * 100).toFixed(1)) : 0;
  });

  const alarmCounts = severityBuckets(props.snapshot);

  if (!qualityChart) {
    qualityChart = new Chart(ctx, {
      data: {
        labels,
        datasets: [
          {
            type: 'line',
            label: '양품률',
            data: qualitySeries,
            yAxisID: 'yQuality',
            tension: 0.28,
            borderColor: '#1aa987',
            backgroundColor: 'rgba(26, 169, 135, 0.16)',
            fill: true,
            pointRadius: 2,
          },
          {
            type: 'bar',
            label: '알람 강도',
            data: labels.map((_, index) => alarmCounts[index % alarmCounts.length] ?? 0),
            yAxisID: 'yAlarm',
            backgroundColor: labels.map((_, index) => severityColor(index % alarmCounts.length)),
            borderRadius: 8,
            maxBarThickness: 22,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            labels: {
              color: '#3c4a5d',
            },
          },
        },
        scales: {
          x: {
            ticks: { color: '#667085' },
            grid: { color: 'rgba(87, 103, 117, 0.08)' },
          },
          yQuality: {
            type: 'linear',
            min: 95,
            max: 100,
            position: 'left',
            ticks: {
              color: '#667085',
              callback: (value) => `${value}%`,
            },
            grid: { color: 'rgba(87, 103, 117, 0.1)' },
          },
          yAlarm: {
            type: 'linear',
            position: 'right',
            beginAtZero: true,
            ticks: { color: '#667085', stepSize: 1 },
            grid: { drawOnChartArea: false },
          },
        },
      },
    });
    return;
  }

  qualityChart.data.labels = labels;
  qualityChart.data.datasets[0]!.data = qualitySeries;
  qualityChart.data.datasets[1]!.data = labels.map((_, index) => alarmCounts[index % alarmCounts.length] ?? 0);
  qualityChart.update();
}

function severityBuckets(snapshot: DashboardSnapshot) {
  const source = snapshot.alarms;
  const info = source.filter((alarm) => alarm.severity === 'INFO').length;
  const warn = source.filter((alarm) => alarm.severity === 'WARN').length;
  const error = source.filter((alarm) => alarm.severity === 'ERROR').length;
  const critical = source.filter((alarm) => alarm.severity === 'CRITICAL').length;
  return [info, warn, error, critical];
}

function severityColor(index: number) {
  return ['rgba(22, 147, 111, 0.45)', 'rgba(199, 131, 28, 0.45)', 'rgba(200, 77, 66, 0.45)', 'rgba(120, 56, 180, 0.45)'][index] ?? 'rgba(100, 116, 139, 0.35)';
}

function baseLineOptions(unit: string) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        labels: {
          color: '#3c4a5d',
        },
      },
    },
    scales: {
      x: {
        ticks: {
          color: '#667085',
        },
        grid: {
          color: 'rgba(87, 103, 117, 0.08)',
        },
      },
      y: {
        ticks: {
          color: '#667085',
          callback: (value: string | number) => `${value} ${unit}`,
        },
        grid: {
          color: 'rgba(87, 103, 117, 0.1)',
        },
      },
    },
  };
}
</script>
