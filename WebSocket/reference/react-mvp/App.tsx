import { useRef, useState } from 'react';
import { Activity, Bot, Camera, Cpu, Network } from 'lucide-react';
import { AlarmList } from './components/AlarmList';
import { ControlPanel } from './components/ControlPanel';
import { EventLog } from './components/EventLog';
import { MonitorPanel } from './components/MonitorPanel';
import { ProcessFlow } from './components/ProcessFlow';
import { StatusCard } from './components/StatusCard';
import { createCommandPayload, openGatewaySocket } from './lib/gatewayClient';
import { initialEvents, initialSnapshot } from './lib/mockData';
import type { DashboardSnapshot, EventItem, GatewayMessage, WebSocketState } from './lib/types';

function now() {
  return new Date().toLocaleTimeString();
}

export function App() {
  const [wsUrl, setWsUrl] = useState('ws://localhost:8765');
  const [wsState, setWsState] = useState<WebSocketState>('MOCK');
  const [snapshot, setSnapshot] = useState<DashboardSnapshot>(initialSnapshot);
  const [events, setEvents] = useState<EventItem[]>(initialEvents);
  const socketRef = useRef<WebSocket | null>(null);

  const addEvent = (severity: EventItem['severity'], source: string, message: string) => {
    setEvents((current) => [{ timestamp: now(), severity, source, message }, ...current].slice(0, 80));
  };

  const handleGatewayMessage = (message: GatewayMessage) => {
    if (message.type === 'state_snapshot') {
      setSnapshot(message);
      return;
    }
    if (message.type === 'event') {
      addEvent(message.severity, message.source, message.message);
      return;
    }
    if (message.type === 'command_result') {
      addEvent('INFO', 'command_result', `${message.command ?? message.request_id}: ${message.status}`);
    }
  };

  const connect = () => {
    socketRef.current?.close();
    setWsState('CONNECTING');
    socketRef.current = openGatewaySocket(wsUrl, {
      onOpen: () => { setWsState('CONNECTED'); addEvent('INFO', 'websocket', `connected to ${wsUrl}`); },
      onClose: () => { setWsState('MOCK'); addEvent('WARN', 'websocket', 'connection closed; fallback to mock mode'); },
      onError: (message) => { setWsState('ERROR'); addEvent('ERROR', 'websocket', message); },
      onMessage: handleGatewayMessage,
    });
  };

  const sendCommand = (command: string) => {
    const payload = createCommandPayload(command);
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(payload));
      addEvent('INFO', 'command', `sent ${payload.command} (${payload.request_id})`);
      return;
    }
    addEvent('INFO', 'mock-command', `created ${payload.command} (${payload.request_id})`);
  };

  const detection = snapshot.vision.detections[0];

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Throughline Control Room</p>
          <h1>Operations Dashboard</h1>
        </div>
        <div className="connection-panel">
          <label htmlFor="wsUrl">Gateway</label>
          <input id="wsUrl" value={wsUrl} onChange={(event) => setWsUrl(event.target.value)} />
          <button onClick={connect}>Connect</button>
          <span className={`badge ${wsState === 'CONNECTED' ? '' : wsState === 'ERROR' ? 'badge-error' : 'badge-muted'}`}>{wsState}</span>
        </div>
      </header>

      <section className="status-grid">
        <StatusCard title="System" value={snapshot.system.state} detail={snapshot.system.mode} tone="ok" />
        <StatusCard title="Robot" value={snapshot.robot.state} detail={snapshot.robot.connected ? 'connected' : 'offline'} tone="ok" />
        <StatusCard title="Vision" value={snapshot.vision.state} detail={snapshot.vision.camera_connected ? 'camera online' : 'camera offline'} tone="ok" />
        <StatusCard title="PLC/Modbus" value={snapshot.modbus.state} detail={`${snapshot.modbus.last_update_ms}ms ago`} tone="ok" />
        <StatusCard title="WebSocket" value={wsState} detail="gateway contract ready" tone={wsState === 'CONNECTED' ? 'ok' : 'mock'} />
      </section>

      <section className="dashboard-grid">
        <ProcessFlow currentStep={snapshot.process.step} />

        <section className="monitoring-stack">
          <section className="panel highlight-panel">
            <div className="panel-heading row-between">
              <div>
                <p className="eyebrow">Current Job</p>
                <h2>{snapshot.process.job_id}</h2>
              </div>
              <span className="badge">{snapshot.system.state}</span>
            </div>
            <div className="metric-grid">
              <div className="metric"><Activity size={18} /><span className="label">Current Step</span><span className="value">{snapshot.process.step}</span></div>
              <div className="metric"><Cpu size={18} /><span className="label">Cycle</span><span className="value">{snapshot.process.cycle_count}</span></div>
              <div className="metric"><Network size={18} /><span className="label">Success</span><span className="value">{snapshot.process.success_count}</span></div>
              <div className="metric"><Bot size={18} /><span className="label">Fail</span><span className="value">{snapshot.process.fail_count}</span></div>
            </div>
          </section>

          <div className="card-grid">
            <MonitorPanel title="Robot" rows={[
              ['State', snapshot.robot.state], ['Connected', snapshot.robot.connected], ['Pose X/Y/Z', `${snapshot.robot.pose.x} / ${snapshot.robot.pose.y} / ${snapshot.robot.pose.z}`], ['Gripper', snapshot.robot.gripper],
            ]} />
            <MonitorPanel title="Vision" rows={[
              ['State', snapshot.vision.state], ['Camera', snapshot.vision.camera_connected ? 'ONLINE' : 'OFFLINE'], ['Detection', detection ? `${detection.label} ${(detection.confidence * 100).toFixed(0)}%` : 'none'], ['Pixel/Depth', detection ? `${detection.x}, ${detection.y}, ${detection.depth}m` : '-'],
            ]} />
            <MonitorPanel title="PLC / Modbus" rows={[
              ['State', snapshot.modbus.state], ['Last Update', `${snapshot.modbus.last_update_ms}ms`], ['Conveyor', snapshot.modbus.signals.conveyor_ready], ['Part Sensor', snapshot.modbus.signals.part_detected],
            ]} />
            <MonitorPanel title="Health" rows={[
              ['Gateway', wsState], ['ROS2 Bridge', 'PENDING'], ['DB', 'PENDING'], ['Updated', new Date(snapshot.timestamp).toLocaleTimeString()],
            ]} />
          </div>
        </section>

        <aside className="control-stack">
          <ControlPanel onCommand={sendCommand} />
          <AlarmList alarms={snapshot.alarms} />
        </aside>
      </section>

      <EventLog events={events} onClear={() => setEvents([])} />
    </main>
  );
}
