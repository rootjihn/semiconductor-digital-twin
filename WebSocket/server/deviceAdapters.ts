import type {
  ConveyorModelState,
  DeviceConnectionState,
  DeviceDetail,
  DeviceEvent,
  DeviceId,
  DeviceMetric,
  DeviceNode,
  DeviceOperatingState,
  DeviceRole,
  DevicesSnapshot,
  DeviceStream,
  ModbusNodeStatus,
  TurtleBotMapState,
} from '../shared/devices';

interface DeviceDefinition {
  id: DeviceId;
  unitId: number;
  name: string;
  role: DeviceRole;
  ip: string;
}

export interface DeviceRuntime {
  seed: number;
  tick: number;
  scenarioStep: number;
  recentEvents: DeviceEvent[];
}

interface SnapshotOptions {
  websocketClients: number;
  modbusConfigured: boolean;
  mode?: 'mock' | 'live';
}

const DEVICE_DEFINITIONS: DeviceDefinition[] = [
  { id: 'dobot', unitId: 1, name: 'Dobot Magician', role: 'Manipulator', ip: '192.168.1.21' },
  { id: 'turtlebot', unitId: 2, name: 'TurtleBot3 Waffle Pi', role: 'MobileRobot', ip: '192.168.1.31' },
  { id: 'realsense', unitId: 3, name: 'RealSense / Vision', role: 'VisionCamera', ip: '192.168.1.41' },
  { id: 'conveyor', unitId: 4, name: 'Conveyor Belt', role: 'Conveyor', ip: '192.168.1.51' },
  { id: 'robodk', unitId: 5, name: 'RoboDK Simulation', role: 'Simulation', ip: '192.168.1.61' },
  { id: 'gateway', unitId: 10, name: 'Gateway Server', role: 'Gateway', ip: '127.0.0.1' },
];

const STATE_SEQUENCE: DeviceOperatingState[] = ['READY', 'RUNNING', 'BUSY', 'WAITING', 'RUNNING', 'READY'];
const DEVICE_LABELS: Record<DeviceId, string> = {
  dobot: 'Dobot',
  turtlebot: 'TurtleBot',
  realsense: 'RealSense',
  conveyor: 'Conveyor',
  robodk: 'RoboDK',
  gateway: 'Gateway',
};
const ROBODK_SEQUENCE_URLS = [
  '/media/robodk/1단계_웨이퍼생성.mp4',
  '/media/robodk/2단계_웨이퍼이동(공정컨베이어로이동).mp4',
  '/media/robodk/3단계_웨이퍼to다이변환.mp4',
  '/media/robodk/4단계_다이트레이.mp4',
  '/media/robodk/5단계_본딩처리.mp4',
  '/media/robodk/6-1단계_AGV올리기.mp4',
  '/media/robodk/6-2단계_AGV올리기.mp4',
  '/media/robodk/6-3단계_AGV올리기.mp4',
  '/media/robodk/7단계_AGV이송.mp4',
];

export class MockModbusAdapter {
  poll(runtime: DeviceRuntime, now: string, websocketClients: number): ModbusNodeStatus[] {
    return DEVICE_DEFINITIONS.map((definition, index) => {
      const baseRtt = 3 + ((runtime.tick + index * 2) % 9);
      const timeoutCount = runtime.tick > 0 && runtime.tick % 30 === 0 && definition.id === 'robodk' ? 1 : 0;
      const retryCount = definition.id === 'gateway' ? 0 : (runtime.tick + index) % 7 === 0 ? 1 : 0;
      return {
        deviceId: definition.id,
        unitId: definition.unitId,
        connected: timeoutCount === 0,
        lastPollAt: now,
        rttMs: baseRtt + timeoutCount * 15,
        retryCount,
        timeoutCount,
        registers: buildRegisters(definition.id, runtime, websocketClients),
      };
    });
  }
}

export class RecordedVideoAdapter {
  snapshot(runtime: DeviceRuntime, now: string): DeviceStream[] {
    return buildStreams(runtime, now);
  }
}

export class VirtualModelAdapter {
  turtlebot(runtime: DeviceRuntime): TurtleBotMapState {
    return buildTurtleBotModel(runtime);
  }

  conveyor(runtime: DeviceRuntime): ConveyorModelState {
    return buildConveyorModel(runtime);
  }
}

export class DeviceScenarioAdapter {
  advance(runtime: DeviceRuntime): DeviceEvent {
    return advanceDeviceRuntime(runtime);
  }

  snapshot(runtime: DeviceRuntime, options: SnapshotOptions): DevicesSnapshot {
    return createDevicesSnapshot(runtime, options);
  }
}

const mockModbusAdapter = new MockModbusAdapter();
const recordedVideoAdapter = new RecordedVideoAdapter();
const virtualModelAdapter = new VirtualModelAdapter();

export function createDeviceRuntime(seed = Date.now()): DeviceRuntime {
  return {
    seed,
    tick: 0,
    scenarioStep: 0,
    recentEvents: [],
  };
}

export function advanceDeviceRuntime(runtime: DeviceRuntime): DeviceEvent {
  runtime.tick += 1;
  runtime.scenarioStep = runtime.tick % 6;
  const event = createDeviceEvent('INFO', scenarioSource(runtime.scenarioStep), scenarioMessage(runtime.scenarioStep));
  runtime.recentEvents = [event, ...runtime.recentEvents].slice(0, 80);
  return event;
}

export function createDevicesSnapshot(runtime: DeviceRuntime, options: SnapshotOptions): DevicesSnapshot {
  const now = new Date().toISOString();
  const modbusNodes = mockModbusAdapter.poll(runtime, now, options.websocketClients);
  const streams = recordedVideoAdapter.snapshot(runtime, now);
  const turtlebotModel = virtualModelAdapter.turtlebot(runtime);
  const conveyorModel = virtualModelAdapter.conveyor(runtime);
  const devices = DEVICE_DEFINITIONS.map((definition) => buildDeviceNode(definition, runtime, now, modbusNodes, streams));
  const summary = summarizeDevices(devices);
  const communication = summarizeCommunication(modbusNodes);
  const generatedEvents = buildSnapshotEvents(runtime, now, devices);
  const events = [...runtime.recentEvents, ...generatedEvents].slice(0, 100);
  const details = Object.fromEntries(
    devices.map((device) => [
      device.id,
      buildDeviceDetail(device, modbusNodes, streams, turtlebotModel, conveyorModel, events),
    ]),
  ) as Record<DeviceId, DeviceDetail>;

  return {
    timestamp: now,
    gateway: {
      mode: options.mode ?? 'mock',
      state: options.modbusConfigured ? 'ONLINE' : 'ONLINE',
      websocketClients: options.websocketClients,
      modbusConfigured: options.modbusConfigured,
    },
    summary,
    communication,
    devices,
    details,
    virtualModels: {
      turtlebot: turtlebotModel,
      conveyor: conveyorModel,
    },
    streams,
    modbus: {
      nodes: modbusNodes,
    },
    events,
  };
}

export function createDeviceEvent(
  severity: DeviceEvent['severity'],
  source: DeviceEvent['source'],
  message: string,
  deviceId?: DeviceId,
  timestamp = new Date().toISOString(),
): DeviceEvent {
  return {
    id: `dev-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    timestamp,
    severity,
    source,
    deviceId,
    message,
  };
}

function buildRegisters(deviceId: DeviceId, runtime: DeviceRuntime, websocketClients: number): Record<string, number | boolean> {
  const heartbeat = runtime.seed % 1000 + runtime.tick;
  const stateCode = runtime.scenarioStep;

  switch (deviceId) {
    case 'dobot':
      return {
        statusCode: stateCode,
        jointMoving: runtime.scenarioStep === 2 || runtime.scenarioStep === 4,
        gripperClosed: runtime.scenarioStep >= 2 && runtime.scenarioStep <= 3,
        errorCode: 0,
        heartbeat,
      };
    case 'turtlebot':
      return {
        statusCode: runtime.scenarioStep === 3 ? 1 : 3,
        poseXmm: Math.round(turtleX(runtime) * 1000),
        poseYmm: Math.round(turtleY(runtime) * 1000),
        thetaDeg: turtleTheta(runtime),
        batteryPct: Math.max(45, 92 - (runtime.tick % 48)),
        heartbeat,
      };
    case 'realsense':
      return {
        yoloLive: true,
        detectedCount: 1 + (runtime.tick % 4),
        fps: 24 + (runtime.tick % 3),
        confidencePct: 84 + (runtime.tick % 9),
        heartbeat,
      };
    case 'conveyor':
      {
        const servo = conveyorServo(runtime);
        return {
          running: runtime.scenarioStep !== 3,
          directionForward: conveyorDirection(runtime) === 'FORWARD',
          speedPct: conveyorSpeed(runtime),
          sensorIn: runtime.tick % 4 < 2,
          sensorMid: runtime.tick % 3 === 0,
          sensorOut: runtime.tick % 5 === 0,
          servoPositionPct: servo.positionPct,
          leftServoAngleDeg: servo.leftAngleDeg,
          rightServoAngleDeg: servo.rightAngleDeg,
          jam: false,
          heartbeat,
        };
      }
    case 'robodk':
      return {
        simState: runtime.scenarioStep,
        currentSequence: robodkSequenceIndex(runtime),
        sequenceLength: ROBODK_SEQUENCE_URLS.length,
        robotMoving: runtime.scenarioStep === 2 || runtime.scenarioStep === 4,
        errorCode: 0,
        heartbeat,
      };
    case 'gateway':
      return {
        websocketClients,
        adapterAlive: true,
        scenarioStep: runtime.scenarioStep,
        heartbeat,
      };
  }
}

function buildStreams(runtime: DeviceRuntime, now: string): DeviceStream[] {
  const playbackMs = runtime.tick * 2500;
  const robodkIndex = robodkSequenceIndex(runtime);
  const robodkNextIndex = (robodkIndex + 1) % ROBODK_SEQUENCE_URLS.length;
  return [
    stream('realsense-yolo', 'realsense', 'YOLO 인식', 'yolo', '/media/_web/realsense_yolo_h264.mp4', now, playbackMs, 11, {
      loop: true,
      playbackMode: 'loop',
    }),
    stream('dobot-model', 'dobot', 'Dobot 모델링', 'modeling', '/media/_web/dobot_urdf_tf_h264.mp4', now, playbackMs, 30, {
      loop: true,
      playbackMode: 'loop',
    }),
    stream('robodk-current', 'robodk', `RoboDK 공정 ${robodkIndex + 1}/${ROBODK_SEQUENCE_URLS.length}`, 'simulation', ROBODK_SEQUENCE_URLS[robodkIndex], now, playbackMs, 30, {
      loop: false,
      sequenceIndex: robodkIndex,
      sequenceLength: ROBODK_SEQUENCE_URLS.length,
      nextSourceUrl: ROBODK_SEQUENCE_URLS[robodkNextIndex],
      playbackMode: 'sequence',
    }),
    {
      id: 'conveyor-virtual',
      deviceId: 'conveyor',
      label: '컨베이어 가상 모델',
      kind: 'simulation',
      source: 'virtual-render',
      transport: 'metadata-only',
      status: 'LIVE',
      currentFrameTs: now,
      fps: 30,
      width: 960,
      height: 540,
      playbackMs,
    },
  ];
}

function stream(
  id: string,
  deviceId: DeviceId,
  label: string,
  kind: DeviceStream['kind'],
  sourceUrl: string,
  now: string,
  playbackMs: number,
  fps: number,
  options: Partial<Pick<DeviceStream, 'loop' | 'sequenceIndex' | 'sequenceLength' | 'nextSourceUrl' | 'playbackMode'>> = {},
): DeviceStream {
  const streamOptions = {
    ...options,
    nextSourceUrl: options.nextSourceUrl ? encodeMediaUrl(options.nextSourceUrl) : undefined,
  };

  return {
    id,
    deviceId,
    label,
    kind,
    source: 'recorded-file',
    transport: 'static-file',
    status: 'LIVE',
    sourceUrl: encodeMediaUrl(sourceUrl),
    currentFrameTs: now,
    fps,
    width: 1280,
    height: 720,
    playbackMs,
    ...streamOptions,
  };
}

function encodeMediaUrl(url: string): string {
  return url
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');
}

function buildTurtleBotModel(runtime: DeviceRuntime): TurtleBotMapState {
  const pose = {
    x: Number(turtleX(runtime).toFixed(2)),
    y: Number(turtleY(runtime).toFixed(2)),
    thetaDeg: turtleTheta(runtime),
  };
  const path = Array.from({ length: 8 }, (_, index) => {
    const tempRuntime = { ...runtime, tick: Math.max(0, runtime.tick - (7 - index)) };
    return {
      x: Number(turtleX(tempRuntime).toFixed(2)),
      y: Number(turtleY(tempRuntime).toFixed(2)),
    };
  });

  return {
    kind: 'turtlebot-map',
    deviceId: 'turtlebot',
    mapId: 'cell-a',
    pose,
    map: {
      widthM: 5.4,
      heightM: 3.2,
      resolutionM: 0.05,
      origin: { x: 0, y: 0 },
    },
    stations: [
      { id: 'home', label: 'Home', x: 1.1, y: 1.2 },
      { id: 'station-a', label: 'Station A', x: 2.6, y: 1.0 },
      { id: 'station-b', label: 'Station B', x: 4.2, y: 2.2 },
    ],
    obstacles: [
      { id: 'safety-fence', x: 0.2, y: 0.2, widthM: 0.2, heightM: 2.8 },
      { id: 'process-cell', x: 2.8, y: 1.6, widthM: 0.8, heightM: 0.7 },
      { id: 'charging-dock', x: 0.8, y: 0.8, widthM: 0.5, heightM: 0.4 },
    ],
    target: runtime.scenarioStep < 3 ? { x: 4.2, y: 2.2, label: 'Station B' } : { x: 1.1, y: 1.2, label: 'Home' },
    path,
    batteryPct: Math.max(45, 92 - (runtime.tick % 48)),
    motionState: runtime.scenarioStep === 3 ? 'ARRIVED' : 'MOVING',
  };
}

function buildConveyorModel(runtime: DeviceRuntime): ConveyorModelState {
  const running = runtime.scenarioStep !== 3;
  const servo = conveyorServo(runtime);
  return {
    kind: 'conveyor-model',
    deviceId: 'conveyor',
    running,
    speedPct: conveyorSpeed(runtime),
    direction: conveyorDirection(runtime),
    servoPositionPct: servo.positionPct,
    servoDirection: servo.direction,
    servoAngleDeg: servo.angleDeg,
    leftServoAngleDeg: servo.leftAngleDeg,
    rightServoAngleDeg: servo.rightAngleDeg,
    boxes: Array.from({ length: 3 }, (_, index) => ({
      id: `box-${index + 1}`,
      positionPct: running ? (runtime.tick * 13 + index * 31) % 100 : (index + 1) * 24,
      detected: (runtime.tick + index) % 3 === 0,
    })),
    sensors: [
      { id: 'in', label: 'IN', active: runtime.tick % 4 < 2, positionPct: 12 },
      { id: 'mid', label: 'MID', active: runtime.tick % 3 === 0, positionPct: 50 },
      { id: 'out', label: 'OUT', active: runtime.tick % 5 === 0, positionPct: 88 },
    ],
  };
}

function buildDeviceNode(
  definition: DeviceDefinition,
  runtime: DeviceRuntime,
  now: string,
  modbusNodes: ModbusNodeStatus[],
  streams: DeviceStream[],
): DeviceNode {
  const modbus = modbusNodes.find((node) => node.deviceId === definition.id);
  const state = deviceState(definition.id, runtime);
  const connection = connectionFromModbus(modbus);
  return {
    id: definition.id,
    name: definition.name,
    role: definition.role,
    ip: definition.ip,
    state,
    statusText: statusText(definition.id, state),
    online: connection !== 'OFFLINE',
    connection,
    lastUpdated: now,
    rttMs: modbus?.rttMs ?? 0,
    retryCount: modbus?.retryCount ?? 0,
    timeoutCount: modbus?.timeoutCount ?? 0,
    primaryStreamId: streams.find((item) => item.deviceId === definition.id)?.id,
  };
}

function buildDeviceDetail(
  device: DeviceNode,
  modbusNodes: ModbusNodeStatus[],
  streams: DeviceStream[],
  turtlebotModel: TurtleBotMapState,
  conveyorModel: ConveyorModelState,
  events: DeviceEvent[],
): DeviceDetail {
  const modbus = modbusNodes.find((node) => node.deviceId === device.id);
  const deviceStreams = streams.filter((item) => item.deviceId === device.id);
  return {
    id: device.id,
    title: device.name,
    state: device.state,
    statusText: device.statusText,
    modbus,
    streams: deviceStreams,
    virtualModel: device.id === 'turtlebot' ? turtlebotModel : device.id === 'conveyor' ? conveyorModel : undefined,
    metrics: buildMetrics(device, modbus),
    recentEvents: events.filter((event) => !event.deviceId || event.deviceId === device.id || event.source === device.id).slice(0, 5),
  };
}

function buildMetrics(device: DeviceNode, modbus?: ModbusNodeStatus): DeviceMetric[] {
  const metrics: DeviceMetric[] = [
    { label: '상태', value: device.statusText, tone: device.connection === 'ONLINE' ? 'good' : 'warn' },
    { label: 'RTT', value: device.rttMs, unit: 'ms', tone: device.rttMs > 18 ? 'warn' : 'good' },
    { label: 'Retry', value: device.retryCount, tone: device.retryCount ? 'warn' : 'good' },
  ];

  if (device.id === 'realsense') {
    metrics.push({ label: 'FPS', value: modbus?.registers.fps as number, tone: 'good' });
    metrics.push({ label: '감지 객체', value: modbus?.registers.detectedCount as number, tone: 'neutral' });
  }
  if (device.id === 'turtlebot') {
    metrics.push({ label: '배터리', value: modbus?.registers.batteryPct as number, unit: '%', tone: 'good' });
  }
  if (device.id === 'conveyor') {
    metrics.push({ label: '속도', value: modbus?.registers.speedPct as number, unit: '%', tone: 'good' });
    metrics.push({ label: '서보 각도', value: modbus?.registers.leftServoAngleDeg as number, unit: 'deg', tone: 'neutral' });
  }
  return metrics;
}

function summarizeDevices(devices: DeviceNode[]): DevicesSnapshot['summary'] {
  const count = (...states: DeviceOperatingState[]) => devices.filter((device) => states.includes(device.state)).length;
  return {
    normal: count('READY', 'IDLE'),
    running: count('RUNNING', 'BUSY', 'STREAMING', 'MOVING'),
    waiting: count('WAITING', 'STOPPED'),
    warning: count('WARNING'),
    fault: count('FAULT'),
    offline: devices.filter((device) => !device.online || device.state === 'OFFLINE').length,
  };
}

function summarizeCommunication(nodes: ModbusNodeStatus[]): DevicesSnapshot['communication'] {
  const rtts = nodes.map((node) => node.rttMs);
  return {
    avgRttMs: Math.round(rtts.reduce((sum, item) => sum + item, 0) / Math.max(1, rtts.length)),
    maxRttMs: Math.max(...rtts),
    timeoutCount: nodes.reduce((sum, node) => sum + node.timeoutCount, 0),
    retryCount: nodes.reduce((sum, node) => sum + node.retryCount, 0),
    nodes: nodes.map((node) => ({ deviceId: node.deviceId, rttMs: node.rttMs, online: node.connected })),
  };
}

function buildSnapshotEvents(runtime: DeviceRuntime, now: string, devices: DeviceNode[]): DeviceEvent[] {
  const active = devices[runtime.scenarioStep % devices.length];
  return [
    createDeviceEvent('INFO', active?.id ?? 'scenario', `${active?.name ?? '장비'} 상태 ${active?.statusText ?? '갱신'}`, active?.id, now),
    createDeviceEvent('INFO', 'modbus', '가상 Modbus register poll 완료', undefined, now),
    createDeviceEvent('INFO', 'stream', '녹화 기반 영상 stream metadata 갱신', undefined, now),
  ];
}

function deviceState(deviceId: DeviceId, runtime: DeviceRuntime): DeviceOperatingState {
  if (deviceId === 'gateway') return 'READY';
  if (deviceId === 'realsense') return 'STREAMING';
  if (deviceId === 'turtlebot') return runtime.scenarioStep === 3 ? 'READY' : 'MOVING';
  if (deviceId === 'conveyor') return runtime.scenarioStep === 3 ? 'STOPPED' : 'RUNNING';
  if (deviceId === 'dobot') return runtime.scenarioStep === 2 || runtime.scenarioStep === 4 ? 'BUSY' : 'READY';
  if (deviceId === 'robodk') return runtime.scenarioStep === 2 || runtime.scenarioStep === 4 ? 'RUNNING' : 'READY';
  return STATE_SEQUENCE[runtime.scenarioStep] ?? 'READY';
}

function statusText(deviceId: DeviceId, state: DeviceOperatingState): string {
  if (deviceId === 'realsense') return 'YOLO 데모 영상 재생';
  if (deviceId === 'turtlebot') return state === 'MOVING' ? '지도 위치 이동 중' : '목표 지점 대기';
  if (deviceId === 'conveyor') return state === 'RUNNING' ? '벨트 가상 구동 중' : '벨트 정지';
  if (deviceId === 'dobot') return state === 'BUSY' ? '집기 시퀀스 동작' : '홈 위치 대기';
  if (deviceId === 'robodk') return state === 'RUNNING' ? '동작 시뮬레이션 재생' : '시뮬레이션 대기';
  return 'Gateway adapter 정상';
}

function connectionFromModbus(node?: ModbusNodeStatus): DeviceConnectionState {
  if (!node?.connected) return 'OFFLINE';
  if (node.timeoutCount || node.retryCount > 1 || node.rttMs > 20) return 'DEGRADED';
  return 'ONLINE';
}

function scenarioSource(step: number): DeviceId | 'scenario' {
  const order: Array<DeviceId | 'scenario'> = ['gateway', 'conveyor', 'realsense', 'turtlebot', 'dobot', 'robodk'];
  return order[step % order.length] ?? 'scenario';
}

function scenarioMessage(step: number): string {
  const messages = [
    'Gateway 장비 snapshot 동기화',
    'Conveyor 가상 박스 이동 갱신',
    'RealSense YOLO stream metadata 갱신',
    'TurtleBot 지도 위치 갱신',
    'Dobot 집기 시퀀스 상태 갱신',
    'RoboDK 동작 영상 상태 갱신',
  ];
  return messages[step % messages.length] ?? '장비 상태 갱신';
}

function turtleX(runtime: Pick<DeviceRuntime, 'tick' | 'seed'>): number {
  return 1.1 + ((runtime.tick * 0.18 + (runtime.seed % 7) * 0.03) % 3.2);
}

function turtleY(runtime: Pick<DeviceRuntime, 'tick' | 'seed'>): number {
  return 1.0 + Math.abs(Math.sin((runtime.tick + runtime.seed % 10) / 4)) * 1.6;
}

function turtleTheta(runtime: Pick<DeviceRuntime, 'tick'>): number {
  return (runtime.tick * 18) % 360;
}

function conveyorSpeed(runtime: DeviceRuntime): number {
  return runtime.scenarioStep === 3 ? 0 : 55 + ((runtime.tick * 7) % 30);
}

function conveyorDirection(runtime: DeviceRuntime): ConveyorModelState['direction'] {
  return runtime.scenarioStep === 5 ? 'REVERSE' : 'FORWARD';
}

function conveyorServo(runtime: DeviceRuntime): {
  positionPct: number;
  direction: ConveyorModelState['servoDirection'];
  angleDeg: number;
  leftAngleDeg: number;
  rightAngleDeg: number;
} {
  const phase = runtime.tick % 20;
  const positionPct = phase <= 10 ? phase * 10 : (20 - phase) * 10;
  const direction = positionPct < 45 ? 'LEFT' : positionPct > 55 ? 'RIGHT' : 'CENTER';
  const angleDeg = Math.round(-45 + positionPct * 0.9);
  return {
    positionPct,
    direction,
    angleDeg,
    leftAngleDeg: angleDeg,
    rightAngleDeg: -angleDeg,
  };
}

function robodkSequenceIndex(runtime: DeviceRuntime): number {
  return runtime.tick % ROBODK_SEQUENCE_URLS.length;
}

export function deviceDefinitions(): DeviceDefinition[] {
  return DEVICE_DEFINITIONS.map((definition) => ({ ...definition }));
}

export function deviceLabel(deviceId: DeviceId): string {
  return DEVICE_LABELS[deviceId];
}
