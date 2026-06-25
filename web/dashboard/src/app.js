const state = {
  ws: null,
  connected: false,
  snapshot: {
    timestamp: new Date().toISOString(),
    system: { mode: "mock", state: "RUNNING", health: "OK" },
    process: { step: "VISION_DETECT", job_id: "job-mock-001", cycle_count: 12, success_count: 11, fail_count: 1 },
    robot: { state: "READY", connected: true, pose: { x: 120.0, y: 30.0, z: 80.0, r: 0.0 }, gripper: "OPEN" },
    vision: { state: "DETECTED", camera_connected: true, detections: [{ label: "target", confidence: 0.93, x: 320, y: 240, depth: 0.42 }] },
    modbus: { state: "CONNECTED", last_update_ms: 120, signals: { conveyor_ready: true, part_detected: true } },
    alarms: [{ severity: "WARN", source: "vision", message: "Mock calibration age is high" }],
  },
  events: [
    { timestamp: new Date().toLocaleTimeString(), severity: "INFO", source: "dashboard", message: "MVP1 mock dashboard initialized" },
  ],
};

const processSteps = [
  ["INPUT", "입고"],
  ["VISION_DETECT", "비전 인식"],
  ["ROBOT_PICK", "로봇 픽업"],
  ["INSPECT_SORT", "검사/분류"],
  ["OUTPUT", "배출"],
];

function badgeClass(value) {
  if (["ERROR", "CRITICAL", "DISCONNECTED", "TIMEOUT", "ESTOP"].includes(value)) return "badge badge-error";
  if (["WARN", "PAUSED", "RECONNECTING"].includes(value)) return "badge badge-warn";
  return "badge";
}

function addEvent(severity, source, message) {
  state.events.unshift({ timestamp: new Date().toLocaleTimeString(), severity, source, message });
  state.events = state.events.slice(0, 80);
  renderEvents();
}

function createCommandPayload(command) {
  return {
    type: "command",
    request_id: `cmd-${Date.now()}`,
    command,
    payload: {},
  };
}

function sendCommand(command) {
  const payload = createCommandPayload(command);
  if (state.connected && state.ws?.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify(payload));
    addEvent("INFO", "command", `sent ${payload.command} (${payload.request_id})`);
    return;
  }
  addEvent("INFO", "mock-command", `created ${payload.command} (${payload.request_id})`);
}

function connectWebSocket() {
  const url = document.querySelector("#wsUrl").value.trim();
  if (!url) return;
  if (state.ws) state.ws.close();
  try {
    state.ws = new WebSocket(url);
    setWsStatus("CONNECTING");
    state.ws.onopen = () => {
      state.connected = true;
      setWsStatus("CONNECTED");
      addEvent("INFO", "websocket", `connected to ${url}`);
      renderControls();
    };
    state.ws.onclose = () => {
      state.connected = false;
      setWsStatus("MOCK");
      addEvent("WARN", "websocket", "connection closed; fallback to mock mode");
      renderControls();
    };
    state.ws.onerror = () => addEvent("ERROR", "websocket", "connection error");
    state.ws.onmessage = (event) => handleGatewayMessage(event.data);
  } catch (error) {
    addEvent("ERROR", "websocket", error.message);
  }
}

function handleGatewayMessage(raw) {
  try {
    const message = JSON.parse(raw);
    if (message.type === "state_snapshot") {
      state.snapshot = message;
      renderAll();
      return;
    }
    if (message.type === "event") {
      addEvent(message.severity || "INFO", message.source || "gateway", message.message || "event received");
      return;
    }
    if (message.type === "command_result") {
      addEvent("INFO", "command_result", `${message.command || message.request_id}: ${message.status}`);
    }
  } catch (error) {
    addEvent("ERROR", "websocket", `invalid message: ${error.message}`);
  }
}

function setWsStatus(label) {
  const el = document.querySelector("#wsStatus");
  el.textContent = label;
  el.className = label === "CONNECTED" ? "badge" : label === "CONNECTING" ? "badge badge-warn" : "badge badge-muted";
}

function renderStatusGrid() {
  const s = state.snapshot;
  const items = [
    ["System", s.system.state, s.system.mode],
    ["Robot", s.robot.state, s.robot.connected ? "connected" : "offline"],
    ["Vision", s.vision.state, s.vision.camera_connected ? "camera online" : "camera offline"],
    ["PLC/Modbus", s.modbus.state, `${s.modbus.last_update_ms}ms ago`],
    ["WebSocket", state.connected ? "CONNECTED" : "MOCK", "gateway contract ready"],
  ];
  document.querySelector("#statusGrid").innerHTML = items.map(([title, value, sub]) => `
    <article class="panel status-card ${value === "CONNECTED" || value === "READY" || value === "RUNNING" ? "ok" : ""}">
      <span>${title}</span>
      <strong>${value}</strong>
      <span>${sub}</span>
    </article>
  `).join("");
}

function renderProcessFlow() {
  const current = state.snapshot.process.step;
  document.querySelector("#processFlow").innerHTML = processSteps.map(([key, title], index) => `
    <div class="process-step ${key === current ? "active" : ""}">
      <div class="step-index">${index + 1}</div>
      <div>
        <div class="step-title">${title}</div>
        <div class="step-state">${key === current ? "ACTIVE" : "WAITING"}</div>
      </div>
    </div>
  `).join("");
}

function renderJob() {
  const p = state.snapshot.process;
  document.querySelector("#jobTitle").textContent = p.job_id;
  const systemState = document.querySelector("#systemState");
  systemState.textContent = state.snapshot.system.state;
  systemState.className = badgeClass(state.snapshot.system.state);
  document.querySelector("#jobSummary").innerHTML = [
    ["Current Step", p.step],
    ["Cycle", p.cycle_count],
    ["Success", p.success_count],
    ["Fail", p.fail_count],
  ].map(([label, value]) => `<div class="metric"><span class="label">${label}</span><span class="value">${value}</span></div>`).join("");
}

function renderPanel(selector, title, rows) {
  document.querySelector(selector).innerHTML = `
    <div class="panel-heading"><p class="eyebrow">Monitor</p><h2>${title}</h2></div>
    ${rows.map(([k, v]) => `<div class="kv"><span>${k}</span><strong>${v}</strong></div>`).join("")}
  `;
}

function renderMonitoringPanels() {
  const s = state.snapshot;
  const det = s.vision.detections?.[0];
  renderPanel("#robotPanel", "Robot", [
    ["State", s.robot.state], ["Connected", s.robot.connected], ["Pose X/Y/Z", `${s.robot.pose.x} / ${s.robot.pose.y} / ${s.robot.pose.z}`], ["Gripper", s.robot.gripper],
  ]);
  renderPanel("#visionPanel", "Vision", [
    ["State", s.vision.state], ["Camera", s.vision.camera_connected ? "ONLINE" : "OFFLINE"], ["Detection", det ? `${det.label} ${(det.confidence * 100).toFixed(0)}%` : "none"], ["Pixel/Depth", det ? `${det.x}, ${det.y}, ${det.depth}m` : "-"],
  ]);
  renderPanel("#modbusPanel", "PLC / Modbus", [
    ["State", s.modbus.state], ["Last Update", `${s.modbus.last_update_ms}ms`], ["Conveyor", s.modbus.signals.conveyor_ready], ["Part Sensor", s.modbus.signals.part_detected],
  ]);
  renderPanel("#healthPanel", "Health", [
    ["Gateway", state.connected ? "CONNECTED" : "MOCK"], ["ROS2 Bridge", "PENDING"], ["DB", "PENDING"], ["Updated", new Date(s.timestamp || Date.now()).toLocaleTimeString()],
  ]);
}

function renderControls() {
  document.querySelectorAll("[data-command]").forEach((button) => {
    button.onclick = () => sendCommand(button.dataset.command);
    button.disabled = false;
  });
}

function renderAlarms() {
  const alarms = state.snapshot.alarms || [];
  document.querySelector("#alarmList").innerHTML = alarms.length ? alarms.map((alarm) => `
    <div class="alarm-item ${String(alarm.severity).toLowerCase()}">
      <strong>${alarm.severity}</strong> · ${alarm.source}<br />
      <span>${alarm.message}</span>
    </div>
  `).join("") : `<p class="hint">활성 알람 없음</p>`;
}

function renderEvents() {
  document.querySelector("#eventLog").innerHTML = state.events.map((event) => `
    <tr><td>${event.timestamp}</td><td>${event.severity}</td><td>${event.source}</td><td>${event.message}</td></tr>
  `).join("");
}

function renderAll() {
  renderStatusGrid();
  renderProcessFlow();
  renderJob();
  renderMonitoringPanels();
  renderControls();
  renderAlarms();
  renderEvents();
}

document.querySelector("#connectButton").addEventListener("click", connectWebSocket);
document.querySelector("#clearEvents").addEventListener("click", () => { state.events = []; renderEvents(); });
renderAll();
