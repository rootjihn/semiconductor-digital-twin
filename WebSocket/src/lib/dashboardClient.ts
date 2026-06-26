import type { DevicesSnapshot } from '../../shared/devices';
import type { CommandName, CommandResult, DashboardSnapshot, GatewayMessage, TelemetryEvent } from '../../shared/telemetry';

export function getGatewayBaseUrl(): string {
  return (import.meta.env.VITE_GATEWAY_URL as string | undefined)?.trim() || 'http://localhost:8765';
}

export function toWebSocketUrl(baseUrl: string): string {
  const normalized = normalizeBaseUrl(baseUrl);
  return new URL('/ws', normalized.replace(/^http/, 'ws')).toString();
}

export async function fetchGatewaySnapshot(baseUrl: string): Promise<DashboardSnapshot> {
  const response = await fetch(`${normalizeBaseUrl(baseUrl)}/api/snapshot`, {
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Snapshot request failed (${response.status})`);
  }

  return (await response.json()) as DashboardSnapshot;
}

export async function fetchGatewayEvents(baseUrl: string): Promise<TelemetryEvent[]> {
  const response = await fetch(`${normalizeBaseUrl(baseUrl)}/api/events`, {
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Events request failed (${response.status})`);
  }

  const payload = (await response.json()) as { events: TelemetryEvent[] } | TelemetryEvent[];
  return Array.isArray(payload) ? payload : payload.events;
}

export async function fetchDevicesSnapshot(baseUrl: string): Promise<DevicesSnapshot> {
  const response = await fetch(`${normalizeBaseUrl(baseUrl)}/api/devices`, {
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Devices request failed (${response.status})`);
  }

  return (await response.json()) as DevicesSnapshot;
}

export async function sendGatewayCommand(baseUrl: string, command: CommandName): Promise<CommandResult> {
  const response = await fetch(`${normalizeBaseUrl(baseUrl)}/api/commands/${encodeURIComponent(command)}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ command }),
  });

  if (!response.ok) {
    throw new Error(`Command request failed (${response.status})`);
  }

  const payload = (await response.json()) as { result?: CommandResult; command?: CommandResult } | CommandResult;
  if ('accepted' in payload) {
    return payload;
  }

  return payload.result ?? payload.command ?? {
    requestId: `cmd-${Date.now()}`,
    command,
    accepted: false,
    message: 'Invalid command payload',
    timestamp: new Date().toISOString(),
  };
}

export function openGatewaySocket(
  baseUrl: string,
  handlers: {
    onOpen: () => void;
    onClose: () => void;
    onError: (message: string) => void;
    onMessage: (message: GatewayMessage) => void;
  },
): WebSocket {
  const socket = new WebSocket(toWebSocketUrl(baseUrl));

  socket.onopen = handlers.onOpen;
  socket.onclose = handlers.onClose;
  socket.onerror = () => handlers.onError('WebSocket connection error');
  socket.onmessage = (event) => {
    try {
      handlers.onMessage(JSON.parse(String(event.data)) as GatewayMessage);
    } catch (error) {
      handlers.onError(error instanceof Error ? error.message : 'Invalid gateway message');
    }
  };

  return socket;
}

function normalizeBaseUrl(baseUrl: string): string {
  const trimmed = baseUrl.trim().replace(/\/$/, '');

  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }

  return `http://${trimmed}`;
}
