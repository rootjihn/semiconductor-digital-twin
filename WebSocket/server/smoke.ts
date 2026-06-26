import { setTimeout as delay } from 'node:timers/promises';
import WebSocket from 'ws';
import { startGatewayServer } from './index';
import type { DevicesSnapshot, DeviceStream } from '../shared/devices';
import type { CommandResult, DashboardSnapshot, TelemetryEvent } from '../shared/telemetry';

interface HealthPayload {
  ok: boolean;
  timestamp: string;
  devicesCount?: number;
}

interface EventsPayload {
  events?: TelemetryEvent[];
}

interface CommandPayload {
  ok?: boolean;
  result?: CommandResult;
}

async function runSmoke() {
  const handle = await startGatewayServer({
    port: 0,
    host: '127.0.0.1',
  });

  try {
    const address = handle.server.address();
    const port = typeof address === 'object' && address ? address.port : 8765;
    const baseUrl = `http://127.0.0.1:${port}`;

    const health = await fetch(`${baseUrl}/api/health`).then((response) => response.json() as Promise<HealthPayload>);
    const snapshot = await fetch(`${baseUrl}/api/snapshot`).then((response) => response.json() as Promise<DashboardSnapshot>);
    const events = await fetch(`${baseUrl}/api/events`).then((response) => response.json() as Promise<EventsPayload>);
    const devices = await fetch(`${baseUrl}/api/devices`).then((response) => response.json() as Promise<DevicesSnapshot>);
    const modbus = await fetch(`${baseUrl}/api/devices/modbus`).then(
      (response) => response.json() as Promise<{ nodes?: unknown[] }>,
    );
    const streams = await fetch(`${baseUrl}/api/devices/streams`).then(
      (response) => response.json() as Promise<{ streams?: DeviceStream[] }>,
    );
    const command = await fetch(`${baseUrl}/api/commands/process.start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ command: 'process.start' }),
    }).then((response) => response.json() as Promise<CommandPayload>);

    if (!health.ok) throw new Error('Health check failed');
    if (!snapshot.timestamp) throw new Error('Snapshot timestamp missing');
    if ((events.events?.length ?? 0) < 1) throw new Error('Events payload is empty');
    if (devices.devices.length < 6) throw new Error(`Expected at least 6 devices, got ${devices.devices.length}`);
    if (Object.keys(devices.details).length < 6) throw new Error('Device details are incomplete');
    if ((modbus.nodes?.length ?? 0) < 6) throw new Error('Modbus nodes are incomplete');
    if ((streams.streams?.length ?? 0) < 1) throw new Error('Device streams are empty');
    assertDeviceStreams(streams.streams ?? []);
    assertVirtualModels(devices);
    if (!(command.result?.accepted ?? command.ok)) throw new Error('Command smoke failed');

    const wsTypes = await new Promise<string[]>((resolve, reject) => {
      const socket = new WebSocket(`ws://127.0.0.1:${port}/ws`);
      const seen = new Set<string>();
      const requiredTypes = [
        'snapshot',
        'devices_snapshot',
        'device_update',
        'device_detail_update',
        'virtual_model_update',
        'stream_status',
        'device_event',
      ];
      const timeout = setTimeout(() => {
        socket.close();
        reject(new Error(`WebSocket devices smoke timeout: seen=${Array.from(seen).join(',')}`));
      }, 6000);

      socket.on('message', (raw) => {
        const payload = JSON.parse(String(raw)) as { type?: string };
        if (payload.type) seen.add(payload.type);
        if (requiredTypes.every((type) => seen.has(type))) {
          clearTimeout(timeout);
          socket.close();
          resolve(Array.from(seen).sort());
        }
      });
      socket.once('error', (error) => {
        clearTimeout(timeout);
        reject(error);
      });
    });

    console.log(
      JSON.stringify(
        {
          health,
          snapshot: snapshot.timestamp,
          events: events.events?.length ?? 0,
          devices: devices.devices.length,
          modbus: modbus.nodes?.length ?? 0,
          streams: streams.streams?.length ?? 0,
          command: command.result?.accepted ?? command.ok,
          wsTypes,
        },
        null,
        2,
      ),
    );
  } finally {
    await handle.close();
    await delay(100);
  }
}

function assertDeviceStreams(streams: DeviceStream[]) {
  const byId = new Map(streams.map((stream) => [stream.id, stream]));
  const requiredIds = ['dobot-model', 'realsense-yolo', 'robodk-current', 'conveyor-virtual'];
  for (const id of requiredIds) {
    if (!byId.has(id)) throw new Error(`Missing device stream: ${id}`);
  }

  for (const id of ['realsense-raw', 'turtlebot-camera']) {
    if (byId.has(id)) throw new Error(`Unexpected placeholder stream: ${id}`);
  }

  const dobot = byId.get('dobot-model');
  if (dobot?.sourceUrl !== '/media/_web/dobot_urdf_tf_h264.mp4' || dobot.playbackMode !== 'loop') {
    throw new Error('Dobot model stream does not use expected looping media');
  }

  const realsense = byId.get('realsense-yolo');
  if (realsense?.sourceUrl !== '/media/_web/realsense_yolo_h264.mp4') {
    throw new Error('RealSense YOLO stream does not use expected media');
  }

  const robodk = byId.get('robodk-current');
  if (
    robodk?.playbackMode !== 'sequence' ||
    robodk.sequenceLength !== 9 ||
    typeof robodk.sequenceIndex !== 'number' ||
    !robodk.sourceUrl?.startsWith('/media/robodk/') ||
    !robodk.nextSourceUrl?.startsWith('/media/robodk/')
  ) {
    throw new Error('RoboDK stream sequence metadata is incomplete');
  }

  const conveyor = byId.get('conveyor-virtual');
  if (conveyor?.source !== 'virtual-render' || conveyor.transport !== 'metadata-only') {
    throw new Error('Conveyor stream should be virtual metadata only');
  }
}

function assertVirtualModels(devices: DevicesSnapshot) {
  const turtlebot = devices.virtualModels.turtlebot;
  if (
    !turtlebot.map ||
    turtlebot.map.widthM <= 0 ||
    turtlebot.map.heightM <= 0 ||
    (turtlebot.stations?.length ?? 0) < 2 ||
    (turtlebot.obstacles?.length ?? 0) < 1
  ) {
    throw new Error('TurtleBot virtual map metadata is incomplete');
  }

  const conveyor = devices.virtualModels.conveyor;
  if (
    typeof conveyor.servoPositionPct !== 'number' ||
    typeof conveyor.servoAngleDeg !== 'number' ||
    typeof conveyor.leftServoAngleDeg !== 'number' ||
    typeof conveyor.rightServoAngleDeg !== 'number'
  ) {
    throw new Error('Conveyor servo metadata is incomplete');
  }
}

runSmoke().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
