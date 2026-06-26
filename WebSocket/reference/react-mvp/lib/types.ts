export type Severity = 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL';
export type WebSocketState = 'MOCK' | 'CONNECTING' | 'CONNECTED' | 'ERROR';

export interface Detection {
  label: string;
  confidence: number;
  x: number;
  y: number;
  depth: number;
}

export interface DashboardSnapshot {
  type?: 'state_snapshot';
  timestamp: string;
  system: { mode: string; state: string; health: string };
  process: { step: string; job_id: string; cycle_count: number; success_count: number; fail_count: number };
  robot: { state: string; connected: boolean; pose: { x: number; y: number; z: number; r: number }; gripper: string };
  vision: { state: string; camera_connected: boolean; detections: Detection[] };
  modbus: { state: string; last_update_ms: number; signals: { conveyor_ready: boolean; part_detected: boolean } };
  alarms: EventItem[];
}

export interface EventItem {
  timestamp: string;
  severity: Severity;
  source: string;
  message: string;
}

export interface CommandPayload {
  type: 'command';
  request_id: string;
  command: string;
  payload: Record<string, unknown>;
}

export type GatewayMessage =
  | (DashboardSnapshot & { type: 'state_snapshot' })
  | ({ type: 'event' } & EventItem)
  | { type: 'command_result'; request_id: string; command?: string; status: string; message?: string };
