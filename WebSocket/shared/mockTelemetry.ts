import {
  COMMAND_LIBRARY,
  PROCESS_STAGES,
  type CommandName,
  type DashboardSnapshot,
  type DeviceStatus,
  type DeviceState,
  type LineState,
  type MetricsSeries,
  type ProcessStage,
  type ProcessStageKey,
  type TelemetryAlarm,
  type TelemetryEvent,
} from './telemetry';

export interface MockRuntime {
  seed: number;
  tick: number;
  lineState: LineState;
  activeStage: ProcessStageKey;
  faultMode: boolean;
}

export function createMockRuntime(seed = Date.now()): MockRuntime {
  const stageIndex = Math.abs(seed) % PROCESS_STAGES.length;

  return {
    seed,
    tick: 0,
    lineState: 'RUNNING',
    activeStage: PROCESS_STAGES[stageIndex]?.id ?? 'conveyor',
    faultMode: false,
  };
}

export function applyMockCommand(runtime: MockRuntime, command: CommandName): void {
  runtime.tick += 1;

  switch (command) {
    case 'process.start':
    case 'process.resume':
      runtime.lineState = 'RUNNING';
      runtime.faultMode = false;
      break;
    case 'process.pause':
      runtime.lineState = 'PAUSED';
      break;
    case 'process.stop':
      runtime.lineState = 'STOPPED';
      break;
    case 'process.reset_error':
      runtime.lineState = 'RUNNING';
      runtime.faultMode = false;
      runtime.activeStage = 'infeed';
      break;
    case 'robot.home':
    case 'system.refresh':
      break;
    default:
      break;
  }
}

export function createMockSnapshot(runtime: MockRuntime, now = Date.now()): DashboardSnapshot {
  const stageIndex = PROCESS_STAGES.findIndex((stage) => stage.id === runtime.activeStage);
  const activeStageIndex = stageIndex >= 0 ? stageIndex : 1;
  const cycleTime = computeCycleTime(runtime, activeStageIndex);
  const goodCount = 1840 + runtime.tick * 3 + activeStageIndex * 11;
  const badCount = 9 + (runtime.faultMode ? 4 : activeStageIndex === 3 ? 2 : 0);
  const outputCount = goodCount + badCount;

  return {
    timestamp: new Date(now).toISOString(),
    gatewayMode: 'mock',
    gatewayState: 'mock',
    line: {
      name: '라인 A-12',
      state: runtime.lineState,
      shift: runtime.tick % 2 === 0 ? 'Day Shift' : 'Night Shift',
      jobId: `JOB-${String(runtime.seed % 1000).padStart(3, '0')}-${String(runtime.tick).padStart(2, '0')}`,
      orderId: `ORD-${String((runtime.seed / 10) % 10000).padStart(4, '0')}`,
      cycleTimeMs: cycleTime,
      targetCycleTimeMs: 680,
      throughput: Math.max(12, Math.round(60000 / cycleTime)),
      uptimePct: runtime.lineState === 'RUNNING' ? 97.8 : runtime.lineState === 'PAUSED' ? 92.4 : 88.1,
      outputCount,
      goodCount,
      badCount,
      temperatureC: runtime.lineState === 'FAULT' ? 41.6 : 33.2 + activeStageIndex,
    },
    process: {
      activeStage: runtime.activeStage,
      stages: buildStages(runtime, cycleTime),
    },
    devices: buildDevices(runtime, cycleTime),
    metrics: buildMetrics(runtime, cycleTime, goodCount, badCount),
    alarms: buildAlarms(runtime, cycleTime),
    events: buildEvents(runtime, cycleTime, goodCount, badCount),
  };
}

export function createMockEvent(
  severity: TelemetryEvent['severity'],
  source: string,
  message: string,
  timestamp = new Date().toISOString(),
): TelemetryEvent {
  return {
    id: `evt-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    timestamp,
    severity,
    source,
    message,
  };
}

export function createCommandResult(command: CommandName, accepted: boolean, message: string): TelemetryEvent {
  return createMockEvent(accepted ? 'INFO' : 'ERROR', 'gateway', `${command}: ${message}`);
}

export function commandLabels() {
  return COMMAND_LIBRARY.map((command) => command.name);
}

function computeCycleTime(runtime: MockRuntime, activeStageIndex: number): number {
  const stageOffset = activeStageIndex * 21;
  const modeOffset =
    runtime.lineState === 'PAUSED' ? 132 : runtime.lineState === 'STOPPED' ? 188 : runtime.lineState === 'FAULT' ? 268 : 0;

  return 648 + stageOffset + modeOffset + ((runtime.seed + runtime.tick * 19) % 34);
}

function buildStages(runtime: MockRuntime, cycleTime: number): ProcessStage[] {
  return PROCESS_STAGES.map((stage, index) => {
    const state: DeviceState =
      runtime.lineState === 'FAULT'
        ? index === 3
          ? 'FAULT'
          : 'WARNING'
        : index === getActiveIndex(runtime)
          ? runtime.lineState === 'RUNNING'
            ? 'RUNNING'
            : runtime.lineState === 'PAUSED'
              ? 'READY'
              : 'WAITING'
          : index < getActiveIndex(runtime)
            ? 'READY'
            : 'WAITING';

    return {
      id: stage.id,
      label: stage.label,
      state,
      value: `${Math.max(0, Math.round((cycleTime / 20) - index * 2))} ms`,
      detail:
        index === 0
          ? '입고 감지'
          : index === 1
            ? '컨베이어 추적'
            : index === 2
              ? '비전 검사'
              : index === 3
                ? '집기/이송'
                : '배출 정렬',
      flowRate: Math.max(0, 18 - index * 2 + (runtime.lineState === 'RUNNING' ? 4 : 0)),
    };
  });
}

function buildDevices(runtime: MockRuntime, cycleTime: number): DeviceStatus[] {
  const activeIndex = getActiveIndex(runtime);
  const lineRunning = runtime.lineState === 'RUNNING';

  return [
    {
      id: 'infeed-sensor',
      label: '입고 센서',
      state: lineRunning ? 'RUNNING' : runtime.lineState === 'PAUSED' ? 'READY' : 'OFFLINE',
      online: true,
      detail: '광전 센서 감지',
      value: lineRunning ? '자재 감지' : '대기',
      signal: 95,
    },
    {
      id: 'conveyor-drive',
      label: '컨베이어 구동부',
      state: lineRunning ? 'RUNNING' : runtime.lineState === 'STOPPED' ? 'IDLE' : 'READY',
      online: true,
      detail: 'VFD 32.8 Hz',
      value: `${Math.round(32.8 + activeIndex)} Hz`,
      signal: 88,
    },
    {
      id: 'vision-camera',
      label: '비전 카메라',
      state: runtime.lineState === 'FAULT' ? 'WARNING' : lineRunning ? 'BUSY' : 'READY',
      online: true,
      detail: '프레임률 24 fps',
      value: runtime.lineState === 'RUNNING' ? '검사 중' : '대기',
      signal: 91,
    },
    {
      id: 'dobot-arm',
      label: 'Dobot 로봇',
      state: runtime.lineState === 'RUNNING' ? 'BUSY' : runtime.lineState === 'FAULT' ? 'WARNING' : 'READY',
      online: true,
      detail: '집기 구역 핸들러',
      value: runtime.lineState === 'RUNNING' ? '동작 중' : '대기',
      signal: 84,
    },
    {
      id: 'outfeed-gate',
      label: '배출 게이트',
      state: runtime.lineState === 'RUNNING' ? 'READY' : 'WAITING',
      online: true,
      detail: '불량/정상 배출 라인',
      value: cycleTime > 760 ? '적체 주의' : '원활',
      signal: 79,
    },
    {
      id: 'edge-pc',
      label: '엣지 PC',
      state: 'READY',
      online: true,
      detail: '게이트웨이 중계',
      value: '정상',
      signal: 100,
    },
  ];
}

function buildMetrics(runtime: MockRuntime, cycleTime: number, goodCount: number, badCount: number): MetricsSeries {
  const labels = Array.from({ length: 8 }, (_, index) => `${index * 5}m`);

  return {
    labels,
    cycleTimes: labels.map((_, index) => Math.max(530, cycleTime - 28 + index * 6 - runtime.tick * 3)),
    goodCounts: labels.map((_, index) => goodCount - 14 + index * 4),
    badCounts: labels.map((_, index) => Math.max(0, badCount - 3 + (index % 4))),
  };
}

function buildAlarms(runtime: MockRuntime, cycleTime: number): TelemetryAlarm[] {
  const alarms: TelemetryAlarm[] = [];

  if (runtime.lineState === 'PAUSED') {
    alarms.push({
      ...createMockEvent('WARN', 'control', '작업자 확인으로 라인 일시 정지'),
      acknowledged: false,
    });
  }

  if (runtime.lineState === 'FAULT') {
    alarms.push({
      ...createMockEvent('CRITICAL', 'safety', '집기 구역 오류 래치 감지'),
      acknowledged: false,
    });
  }

  if (cycleTime > 790) {
    alarms.push({
      ...createMockEvent('ERROR', 'vision', '사이클 목표 초과'),
      acknowledged: false,
    });
  } else {
    alarms.push({
      ...createMockEvent('INFO', 'health', '전체 셀 정상'),
      acknowledged: true,
    });
  }

  return alarms;
}

function buildEvents(runtime: MockRuntime, cycleTime: number, goodCount: number, badCount: number): TelemetryEvent[] {
  return [
    createMockEvent('INFO', 'gateway', `${runtime.tick + 1}번째 사이클 ${cycleTime} ms`),
    createMockEvent('INFO', 'production', `양품: ${goodCount}, 불량: ${badCount}`),
    createMockEvent(runtime.lineState === 'FAULT' ? 'CRITICAL' : 'INFO', 'cell', `${PROCESS_STAGES[getActiveIndex(runtime)]?.label ?? '컨베이어'} 단계 갱신`),
    createMockEvent('WARN', 'modbus', '모의 Modbus 브리지'),
  ];
}

function getActiveIndex(runtime: MockRuntime): number {
  const index = PROCESS_STAGES.findIndex((stage) => stage.id === runtime.activeStage);
  return index >= 0 ? index : 1;
}
