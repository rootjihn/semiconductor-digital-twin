import type { DevicesGatewayMessage } from './devices';

export type Severity = 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL';
export type ConnectionState = 'mock' | 'connecting' | 'online' | 'degraded' | 'offline';
export type LineState = 'RUNNING' | 'PAUSED' | 'STOPPED' | 'FAULT';
export type DeviceState = 'READY' | 'RUNNING' | 'BUSY' | 'WAITING' | 'WARNING' | 'FAULT' | 'OFFLINE' | 'IDLE';

export const PROCESS_STAGES = [
  { id: 'infeed', label: '입고 센서' },
  { id: 'conveyor', label: '컨베이어' },
  { id: 'vision', label: '비전 카메라' },
  { id: 'pick', label: 'Dobot 로봇' },
  { id: 'outfeed', label: '배출부' },
] as const;

export type ProcessStageKey = (typeof PROCESS_STAGES)[number]['id'];

export const COMMAND_LIBRARY = [
  { name: 'process.start', label: '공정 시작', description: '라인 가동', danger: false },
  { name: 'process.pause', label: '일시 정지', description: '상태 유지', danger: false },
  { name: 'process.resume', label: '재개', description: '공정 재개', danger: false },
  { name: 'process.stop', label: '공정 정지', description: '라인 정지', danger: true },
  { name: 'process.reset_error', label: '오류 초기화', description: '알람 복구', danger: true },
  { name: 'robot.home', label: '로봇 홈 복귀', description: '기준 위치 이동', danger: false },
  { name: 'system.refresh', label: '상태 새로고침', description: '스냅샷 요청', danger: false },
] as const;

export type CommandName = (typeof COMMAND_LIBRARY)[number]['name'];

export interface TelemetryEvent {
  id: string;
  timestamp: string;
  severity: Severity;
  source: string;
  message: string;
}

export interface TelemetryAlarm extends TelemetryEvent {
  acknowledged: boolean;
}

export interface DeviceStatus {
  id: string;
  label: string;
  state: DeviceState;
  online: boolean;
  detail: string;
  value: string;
  signal: number;
}

export interface ProcessStage {
  id: ProcessStageKey;
  label: string;
  state: DeviceState;
  value: string;
  detail: string;
  flowRate: number;
}

export interface MetricsSeries {
  labels: string[];
  cycleTimes: number[];
  goodCounts: number[];
  badCounts: number[];
}

export interface DashboardSnapshot {
  timestamp: string;
  gatewayMode: 'mock' | 'live';
  gatewayState: ConnectionState;
  line: {
    name: string;
    state: LineState;
    shift: string;
    jobId: string;
    orderId: string;
    cycleTimeMs: number;
    targetCycleTimeMs: number;
    throughput: number;
    uptimePct: number;
    outputCount: number;
    goodCount: number;
    badCount: number;
    temperatureC: number;
  };
  process: {
    activeStage: ProcessStageKey;
    stages: ProcessStage[];
  };
  devices: DeviceStatus[];
  metrics: MetricsSeries;
  alarms: TelemetryAlarm[];
  events: TelemetryEvent[];
}

export interface CommandResult {
  requestId: string;
  command: CommandName;
  accepted: boolean;
  message: string;
  timestamp: string;
}

export type GatewayMessage =
  | { type: 'snapshot'; snapshot: DashboardSnapshot }
  | { type: 'event'; event: TelemetryEvent }
  | { type: 'command_result'; result: CommandResult }
  | DevicesGatewayMessage;
