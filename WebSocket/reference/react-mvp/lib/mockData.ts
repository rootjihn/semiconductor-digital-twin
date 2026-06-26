import type { DashboardSnapshot, EventItem } from './types';

export const processSteps = [
  { key: 'INPUT', label: '입고' },
  { key: 'VISION_DETECT', label: '비전 인식' },
  { key: 'ROBOT_PICK', label: '로봇 픽업' },
  { key: 'INSPECT_SORT', label: '검사/분류' },
  { key: 'OUTPUT', label: '배출' },
];

export const initialSnapshot: DashboardSnapshot = {
  timestamp: new Date().toISOString(),
  system: { mode: 'mock', state: 'RUNNING', health: 'OK' },
  process: { step: 'VISION_DETECT', job_id: 'job-mock-001', cycle_count: 12, success_count: 11, fail_count: 1 },
  robot: { state: 'READY', connected: true, pose: { x: 120, y: 30, z: 80, r: 0 }, gripper: 'OPEN' },
  vision: { state: 'DETECTED', camera_connected: true, detections: [{ label: 'target', confidence: 0.93, x: 320, y: 240, depth: 0.42 }] },
  modbus: { state: 'CONNECTED', last_update_ms: 120, signals: { conveyor_ready: true, part_detected: true } },
  alarms: [{ timestamp: new Date().toLocaleTimeString(), severity: 'WARN', source: 'vision', message: 'Mock calibration age is high' }],
};

export const initialEvents: EventItem[] = [
  { timestamp: new Date().toLocaleTimeString(), severity: 'INFO', source: 'dashboard', message: 'MVP1 mock dashboard initialized' },
];
