import type { CommandPayload, GatewayMessage } from './types';

export function createCommandPayload(command: string): CommandPayload {
  return {
    type: 'command',
    request_id: `cmd-${Date.now()}`,
    command,
    payload: {},
  };
}

export function parseGatewayMessage(raw: string): GatewayMessage {
  return JSON.parse(raw) as GatewayMessage;
}

export function openGatewaySocket(
  url: string,
  handlers: {
    onOpen: () => void;
    onClose: () => void;
    onError: (message: string) => void;
    onMessage: (message: GatewayMessage) => void;
  },
): WebSocket {
  const socket = new WebSocket(url);
  socket.onopen = handlers.onOpen;
  socket.onclose = handlers.onClose;
  socket.onerror = () => handlers.onError('WebSocket connection error');
  socket.onmessage = (event) => {
    try {
      handlers.onMessage(parseGatewayMessage(String(event.data)));
    } catch (error) {
      handlers.onError(error instanceof Error ? error.message : 'Invalid gateway message');
    }
  };
  return socket;
}
