import express from 'express';
import http from 'node:http';
import { resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { WebSocket, WebSocketServer } from 'ws';
import { advanceDeviceRuntime, createDeviceRuntime, createDevicesSnapshot } from './deviceAdapters';
import { applyMockCommand, createCommandResult, createMockEvent, createMockRuntime, createMockSnapshot } from '../shared/mockTelemetry';
import type { DeviceId, DeviceEvent, DevicesSnapshot } from '../shared/devices';
import type { CommandName, CommandResult, DashboardSnapshot, GatewayMessage, TelemetryEvent } from '../shared/telemetry';
import { ModbusTcpClient } from './tcpClient';

export interface GatewayServerHandle {
  server: http.Server;
  wss: WebSocketServer;
  close: () => Promise<void>;
  state: GatewayRuntimeState;
}

interface GatewayRuntimeState {
  runtime: ReturnType<typeof createMockRuntime>;
  snapshot: DashboardSnapshot;
  events: TelemetryEvent[];
  devicesRuntime: ReturnType<typeof createDeviceRuntime>;
  devicesSnapshot: DevicesSnapshot;
  deviceEvents: DeviceEvent[];
  commandCounter: number;
}

const DEFAULT_PORT = Number(process.env.PORT ?? process.env.GATEWAY_PORT ?? 8765);
const DEFAULT_HOST = process.env.HOST ?? '0.0.0.0';
const PROJECT_ROOT = fileURLToPath(new URL('..', import.meta.url));
const MEDIA_ROOT = resolve(process.env.RECORD_DATA_DIR ?? process.env.MEDIA_ROOT_DIR ?? resolve(PROJECT_ROOT, '..', 'record_data'));

export async function startGatewayServer(options: { port?: number; host?: string } = {}): Promise<GatewayServerHandle> {
  const app = express();
  const initialRuntime = createMockRuntime();
  const initialDevicesRuntime = createDeviceRuntime();
  const modbusClient = createModbusSkeleton();
  const state: GatewayRuntimeState = {
    runtime: initialRuntime,
    snapshot: createSnapshot(initialRuntime),
    events: [],
    devicesRuntime: initialDevicesRuntime,
    devicesSnapshot: createDevicesSnapshot(initialDevicesRuntime, {
      websocketClients: 0,
      modbusConfigured: Boolean(modbusClient),
      mode: 'mock',
    }),
    deviceEvents: [],
    commandCounter: 0,
  };

  state.events = state.snapshot.events;
  state.deviceEvents = state.devicesSnapshot.events;

  app.use(express.json({ limit: '64kb' }));
  app.use(setCorsHeaders);
  app.use('/media', express.static(MEDIA_ROOT, { dotfiles: 'ignore', index: false }));

  app.get('/api/health', (_request, response) => {
    response.json({
      ok: true,
      timestamp: new Date().toISOString(),
      mode: state.snapshot.gatewayMode,
      websocketClients: wss.clients.size,
      modbusConfigured: Boolean(modbusClient),
      devicesTimestamp: state.devicesSnapshot.timestamp,
      devicesCount: state.devicesSnapshot.devices.length,
    });
  });

  app.get('/api/snapshot', (_request, response) => {
    response.json(state.snapshot);
  });

  app.get('/api/events', (_request, response) => {
    response.json({ events: state.events.slice(0, 80) });
  });

  app.get('/api/devices', (_request, response) => {
    response.json(state.devicesSnapshot);
  });

  app.get('/api/devices/events', (_request, response) => {
    response.json({ events: state.deviceEvents.slice(0, 80) });
  });

  app.get('/api/devices/modbus', (_request, response) => {
    response.json({ nodes: state.devicesSnapshot.modbus.nodes });
  });

  app.get('/api/devices/streams', (_request, response) => {
    response.json({ streams: state.devicesSnapshot.streams });
  });

  app.get('/api/devices/:deviceId', (request, response) => {
    const deviceId = request.params.deviceId as DeviceId;
    const detail = state.devicesSnapshot.details[deviceId];
    if (!detail) {
      response.status(404).json({ ok: false, message: 'Unknown device' });
      return;
    }

    response.json(detail);
  });

  app.post('/api/commands/:command', (request, response) => {
    const command = request.params.command as CommandName;
    if (!isKnownCommand(command)) {
      response.status(400).json({ ok: false, message: 'Unknown command' });
      return;
    }

    applyMockCommand(state.runtime, command);
    state.commandCounter += 1;
    state.snapshot = createSnapshot(state.runtime);
    state.devicesSnapshot = createDevicesSnapshot(state.devicesRuntime, {
      websocketClients: wss.clients.size,
      modbusConfigured: Boolean(modbusClient),
      mode: 'mock',
    });
    state.deviceEvents = state.devicesSnapshot.events;

    const result: CommandResult = {
      requestId: `cmd-${Date.now()}-${state.commandCounter}`,
      command,
      accepted: true,
      message: `Command ${command} accepted`,
      timestamp: new Date().toISOString(),
    };

    const event = createMockEvent('INFO', 'command', `${command} accepted`);
    state.events = [event, ...state.snapshot.events, ...state.events].slice(0, 100);

    broadcast({ type: 'event', event });
    broadcast({ type: 'command_result', result });
    broadcast({ type: 'snapshot', snapshot: state.snapshot });
    broadcast({ type: 'devices_snapshot', snapshot: state.devicesSnapshot });
    broadcastDeviceDeltas(state.devicesSnapshot);
    response.json({ ok: true, result, snapshot: state.snapshot });
  });

  const server = http.createServer(app);
  const wss = new WebSocketServer({ noServer: true });
  const port = options.port ?? DEFAULT_PORT;
  const host = options.host ?? DEFAULT_HOST;
  const heartbeat = setInterval(() => {
    state.runtime.tick += 1;
    if (state.runtime.tick % 3 === 0) {
      rotateStage();
    }

    state.snapshot = createSnapshot(state.runtime);
    const deviceEvent = advanceDeviceRuntime(state.devicesRuntime);
    state.devicesSnapshot = createDevicesSnapshot(state.devicesRuntime, {
      websocketClients: wss.clients.size,
      modbusConfigured: Boolean(modbusClient),
      mode: 'mock',
    });
    state.deviceEvents = [deviceEvent, ...state.devicesSnapshot.events, ...state.deviceEvents].slice(0, 100);
    const event = createMockEvent(
      state.snapshot.line.state === 'RUNNING' ? 'INFO' : 'WARN',
      'gateway',
      `Snapshot tick ${state.runtime.tick} captured`,
    );
    state.events = [event, ...state.snapshot.events, ...state.events].slice(0, 100);
    broadcast({ type: 'snapshot', snapshot: state.snapshot });
    broadcast({ type: 'event', event });
    broadcast({ type: 'devices_snapshot', snapshot: state.devicesSnapshot });
    broadcastDeviceDeltas(state.devicesSnapshot);
    broadcast({ type: 'device_event', event: deviceEvent });
    broadcast({ type: 'virtual_model_update', model: state.devicesSnapshot.virtualModels.turtlebot });
    broadcast({ type: 'virtual_model_update', model: state.devicesSnapshot.virtualModels.conveyor });
    for (const stream of state.devicesSnapshot.streams) {
      broadcast({ type: 'stream_status', stream });
    }
  }, 2500);

  server.on('upgrade', (request, socket, head) => {
    if (!request.url?.startsWith('/ws')) {
      socket.destroy();
      return;
    }

    wss.handleUpgrade(request, socket, head, (ws) => {
      wss.emit('connection', ws, request);
    });
  });

  wss.on('connection', (socket) => {
    socket.send(JSON.stringify({ type: 'snapshot', snapshot: state.snapshot } satisfies GatewayMessage));
    socket.send(JSON.stringify({ type: 'event', event: createMockEvent('INFO', 'gateway', 'WebSocket subscriber connected') } satisfies GatewayMessage));
    socket.send(JSON.stringify({ type: 'devices_snapshot', snapshot: state.devicesSnapshot } satisfies GatewayMessage));
  });

  await new Promise<void>((resolve) => {
    server.listen(port, host, () => {
      const address = server.address();
      const actualPort = typeof address === 'object' && address ? address.port : port;
      console.log(`Gateway listening on http://${host}:${actualPort}`);
      resolve();
    });
  });

  return {
    server,
    wss,
    state,
    close: async () => {
      clearInterval(heartbeat);
      if (modbusClient) {
        await modbusClient.disconnect().catch(() => undefined);
      }
      await new Promise<void>((resolve) => {
        wss.close(() => resolve());
      });
      await new Promise<void>((resolve) => {
        server.close(() => resolve());
      });
    },
  };

  function rotateStage() {
    const stageOrder = ['infeed', 'conveyor', 'vision', 'pick', 'outfeed'] as const;
    const currentIndex = stageOrder.indexOf(state.runtime.activeStage);
    state.runtime.activeStage = stageOrder[(currentIndex + 1) % stageOrder.length];
  }

  function createModbusSkeleton() {
    const hostName = process.env.MODBUS_TCP_HOST;
    const portNumber = Number(process.env.MODBUS_TCP_PORT ?? 502);

    if (!hostName) {
      return null;
    }

    return new ModbusTcpClient({
      host: hostName,
      port: portNumber,
      unitId: Number(process.env.MODBUS_UNIT_ID ?? 1),
    });
  }

  function broadcast(message: GatewayMessage) {
    const payload = JSON.stringify(message);
    for (const client of wss.clients) {
      if (client.readyState === WebSocket.OPEN) {
        client.send(payload);
      }
    }
  }

  function broadcastDeviceDeltas(snapshot: DevicesSnapshot) {
    for (const device of snapshot.devices) {
      broadcast({ type: 'device_update', device });
      const detail = snapshot.details[device.id];
      if (detail) {
        broadcast({ type: 'device_detail_update', detail });
      }
    }
  }
}

function createSnapshot(runtime: ReturnType<typeof createMockRuntime>): DashboardSnapshot {
  const snapshot = createMockSnapshot(runtime);
  return {
    ...snapshot,
    gatewayMode: 'live',
    gatewayState: 'online',
  };
}

function setCorsHeaders(_request: express.Request, response: express.Response, next: express.NextFunction) {
  response.setHeader('Access-Control-Allow-Origin', '*');
  response.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  response.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (_request.method === 'OPTIONS') {
    response.sendStatus(204);
    return;
  }

  next();
}

function isKnownCommand(command: string): command is CommandName {
  return [
    'process.start',
    'process.pause',
    'process.resume',
    'process.stop',
    'process.reset_error',
    'robot.home',
    'system.refresh',
  ].includes(command);
}

async function main() {
  await startGatewayServer({
    port: DEFAULT_PORT,
    host: DEFAULT_HOST,
  });
}

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
