export type DeviceId = 'dobot' | 'turtlebot' | 'realsense' | 'conveyor' | 'robodk' | 'gateway';

export type DeviceRole = 'Manipulator' | 'MobileRobot' | 'VisionCamera' | 'Conveyor' | 'Simulation' | 'Gateway';

export type DeviceOperatingState =
  | 'READY'
  | 'RUNNING'
  | 'BUSY'
  | 'WAITING'
  | 'WARNING'
  | 'FAULT'
  | 'OFFLINE'
  | 'STREAMING'
  | 'MOVING'
  | 'STOPPED'
  | 'IDLE';

export type DeviceConnectionState = 'ONLINE' | 'DEGRADED' | 'OFFLINE';
export type DeviceEventSeverity = 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL';

export interface DeviceMetric {
  label: string;
  value: string | number;
  unit?: string;
  tone?: 'good' | 'warn' | 'danger' | 'neutral';
}

export interface DeviceEvent {
  id: string;
  timestamp: string;
  severity: DeviceEventSeverity;
  source: DeviceId | 'modbus' | 'scenario' | 'stream';
  deviceId?: DeviceId;
  message: string;
}

export interface DeviceNode {
  id: DeviceId;
  name: string;
  role: DeviceRole;
  ip?: string;
  state: DeviceOperatingState;
  statusText: string;
  online: boolean;
  connection: DeviceConnectionState;
  lastUpdated: string;
  rttMs: number;
  retryCount: number;
  timeoutCount: number;
  primaryStreamId?: string;
}

export interface DeviceStream {
  id: string;
  deviceId: DeviceId;
  label: string;
  kind: 'camera' | 'yolo' | 'modeling' | 'simulation';
  source: 'recorded-file' | 'virtual-render' | 'mock';
  transport: 'static-file' | 'websocket-frame' | 'hls' | 'mjpeg' | 'metadata-only';
  status: 'LIVE' | 'PAUSED' | 'ENDED' | 'ERROR';
  sourceUrl?: string;
  fps?: number;
  width?: number;
  height?: number;
  currentFrameTs: string;
  playbackMs?: number;
  loop?: boolean;
  sequenceIndex?: number;
  sequenceLength?: number;
  nextSourceUrl?: string;
  playbackMode?: 'loop' | 'sequence';
}

export interface ModbusNodeStatus {
  deviceId: DeviceId;
  unitId: number;
  connected: boolean;
  lastPollAt: string;
  rttMs: number;
  retryCount: number;
  timeoutCount: number;
  registers: Record<string, number | boolean>;
}

export interface TurtleBotMapState {
  kind: 'turtlebot-map';
  deviceId: 'turtlebot';
  mapId: 'cell-a';
  pose: {
    x: number;
    y: number;
    thetaDeg: number;
  };
  map?: {
    widthM: number;
    heightM: number;
    resolutionM: number;
    origin: {
      x: number;
      y: number;
    };
  };
  stations?: Array<{
    id: string;
    label: string;
    x: number;
    y: number;
  }>;
  obstacles?: Array<{
    id: string;
    x: number;
    y: number;
    widthM: number;
    heightM: number;
  }>;
  target?: {
    x: number;
    y: number;
    label: string;
  };
  path: Array<{
    x: number;
    y: number;
  }>;
  batteryPct: number;
  motionState: 'IDLE' | 'MOVING' | 'ARRIVED' | 'BLOCKED';
}

export interface ConveyorModelState {
  kind: 'conveyor-model';
  deviceId: 'conveyor';
  running: boolean;
  speedPct: number;
  direction: 'FORWARD' | 'REVERSE';
  servoPositionPct?: number;
  servoDirection?: 'LEFT' | 'RIGHT' | 'CENTER';
  servoAngleDeg?: number;
  leftServoAngleDeg?: number;
  rightServoAngleDeg?: number;
  boxes: Array<{
    id: string;
    positionPct: number;
    detected: boolean;
  }>;
  sensors: Array<{
    id: string;
    label: string;
    active: boolean;
    positionPct: number;
  }>;
  fault?: 'JAM' | 'MOTOR_ERROR' | 'SENSOR_ERROR';
}

export type VirtualModelState = TurtleBotMapState | ConveyorModelState;

export interface DeviceDetail {
  id: DeviceId;
  title: string;
  state: DeviceOperatingState;
  statusText: string;
  modbus?: ModbusNodeStatus;
  streams: DeviceStream[];
  virtualModel?: VirtualModelState;
  metrics: DeviceMetric[];
  recentEvents: DeviceEvent[];
}

export interface DevicesSnapshot {
  timestamp: string;
  gateway: {
    mode: 'mock' | 'live';
    state: DeviceConnectionState;
    websocketClients: number;
    modbusConfigured: boolean;
  };
  summary: {
    normal: number;
    running: number;
    waiting: number;
    warning: number;
    fault: number;
    offline: number;
  };
  communication: {
    avgRttMs: number;
    maxRttMs: number;
    timeoutCount: number;
    retryCount: number;
    nodes: Array<{
      deviceId: DeviceId;
      rttMs: number;
      online: boolean;
    }>;
  };
  devices: DeviceNode[];
  details: Record<DeviceId, DeviceDetail>;
  virtualModels: {
    turtlebot: TurtleBotMapState;
    conveyor: ConveyorModelState;
  };
  streams: DeviceStream[];
  modbus: {
    nodes: ModbusNodeStatus[];
  };
  events: DeviceEvent[];
}

export type DevicesGatewayMessage =
  | { type: 'devices_snapshot'; snapshot: DevicesSnapshot }
  | { type: 'device_update'; device: DeviceNode }
  | { type: 'device_detail_update'; detail: DeviceDetail }
  | { type: 'virtual_model_update'; model: VirtualModelState }
  | { type: 'stream_status'; stream: DeviceStream }
  | { type: 'device_event'; event: DeviceEvent };

export function createFallbackDevicesSnapshot(now = new Date().toISOString()): DevicesSnapshot {
  const devices: DeviceNode[] = [
    { id: 'dobot', name: 'Dobot Magician', role: 'Manipulator', ip: '192.168.1.21', state: 'BUSY', statusText: 'PICKING', online: true, connection: 'ONLINE', lastUpdated: now, rttMs: 3, retryCount: 0, timeoutCount: 0, primaryStreamId: 'dobot-model' },
    { id: 'turtlebot', name: 'TurtleBot3 Waffle Pi', role: 'MobileRobot', ip: '192.168.1.22', state: 'MOVING', statusText: '지도 위치 갱신', online: true, connection: 'ONLINE', lastUpdated: now, rttMs: 8, retryCount: 1, timeoutCount: 0 },
    { id: 'realsense', name: 'RealSense / Vision', role: 'VisionCamera', ip: '192.168.1.23', state: 'STREAMING', statusText: 'YOLO stream', online: true, connection: 'ONLINE', lastUpdated: now, rttMs: 7, retryCount: 0, timeoutCount: 0, primaryStreamId: 'realsense-yolo' },
    { id: 'conveyor', name: 'Conveyor Belt / Raspberry Pi 5', role: 'Conveyor', ip: '192.168.1.24', state: 'RUNNING', statusText: 'RUNNING', online: true, connection: 'ONLINE', lastUpdated: now, rttMs: 4, retryCount: 0, timeoutCount: 0 },
    { id: 'robodk', name: 'RoboDK Simulation', role: 'Simulation', ip: '192.168.1.25', state: 'IDLE', statusText: 'IDLE', online: true, connection: 'ONLINE', lastUpdated: now, rttMs: 9, retryCount: 0, timeoutCount: 0, primaryStreamId: 'robodk-simulation' },
    { id: 'gateway', name: 'Gateway / Server', role: 'Gateway', ip: '192.168.1.10', state: 'READY', statusText: 'READY', online: true, connection: 'ONLINE', lastUpdated: now, rttMs: 2, retryCount: 0, timeoutCount: 0 },
  ];
  const turtlebot: TurtleBotMapState = {
    kind: 'turtlebot-map', deviceId: 'turtlebot', mapId: 'cell-a',
    pose: { x: 4.2, y: 2.4, thetaDeg: 42 },
    map: { widthM: 8, heightM: 4.5, resolutionM: 0.05, origin: { x: 0, y: 0 } },
    stations: [{ id: 's1', label: 'PICK', x: 1.2, y: 3.4 }, { id: 's2', label: 'PLACE', x: 6.8, y: 1.1 }],
    obstacles: [{ id: 'obs-a', x: 3.2, y: 1.9, widthM: 0.8, heightM: 0.5 }],
    target: { x: 6.8, y: 1.1, label: 'PLACE' },
    path: [{ x: 1.1, y: 3.3 }, { x: 2.4, y: 2.8 }, { x: 3.6, y: 2.4 }, { x: 4.2, y: 2.4 }],
    batteryPct: 82,
    motionState: 'MOVING',
  };
  const conveyor: ConveyorModelState = {
    kind: 'conveyor-model', deviceId: 'conveyor', running: true, speedPct: 62, direction: 'FORWARD', servoPositionPct: 54, servoDirection: 'CENTER', servoAngleDeg: 4, leftServoAngleDeg: -8, rightServoAngleDeg: 9,
    boxes: [{ id: 'box-a', positionPct: 34, detected: true }, { id: 'box-b', positionPct: 71, detected: false }],
    sensors: [{ id: 'in', label: 'IN', active: true, positionPct: 18 }, { id: 'mid', label: 'MID', active: true, positionPct: 50 }, { id: 'out', label: 'OUT', active: false, positionPct: 84 }],
  };
  const streams: DeviceStream[] = [
    { id: 'realsense-yolo', deviceId: 'realsense', label: 'YOLO 인식 영상', kind: 'yolo', source: 'recorded-file', transport: 'static-file', status: 'LIVE', sourceUrl: '/media/_web/realsense_yolo_h264.mp4', fps: 11, width: 1280, height: 720, currentFrameTs: now, playbackMs: 0, loop: true, playbackMode: 'loop' },
    { id: 'dobot-model', deviceId: 'dobot', label: 'Dobot 모델링 영상', kind: 'modeling', source: 'recorded-file', transport: 'static-file', status: 'LIVE', sourceUrl: '/media/_web/dobot_urdf_tf_h264.mp4', fps: 30, width: 1280, height: 720, currentFrameTs: now, playbackMs: 0, loop: true, playbackMode: 'loop' },
    { id: 'robodk-simulation', deviceId: 'robodk', label: 'RoboDK 시퀀스', kind: 'simulation', source: 'recorded-file', transport: 'static-file', status: 'LIVE', sourceUrl: '/media/robodk/1.디자인 아이디어 구현(24.12.19).mp4', fps: 30, width: 1280, height: 720, currentFrameTs: now, playbackMs: 0, sequenceIndex: 0, sequenceLength: 7, nextSourceUrl: '/media/robodk/2.최초공정구현(25.02.15).mp4', playbackMode: 'sequence' },
  ];
  const details = Object.fromEntries(devices.map((device) => [device.id, {
    id: device.id,
    title: device.name,
    state: device.state,
    statusText: device.statusText,
    streams: streams.filter((stream) => stream.deviceId === device.id),
    virtualModel: device.id === 'turtlebot' ? turtlebot : device.id === 'conveyor' ? conveyor : undefined,
    metrics: [
      { label: 'RTT', value: device.rttMs, unit: 'ms', tone: 'good' },
      { label: 'Timeout', value: device.timeoutCount, tone: device.timeoutCount ? 'warn' : 'good' },
      { label: 'Retry', value: device.retryCount, tone: device.retryCount ? 'warn' : 'good' },
    ],
    recentEvents: [],
  }])) as unknown as Record<DeviceId, DeviceDetail>;
  return {
    timestamp: now,
    gateway: { mode: 'mock', state: 'ONLINE', websocketClients: 0, modbusConfigured: false },
    summary: { normal: 4, running: 2, waiting: 1, warning: 0, fault: 0, offline: 0 },
    communication: { avgRttMs: 6, maxRttMs: 12, timeoutCount: 0, retryCount: 1, nodes: devices.map((device) => ({ deviceId: device.id, rttMs: device.rttMs, online: device.online })) },
    devices,
    details,
    virtualModels: { turtlebot, conveyor },
    streams,
    modbus: { nodes: [] },
    events: [
      { id: 'evt-dobot-busy', timestamp: now, severity: 'INFO', source: 'dobot', deviceId: 'dobot', message: 'Dobot 상태 READY → BUSY' },
      { id: 'evt-realsense-stream', timestamp: now, severity: 'INFO', source: 'realsense', deviceId: 'realsense', message: 'YOLO stream started' },
      { id: 'evt-conveyor-run', timestamp: now, severity: 'INFO', source: 'conveyor', deviceId: 'conveyor', message: 'Conveyor RUNNING' },
    ],
  };
}
