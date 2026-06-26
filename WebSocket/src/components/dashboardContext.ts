import { inject, type ComputedRef, type InjectionKey, type Ref } from 'vue';
import type { DevicesSnapshot } from '../../shared/devices';
import type { CommandName, ConnectionState, DashboardSnapshot, TelemetryEvent } from '../../shared/telemetry';

export interface DashboardContext {
  snapshot: Ref<DashboardSnapshot>;
  devicesSnapshot: Ref<DevicesSnapshot>;
  events: Ref<TelemetryEvent[]>;
  connectionState: Ref<ConnectionState>;
  gatewayUrl: Ref<string>;
  busyCommand: Ref<CommandName | null>;
  statusNote: Ref<string>;
  lastSyncLabel: Ref<string>;
  lineCode: ComputedRef<string>;
  onlineDeviceCount: ComputedRef<number>;
  websocketLabel: ComputedRef<string>;
  connectGateway: () => Promise<void>;
  refreshFromGateway: () => Promise<void>;
  runCommand: (command: CommandName) => Promise<void>;
  clearEvents: () => void;
}

export const dashboardContextKey: InjectionKey<DashboardContext> = Symbol('dashboard-context');

export function useDashboardContext(): DashboardContext {
  const context = inject(dashboardContextKey);
  if (!context) {
    throw new Error('Dashboard context was not provided');
  }
  return context;
}
