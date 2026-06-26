<template>
  <section class="page-grid process-page--demo">
    <section class="panel surface-rise route-summary-panel process-hero">
      <div>
        <p class="eyebrow">PROCESS</p>
        <h2>공정 흐름</h2>
        <p class="subtitle">시연에서 “현재 후공정 라인이 어느 단계인지”만 빠르게 보여주는 핵심 화면입니다.</p>
      </div>
      <div class="banner-meta">
        <span class="chip" :class="lineToneClass">{{ lineStateLabel(snapshot.line.state) }}</span>
        <span class="chip chip-soft">현재 단계: {{ activeStage?.label ?? snapshot.process.activeStage }}</span>
        <span class="chip chip-soft">{{ lastSyncLabel }}</span>
      </div>
    </section>

    <section class="process-layout-grid">
      <article class="panel surface-rise process-flow-panel">
        <div class="panel-header">
          <div>
            <p class="eyebrow">6 STEP FLOW</p>
            <h2>후공정 6단계 흐름</h2>
          </div>
          <span class="chip chip-neutral">{{ completedCount }} / {{ processSteps.length }} 진행</span>
        </div>

        <div class="process-line-canvas" aria-label="공정 라인 시각화">
          <div class="process-line-canvas__track" aria-hidden="true"></div>
          <article
            v-for="(stage, index) in processSteps"
            :key="`line-${stage.id}`"
            class="process-line-node"
            :class="[`process-line-node--${stage.tone}`, { active: stage.id === snapshot.process.activeStage, done: index < activeStageIndex }]"
          >
            <span class="process-line-node__dot">{{ index + 1 }}</span>
            <strong>{{ stage.label }}</strong>
            <small>{{ stage.status }}</small>
          </article>
        </div>

        <div class="process-step-grid">
          <article
            v-for="(stage, index) in processSteps"
            :key="stage.id"
            class="process-step-card"
            :class="[`process-step-card--${stage.tone}`, { active: stage.id === snapshot.process.activeStage, done: index < activeStageIndex }]"
          >
            <span class="process-step-card__index">{{ index + 1 }}</span>
            <div>
              <strong>{{ stage.label }}</strong>
              <p>{{ stage.detail }}</p>
            </div>
            <span class="chip" :class="stage.tone">{{ stage.status }}</span>
          </article>
        </div>
      </article>

      <aside class="process-side-stack">
        <article class="panel surface-rise detail-panel process-focus-card">
          <div class="panel-header">
            <div>
              <p class="eyebrow">CURRENT</p>
              <h2>현재 공정 단계</h2>
            </div>
            <span class="chip" :class="toneClass(activeStage?.state ?? 'READY')">{{ activeStage?.state ?? 'READY' }}</span>
          </div>
          <div class="server-grid server-grid--compact">
            <article class="mini-stat">
              <span>단계</span>
              <strong>{{ activeStage?.label ?? snapshot.process.activeStage }}</strong>
              <small>{{ activeStage?.value ?? '상태 갱신 대기' }}</small>
            </article>
            <article class="mini-stat">
              <span>담당 장비</span>
              <strong>{{ activeDeviceLabel }}</strong>
              <small>게이트웨이 상태 기준</small>
            </article>
            <article class="mini-stat">
              <span>시연 데이터</span>
              <strong>기록 영상 + 가상 모델</strong>
              <small>실제 카메라 영상은 제외</small>
            </article>
            <article class="mini-stat">
              <span>다음 동작</span>
              <strong>{{ nextStageLabel }}</strong>
              <small>단계 전환 대기</small>
            </article>
          </div>
        </article>

        <article class="panel surface-rise detail-panel process-log-card">
          <div class="panel-header">
            <div>
              <p class="eyebrow">RECENT LOG</p>
              <h2>최근 로그 5개</h2>
            </div>
            <span class="chip" :class="alertTone">{{ recentLogs.length }}건</span>
          </div>
          <div class="stack-list stack-list--compact">
            <article v-for="event in recentLogs" :key="event.id" class="mini-stat mini-stat--event">
              <span>{{ formatTime(event.timestamp) }} · {{ event.source }}</span>
              <strong>{{ event.message }}</strong>
              <small>{{ event.severity }}</small>
            </article>
          </div>
        </article>
      </aside>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useDashboardContext } from '../components/dashboardContext';
import type { DashboardSnapshot, DeviceState, LineState, ProcessStage } from '../../shared/telemetry';

const { snapshot, events, lastSyncLabel } = useDashboardContext();

type Tone = 'good' | 'warn' | 'danger' | 'neutral';

type ProcessStepView = {
  id: string;
  label: string;
  detail: string;
  status: string;
  state: DeviceState;
  tone: Tone;
};

const activeStageIndex = computed(() => {
  const index = snapshot.value.process.stages.findIndex((stage) => stage.id === snapshot.value.process.activeStage);
  return index >= 0 ? index : 0;
});

const activeStage = computed(() => snapshot.value.process.stages.find((stage) => stage.id === snapshot.value.process.activeStage));
const completedCount = computed(() => Math.min(activeStageIndex.value + 1, processSteps.value.length));
const recentLogs = computed(() => [...snapshot.value.alarms, ...events.value].slice(0, 5));
const nextStageLabel = computed(() => processSteps.value[Math.min(activeStageIndex.value + 1, processSteps.value.length - 1)]?.label ?? '완료 상태 유지');

const processSteps = computed<ProcessStepView[]>(() => {
  const base = snapshot.value.process.stages.map((stage, index) => toStepView(stage, index));
  const finalStep: ProcessStepView = {
    id: 'complete',
    label: '완료 / 배출 확인',
    detail: '공정 결과와 배출 상태를 요약합니다.',
    status: activeStageIndex.value >= base.length ? '진행 중' : '대기',
    state: activeStageIndex.value >= base.length ? 'RUNNING' : 'WAITING',
    tone: activeStageIndex.value >= base.length ? 'good' : 'neutral',
  };
  return [...base, finalStep].slice(0, 6);
});

const activeDeviceLabel = computed(() => {
  const map: Record<string, string> = {
    infeed: 'Conveyor / Sensor',
    conveyor: 'Conveyor Pi / Modbus',
    vision: 'RealSense / Vision',
    pick: 'Dobot / ROS',
    outfeed: 'Conveyor / 배출부',
    complete: 'Gateway',
  };
  return map[snapshot.value.process.activeStage] ?? 'Gateway';
});

const alertTone = computed<Tone>(() => {
  if (recentLogs.value.some((event) => event.severity === 'ERROR' || event.severity === 'CRITICAL')) return 'danger';
  if (recentLogs.value.some((event) => event.severity === 'WARN')) return 'warn';
  return 'good';
});

const lineToneClass = computed(() => toneClass(snapshot.value.line.state));

function toStepView(stage: ProcessStage, index: number): ProcessStepView {
  const isActive = stage.id === snapshot.value.process.activeStage;
  const isDone = index < activeStageIndex.value;
  return {
    id: stage.id,
    label: stage.label,
    detail: stage.detail,
    status: isDone ? '완료' : isActive ? '진행 중' : stage.state === 'FAULT' ? '오류' : '대기',
    state: stage.state,
    tone: isDone || isActive ? toneClass(stage.state) : 'neutral',
  };
}

function toneClass(value: DeviceState | LineState | string): Tone {
  const normalized = String(value).toUpperCase();
  if (normalized.includes('FAULT') || normalized.includes('ERROR') || normalized.includes('OFFLINE')) return 'danger';
  if (normalized.includes('WARN') || normalized.includes('WAITING') || normalized.includes('PAUSED') || normalized.includes('STOPPED')) return 'warn';
  if (normalized.includes('READY') || normalized.includes('RUNNING') || normalized.includes('BUSY')) return 'good';
  return 'neutral';
}

function lineStateLabel(state: DashboardSnapshot['line']['state']) {
  const map: Record<DashboardSnapshot['line']['state'], string> = {
    RUNNING: '가동',
    PAUSED: '일시 정지',
    STOPPED: '정지',
    FAULT: '장애',
  };
  return map[state];
}

function formatTime(timestamp: string) {
  return new Intl.DateTimeFormat('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(timestamp));
}
</script>
