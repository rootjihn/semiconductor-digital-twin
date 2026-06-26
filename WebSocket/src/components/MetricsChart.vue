<template>
  <section class="panel chart-panel surface-rise">
    <div class="panel-header">
      <div>
        <p class="eyebrow">관제 추이</p>
        <h2>사이클 시간 및 생산 추이</h2>
      </div>
      <span class="chip chip-neutral">{{ snapshot.line.cycleTimeMs }} ms</span>
    </div>

    <canvas ref="canvasRef" class="metrics-canvas" />
  </section>
</template>

<script setup lang="ts">
import Chart from 'chart.js/auto';
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import type { DashboardSnapshot } from '../../shared/telemetry';

const props = defineProps<{
  snapshot: DashboardSnapshot;
}>();

const canvasRef = ref<HTMLCanvasElement | null>(null);
let chart: Chart<'line'> | null = null;

onMounted(() => {
  renderChart();
});

onBeforeUnmount(() => {
  chart?.destroy();
  chart = null;
});

watch(
  () => props.snapshot.metrics,
  () => {
    renderChart();
  },
  { deep: true },
);

function renderChart() {
  if (!canvasRef.value) {
    return;
  }

  const ctx = canvasRef.value.getContext('2d');
  if (!ctx) {
    return;
  }

  const data = props.snapshot.metrics;

  if (!chart) {
    chart = new Chart(ctx, {
      type: 'line',
        data: {
          labels: data.labels,
          datasets: [
            {
              label: '사이클 시간',
              data: data.cycleTimes,
              tension: 0.35,
              borderColor: '#0f6f8f',
              backgroundColor: 'rgba(15, 111, 143, 0.16)',
              fill: true,
              yAxisID: 'yCycle',
              pointRadius: 3,
            },
            {
              label: '양품 수',
              data: data.goodCounts,
              tension: 0.32,
              borderColor: '#1f8c7a',
              backgroundColor: 'rgba(31, 140, 122, 0.12)',
              fill: false,
              yAxisID: 'yCount',
              pointRadius: 2,
            },
            {
              label: '불량 수',
              data: data.badCounts,
              tension: 0.32,
              borderColor: '#c65d38',
              backgroundColor: 'rgba(198, 93, 56, 0.12)',
              fill: false,
              yAxisID: 'yCount',
              pointRadius: 2,
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
            ticks: {
              color: '#667085',
            },
            grid: {
              color: 'rgba(87, 103, 117, 0.08)',
            },
          },
          yCycle: {
            type: 'linear',
            position: 'left',
            ticks: {
              color: '#667085',
            },
            grid: {
              color: 'rgba(87, 103, 117, 0.1)',
            },
          },
          yCount: {
            type: 'linear',
            position: 'right',
            ticks: {
              color: '#667085',
            },
            grid: {
              drawOnChartArea: false,
            },
          },
        },
      },
    });
    return;
  }

  chart.data.labels = data.labels;
  chart.data.datasets[0].data = data.cycleTimes;
  chart.data.datasets[1].data = data.goodCounts;
  chart.data.datasets[2].data = data.badCounts;
  chart.update();
}
</script>
