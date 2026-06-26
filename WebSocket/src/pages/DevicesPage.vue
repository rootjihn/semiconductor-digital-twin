<template>
  <section class="zd-devices-page" aria-label="장비 탭">
    <header class="zd-devices-header">
      <h1>장비 탭</h1>
      <div class="zd-status-strip" aria-label="전체 시스템 상태">
        <article class="zd-status-chip">
          <span :class="['zd-dot', devices.gateway.state === 'ONLINE' ? 'zd-dot--good' : 'zd-dot--warn']"></span>
          <span>Gateway: {{ gatewayModeLabel }}</span>
        </article>
        <article class="zd-status-chip">
          <span class="zd-check">✓</span>
          <span>전체 라인</span>
          <strong :class="lineStateTone">{{ lineStateLabel }}</strong>
        </article>
        <article class="zd-status-chip">
          <span class="zd-warning">!</span>
          <span>WARN/ERROR</span>
          <strong class="zd-text-danger">{{ alarmCount }}건</strong>
        </article>
        <article class="zd-status-chip zd-status-chip--wide">
          <span class="zd-clock">◷</span>
          <span>마지막 동기화 {{ formatClock(devices.timestamp || snapshot.timestamp) }}</span>
        </article>
      </div>
    </header>

    <div class="zd-devices-layout">
      <aside class="zd-left-column" aria-label="요약">
        <section class="zd-card zd-summary-card">
          <h2>상태 요약</h2>
          <ul class="zd-summary-list">
            <li v-for="item in summaryRows" :key="item.label">
              <span><i :class="['zd-dot', `zd-dot--${item.tone}`]"></i>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </li>
          </ul>
        </section>

        <section class="zd-card zd-comm-card">
          <h2>통신 상태</h2>
          <dl class="zd-metric-list">
            <div><dt>평균 RTT</dt><dd>{{ devices.communication.avgRttMs }} ms</dd></div>
            <div><dt>최대 RTT</dt><dd>{{ devices.communication.maxRttMs }} ms</dd></div>
            <div><dt>Timeout</dt><dd>{{ devices.communication.timeoutCount }}</dd></div>
            <div><dt>Retry</dt><dd>{{ devices.communication.retryCount }}</dd></div>
          </dl>
          <ul class="zd-rtt-list">
            <li v-for="node in devices.communication.nodes" :key="node.deviceId">
              <span><i :class="['zd-dot', node.online ? 'zd-dot--good' : 'zd-dot--offline']"></i>{{ shortDeviceName(node.deviceId) }}</span>
              <strong>{{ node.rttMs }} ms</strong>
            </li>
          </ul>
        </section>

        <section class="zd-card zd-events-card">
          <h2>최근 알림</h2>
          <ul class="zd-event-list">
            <li v-for="event in recentEvents" :key="event.id">
              <span :class="['zd-event-icon', `zd-event-icon--${eventTone(event.severity)}`]">{{ eventIcon(event.severity) }}</span>
              <p>{{ event.message }}</p>
              <time>{{ formatClock(event.timestamp) }}</time>
            </li>
            <li v-if="!recentEvents.length" class="zd-empty-row">최근 알림 없음</li>
          </ul>
          <button class="zd-secondary-action" type="button" @click="refreshFromGateway">알림 새로고침</button>
        </section>
      </aside>

      <main class="zd-main-column" aria-label="장비 목록과 선택 프리뷰">
        <section class="zd-card zd-device-board">
          <div class="zd-board-head">
            <div>
              <h2>장비 목록</h2>
              <p>게이트웨이 스냅샷 기준 장비와 연결된 영상/가상 모델 상태입니다.</p>
            </div>
            <div class="zd-filters">
              <label class="zd-search-box">
                <span>⌕</span>
                <input v-model="searchText" type="search" placeholder="장비 검색" />
              </label>
              <select v-model="stateFilter" aria-label="상태 필터">
                <option value="all">전체 상태</option>
                <option value="ONLINE">온라인</option>
                <option value="RUNNING">가동/작업 중</option>
                <option value="WAITING">대기</option>
                <option value="OFFLINE">오프라인</option>
              </select>
              <select v-model="roleFilter" aria-label="역할 필터">
                <option value="all">전체 역할</option>
                <option v-for="role in roles" :key="role" :value="role">{{ roleLabel(role) }}</option>
              </select>
            </div>
          </div>

          <div class="zd-device-grid">
            <article
              v-for="device in filteredDevices"
              :key="device.id"
              class="zd-device-card"
              :class="{ 'zd-device-card--selected': selectedDeviceId === device.id }"
              tabindex="0"
              @click="selectDevice(device.id)"
              @keydown.enter.prevent="selectDevice(device.id)"
            >
              <figure>
                <img :src="deviceImage(device.id)" :alt="device.name" />
              </figure>
              <div class="zd-device-card__body">
                <div class="zd-device-title-row">
                  <h3>{{ device.name }}</h3>
                  <span :class="['zd-state-badge', `zd-state-badge--${stateTone(device.state, device.connection)}`]">{{ stateLabel(device.state) }}</span>
                </div>
                <p>{{ roleLabel(device.role) }}</p>
                <dl>
                  <div><dt>연결</dt><dd>{{ connectionLabel(device.connection) }}</dd></div>
                  <div><dt>RTT</dt><dd>{{ device.rttMs }} ms</dd></div>
                </dl>
                <small>{{ deviceMediaStatus(device.id) }}</small>
              </div>
              <span v-if="selectedDeviceId === device.id" class="zd-selected-mark">✓</span>
            </article>
            <p v-if="!filteredDevices.length" class="zd-empty-card">조건에 맞는 장비가 없습니다.</p>
          </div>
        </section>

        <section class="zd-card zd-preview-board">
          <header class="zd-preview-head">
            <div>
              <h2>{{ selectedDevice.name }} 프리뷰</h2>
              <p>{{ previewSubtitle }}</p>
            </div>
            <div class="zd-preview-actions">
              <button class="zd-test-button" type="button" @click="refreshFromGateway">⌁ 연결 테스트</button>
              <button
                v-if="selectedMediaUrl"
                class="zd-primary-action"
                type="button"
                @click="openMedia(selectedMediaUrl)"
              >
                미디어 확인
              </button>
              <button
                v-if="selectedNextMediaUrl"
                class="zd-secondary-action"
                type="button"
                @click="openMedia(selectedNextMediaUrl)"
              >
                다음 소스 확인
              </button>
              <button
                v-if="isVirtualModelSelected"
                class="zd-primary-action"
                type="button"
                @click="refreshFromGateway"
              >
                모델 데이터 갱신
              </button>
            </div>
          </header>

          <div class="zd-preview-body">
            <div v-if="selectedMediaUrl" class="zd-video-panel">
              <video
                :key="selectedMediaUrl"
                :src="selectedMediaUrl"
                controls
                muted
                playsinline
                :loop="selectedStream?.loop || selectedStream?.playbackMode === 'loop'"
              ></video>
              <div class="zd-video-meta">
                <span :class="['zd-state-badge', `zd-state-badge--${streamTone(selectedStream?.status)}`]">{{ selectedStream?.status ?? 'LIVE' }}</span>
                <span>{{ selectedStream?.label ?? selectedStream?.id }}</span>
                <span v-if="selectedStream?.width && selectedStream?.height">{{ selectedStream.width }}×{{ selectedStream.height }}</span>
                <span v-if="selectedStream?.fps">{{ selectedStream.fps }} fps</span>
                <span v-if="isSequenceStream" class="zd-sequence-chip">{{ sequenceLabel }}</span>
              </div>
              <dl class="zd-source-list">
                <div><dt>현재 소스</dt><dd>{{ selectedStream?.sourceUrl ?? '-' }}</dd></div>
                <div v-if="selectedStream?.nextSourceUrl"><dt>다음 소스</dt><dd>{{ selectedStream.nextSourceUrl }}</dd></div>
                <div><dt>송신 방식</dt><dd>{{ transportLabel(selectedStream?.transport) }}</dd></div>
              </dl>
            </div>

            <div v-else-if="selectedDevice.id === 'turtlebot'" class="zd-virtual-panel">
              <svg class="zd-turtle-map" viewBox="0 0 520 300" role="img" aria-label="터틀봇 가상 지도">
                <defs>
                  <pattern id="map-grid" width="26" height="26" patternUnits="userSpaceOnUse">
                    <path d="M 26 0 L 0 0 0 26" fill="none" stroke="#d8e5f5" stroke-width="1" />
                  </pattern>
                </defs>
                <rect x="20" y="20" width="480" height="260" rx="16" fill="#f7fbff" stroke="#cddced" />
                <rect x="20" y="20" width="480" height="260" rx="16" fill="url(#map-grid)" />
                <polyline v-if="turtlePathPolyline" :points="turtlePathPolyline" fill="none" stroke="#2878ff" stroke-width="5" stroke-linecap="round" stroke-dasharray="10 9" />
                <rect
                  v-for="obstacle in turtleObstacleRects"
                  :key="obstacle.id"
                  :x="obstacle.x"
                  :y="obstacle.y"
                  :width="obstacle.width"
                  :height="obstacle.height"
                  rx="8"
                  fill="#f3c35a"
                  stroke="#ba8420"
                  opacity="0.85"
                />
                <g v-for="station in turtleStationPoints" :key="station.id">
                  <circle :cx="station.x" :cy="station.y" r="10" fill="#ffffff" stroke="#18a83a" stroke-width="4" />
                  <text :x="station.x + 12" :y="station.y - 10">{{ station.label }}</text>
                </g>
                <g v-if="turtleTargetPoint">
                  <circle :cx="turtleTargetPoint.x" :cy="turtleTargetPoint.y" r="12" fill="#ff5f46" opacity="0.2" />
                  <circle :cx="turtleTargetPoint.x" :cy="turtleTargetPoint.y" r="6" fill="#ff5f46" />
                  <text :x="turtleTargetPoint.x + 12" :y="turtleTargetPoint.y + 4">{{ turtleModel.target?.label ?? 'Target' }}</text>
                </g>
                <g :transform="`translate(${turtlePosePoint.x} ${turtlePosePoint.y}) rotate(${turtlePosePoint.theta})`">
                  <circle r="17" fill="#12b532" stroke="#ffffff" stroke-width="5" />
                  <path d="M0 -26 L9 -5 L-9 -5 Z" fill="#0e2454" />
                </g>
              </svg>
              <dl class="zd-virtual-facts">
                <div><dt>위치</dt><dd>x {{ turtleModel.pose.x.toFixed(2) }} / y {{ turtleModel.pose.y.toFixed(2) }}</dd></div>
                <div><dt>방향</dt><dd>{{ turtleModel.pose.thetaDeg.toFixed(0) }}°</dd></div>
                <div><dt>목표</dt><dd>{{ turtleModel.target ? `${turtleModel.target.label} (${turtleModel.target.x.toFixed(1)}, ${turtleModel.target.y.toFixed(1)})` : '-' }}</dd></div>
                <div><dt>배터리</dt><dd>{{ turtleModel.batteryPct }}%</dd></div>
                <div><dt>주행 상태</dt><dd>{{ turtleModel.motionState }}</dd></div>
              </dl>
            </div>

            <div v-else-if="selectedDevice.id === 'conveyor'" class="zd-virtual-panel">
              <div class="zd-conveyor-model" :class="{ 'zd-conveyor-model--reverse': conveyorModel.direction === 'REVERSE' }">
                <div class="zd-conveyor-belt">
                  <span v-for="tick in 8" :key="tick"></span>
                </div>
                <span
                  v-for="box in conveyorModel.boxes"
                  :key="box.id"
                  class="zd-conveyor-box"
                  :class="{ 'zd-conveyor-box--detected': box.detected }"
                  :style="{ left: `${clampPct(box.positionPct)}%` }"
                >{{ box.id }}</span>
                <span
                  v-for="sensor in conveyorModel.sensors"
                  :key="sensor.id"
                  class="zd-conveyor-sensor"
                  :class="{ 'zd-conveyor-sensor--active': sensor.active }"
                  :style="{ left: `${clampPct(sensor.positionPct)}%` }"
                >{{ sensor.label }}</span>
                <div class="zd-servo" :style="{ left: `${clampPct(conveyorModel.servoPositionPct ?? 50)}%` }">
                  <span :style="{ transform: `rotate(${conveyorModel.servoAngleDeg ?? 0}deg)` }"></span>
                  <small>{{ conveyorModel.servoDirection ?? 'CENTER' }}</small>
                </div>
                <strong class="zd-belt-arrow">{{ conveyorModel.direction === 'FORWARD' ? '→' : '←' }}</strong>
              </div>
              <dl class="zd-virtual-facts">
                <div><dt>동작</dt><dd>{{ conveyorModel.running ? 'RUNNING' : 'STOPPED' }}</dd></div>
                <div><dt>방향</dt><dd>{{ conveyorModel.direction }}</dd></div>
                <div><dt>속도</dt><dd>{{ conveyorModel.speedPct }}%</dd></div>
                <div><dt>서보</dt><dd>{{ conveyorModel.servoDirection ?? 'CENTER' }} / {{ conveyorModel.servoAngleDeg ?? 0 }}°</dd></div>
                <div><dt>센서</dt><dd>{{ activeSensorLabel }}</dd></div>
              </dl>
            </div>

            <div v-else-if="selectedDevice.id === 'gateway'" class="zd-gateway-panel">
              <dl class="zd-gateway-grid">
                <div><dt>모드</dt><dd>{{ gatewayModeLabel }}</dd></div>
                <div><dt>WebSocket Clients</dt><dd>{{ devices.gateway.websocketClients }}</dd></div>
                <div><dt>Adapter</dt><dd>{{ devices.gateway.modbusConfigured ? 'configured' : 'mock/local' }}</dd></div>
                <div><dt>RTT</dt><dd>{{ selectedDevice.rttMs }} ms</dd></div>
                <div><dt>Timeout</dt><dd>{{ selectedDevice.timeoutCount }}</dd></div>
                <div><dt>Retry</dt><dd>{{ selectedDevice.retryCount }}</dd></div>
                <div><dt>최근 갱신</dt><dd>{{ formatClock(selectedDevice.lastUpdated) }}</dd></div>
              </dl>
            </div>

            <div v-else class="zd-no-preview">
              <img :src="deviceImage(selectedDevice.id)" :alt="selectedDevice.name" />
              <strong>{{ selectedDevice.name }}</strong>
              <p>이 장비는 현재 표시할 정적 영상이나 가상 모델 데이터가 없습니다.</p>
            </div>
          </div>
        </section>
      </main>

      <aside class="zd-right-column" aria-label="선택 장비 상세">
        <section class="zd-card zd-selected-card">
          <h2>선택 장비</h2>
          <div class="zd-selected-head">
            <figure><img :src="deviceImage(selectedDevice.id)" :alt="selectedDevice.name" /></figure>
            <div>
              <h3>{{ selectedDevice.name }}</h3>
              <span :class="['zd-state-badge', `zd-state-badge--${stateTone(selectedDevice.state, selectedDevice.connection)}`]">{{ stateLabel(selectedDevice.state) }}</span>
              <p>{{ selectedDevice.statusText }}</p>
            </div>
          </div>

          <dl class="zd-selected-facts">
            <div v-for="fact in selectedFacts" :key="fact.label">
              <dt>{{ fact.label }}</dt>
              <dd :class="fact.tone ? `zd-text-${fact.tone}` : undefined">{{ fact.value }}</dd>
            </div>
          </dl>

          <section class="zd-stream-list">
            <h3>연결 어댑터</h3>
            <ul>
              <li v-for="stream in selectedStreams" :key="stream.id">
                <span>{{ stream.label }}</span>
                <strong>{{ transportLabel(stream.transport) }}</strong>
              </li>
              <li v-if="!selectedStreams.length && !isVirtualModelSelected">연결된 영상/모델 어댑터 없음</li>
              <li v-if="isVirtualModelSelected">
                <span>{{ selectedDevice.id === 'turtlebot' ? 'TurtleBot 가상 맵' : 'Conveyor 가상 모델' }}</span>
                <strong>metadata-only</strong>
              </li>
            </ul>
          </section>

          <section class="zd-selected-events">
            <h3>장비 알림</h3>
            <ul>
              <li v-for="event in selectedEvents" :key="event.id">
                <span :class="`zd-event-dot--${eventTone(event.severity)}`"></span>
                <p>{{ event.message }}</p>
                <time>{{ formatClock(event.timestamp) }}</time>
              </li>
              <li v-if="!selectedEvents.length" class="zd-empty-row">알림 없음</li>
            </ul>
          </section>
        </section>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useDashboardContext } from '../components/dashboardContext';
import type {
  ConveyorModelState,
  DeviceConnectionState,
  DeviceEventSeverity,
  DeviceId,
  DeviceNode,
  DeviceOperatingState,
  DeviceRole,
  DeviceStream,
  TurtleBotMapState,
} from '../../shared/devices';

import dobotImage from '../assets/dashboard/devices/device-dobot-magician.png';
import turtlebotImage from '../assets/dashboard/devices/device-turtlebot3-waffle-pi.png';
import realsenseImage from '../assets/dashboard/devices/device-realsense-camera.png';
import conveyorImage from '../assets/dashboard/devices/device-conveyor-rpi5.png';
import robodkImage from '../assets/dashboard/devices/device-robodk-monitor.png';
import serverImage from '../assets/dashboard/devices/device-server-rack.png';

const { snapshot, devicesSnapshot, gatewayUrl, refreshFromGateway } = useDashboardContext();

const searchText = ref('');
const stateFilter = ref<'all' | 'ONLINE' | 'RUNNING' | 'WAITING' | 'OFFLINE'>('all');
const roleFilter = ref<'all' | DeviceRole>('all');
const selectedDeviceId = ref<DeviceId>('dobot');

const deviceImages: Record<DeviceId, string> = {
  dobot: dobotImage,
  turtlebot: turtlebotImage,
  realsense: realsenseImage,
  conveyor: conveyorImage,
  robodk: robodkImage,
  gateway: serverImage,
};

const devices = computed(() => devicesSnapshot.value);
const roles = computed(() => Array.from(new Set(devices.value.devices.map((device) => device.role))));
const alarmCount = computed(() => devices.value.summary.warning + devices.value.summary.fault + devices.value.summary.offline);
const gatewayModeLabel = computed(() => (devices.value.gateway.mode === 'live' ? 'Live' : 'Mock'));
const lineStateLabel = computed(() => {
  if (snapshot.value.line.state === 'RUNNING') return '가동';
  if (snapshot.value.line.state === 'PAUSED') return '대기';
  if (snapshot.value.line.state === 'FAULT') return '오류';
  return '정지';
});
const lineStateTone = computed(() => (snapshot.value.line.state === 'FAULT' ? 'zd-text-danger' : snapshot.value.line.state === 'RUNNING' ? 'zd-text-good' : 'zd-text-warn'));

const summaryRows = computed(() => [
  { label: '정상', value: devices.value.summary.normal, tone: 'good' },
  { label: '작업 중', value: devices.value.summary.running, tone: 'blue' },
  { label: '대기', value: devices.value.summary.waiting, tone: 'muted' },
  { label: '경고', value: devices.value.summary.warning, tone: 'warn' },
  { label: '오류', value: devices.value.summary.fault, tone: 'danger' },
  { label: '오프라인', value: devices.value.summary.offline, tone: 'offline' },
]);

const filteredDevices = computed(() => {
  const query = searchText.value.trim().toLowerCase();
  return devices.value.devices.filter((device) => {
    const matchesQuery = !query || [device.name, device.ip, device.role, device.statusText, device.primaryStreamId]
      .some((value) => String(value ?? '').toLowerCase().includes(query));
    const matchesRole = roleFilter.value === 'all' || device.role === roleFilter.value;
    const matchesState = stateFilter.value === 'all'
      || (stateFilter.value === 'ONLINE' && device.connection === 'ONLINE')
      || (stateFilter.value === 'RUNNING' && ['RUNNING', 'BUSY', 'STREAMING', 'MOVING'].includes(device.state))
      || (stateFilter.value === 'WAITING' && ['READY', 'WAITING', 'STOPPED', 'IDLE'].includes(device.state))
      || (stateFilter.value === 'OFFLINE' && !device.online);
    return matchesQuery && matchesRole && matchesState;
  });
});

const selectedDevice = computed<DeviceNode>(() => {
  return devices.value.devices.find((device) => device.id === selectedDeviceId.value) ?? devices.value.devices[0] ?? emptyDevice();
});
const selectedDetail = computed(() => devices.value.details[selectedDevice.value.id]);
const selectedStreams = computed(() => {
  const detailStreams = selectedDetail.value?.streams ?? [];
  const topStreams = devices.value.streams.filter((stream) => stream.deviceId === selectedDevice.value.id);
  const merged = [...detailStreams, ...topStreams];
  return merged.filter((stream, index) => merged.findIndex((item) => item.id === stream.id) === index);
});
const selectedStream = computed(() => {
  const primary = selectedDevice.value.primaryStreamId;
  return selectedStreams.value.find((stream) => stream.id === primary) ?? selectedStreams.value.find((stream) => stream.sourceUrl) ?? selectedStreams.value[0];
});
const selectedMediaUrl = computed(() => mediaUrl(selectedStream.value?.sourceUrl));
const selectedNextMediaUrl = computed(() => mediaUrl(selectedStream.value?.nextSourceUrl));
const isSequenceStream = computed(() => selectedStream.value?.playbackMode === 'sequence' || Boolean(selectedStream.value?.sequenceLength));
const sequenceLabel = computed(() => {
  const stream = selectedStream.value;
  if (!stream?.sequenceLength) return 'sequence';
  return `${(stream.sequenceIndex ?? 0) + 1}/${stream.sequenceLength}`;
});
const isVirtualModelSelected = computed(() => selectedDevice.value.id === 'turtlebot' || selectedDevice.value.id === 'conveyor');
const previewSubtitle = computed(() => {
  if (selectedMediaUrl.value) return selectedStream.value?.playbackMode === 'sequence' ? '녹화 파일 순차 재생 어댑터' : '녹화 파일 반복 재생 어댑터';
  if (selectedDevice.value.id === 'turtlebot') return '실제 카메라 없이 위치/지도 데이터만 시각화';
  if (selectedDevice.value.id === 'conveyor') return '벨트 속도·방향·서보 값 기반 가상 모델';
  if (selectedDevice.value.id === 'gateway') return '게이트웨이 연결 진단 요약';
  return '상태 데이터 중심 장비 카드';
});

const recentEvents = computed(() => devices.value.events.slice(0, 5));
const selectedEvents = computed(() => {
  const detailEvents = selectedDetail.value?.recentEvents ?? [];
  return (detailEvents.length ? detailEvents : devices.value.events.filter((event) => event.deviceId === selectedDevice.value.id || event.source === selectedDevice.value.id)).slice(0, 4);
});
const selectedFacts = computed(() => [
  { label: '역할', value: roleLabel(selectedDevice.value.role) },
  { label: 'IP', value: selectedDevice.value.ip ?? '-' },
  { label: '연결', value: connectionLabel(selectedDevice.value.connection), tone: selectedDevice.value.connection === 'ONLINE' ? 'good' : 'warn' },
  { label: 'RTT', value: `${selectedDevice.value.rttMs} ms` },
  { label: 'Timeout / Retry', value: `${selectedDevice.value.timeoutCount} / ${selectedDevice.value.retryCount}` },
  { label: '어댑터', value: deviceMediaStatus(selectedDevice.value.id) },
]);

const turtleModel = computed<TurtleBotMapState>(() => devices.value.virtualModels.turtlebot);
const conveyorModel = computed<ConveyorModelState>(() => devices.value.virtualModels.conveyor);
const turtlePathPolyline = computed(() => turtleModel.value.path.map((point) => mapToSvgPoint(point.x, point.y).join(',')).join(' '));
const turtlePosePoint = computed(() => {
  const [x, y] = mapToSvgPoint(turtleModel.value.pose.x, turtleModel.value.pose.y);
  return { x, y, theta: turtleModel.value.pose.thetaDeg };
});
const turtleTargetPoint = computed(() => {
  if (!turtleModel.value.target) return null;
  const [x, y] = mapToSvgPoint(turtleModel.value.target.x, turtleModel.value.target.y);
  return { x, y };
});
const turtleStationPoints = computed(() => (turtleModel.value.stations ?? []).map((station) => {
  const [x, y] = mapToSvgPoint(station.x, station.y);
  return { ...station, x, y };
}));
const turtleObstacleRects = computed(() => (turtleModel.value.obstacles ?? []).map((obstacle) => {
  const [x1, y1] = mapToSvgPoint(obstacle.x, obstacle.y);
  const [x2, y2] = mapToSvgPoint(obstacle.x + obstacle.widthM, obstacle.y + obstacle.heightM);
  return {
    id: obstacle.id,
    x: Math.min(x1, x2),
    y: Math.min(y1, y2),
    width: Math.abs(x2 - x1),
    height: Math.abs(y2 - y1),
  };
}));
const activeSensorLabel = computed(() => {
  const active = conveyorModel.value.sensors.filter((sensor) => sensor.active).map((sensor) => sensor.label);
  return active.length ? active.join(', ') : '활성 센서 없음';
});

watch(
  () => devices.value.devices.map((device) => device.id).join(','),
  () => {
    if (!devices.value.devices.some((device) => device.id === selectedDeviceId.value)) {
      selectedDeviceId.value = devices.value.devices[0]?.id ?? 'dobot';
    }
  },
  { immediate: true },
);

function selectDevice(id: DeviceId) {
  selectedDeviceId.value = id;
}

function deviceImage(id: DeviceId) {
  return deviceImages[id];
}

function deviceMediaStatus(id: DeviceId) {
  const streams = devices.value.streams.filter((stream) => stream.deviceId === id);
  const detailStreams = devices.value.details[id]?.streams ?? [];
  const stream = [...detailStreams, ...streams].find((item) => item.sourceUrl) ?? [...detailStreams, ...streams][0];
  if (stream?.sourceUrl && stream.playbackMode === 'sequence') return '순차 영상 어댑터 연결';
  if (stream?.sourceUrl) return '반복 영상 어댑터 연결';
  if (id === 'turtlebot') return '가상 맵 데이터 연결';
  if (id === 'conveyor') return '가상 컨베이어 데이터 연결';
  if (id === 'gateway') return '게이트웨이 상태 수신';
  return stream ? `${transportLabel(stream.transport)} 수신` : '상태 데이터 수신';
}

function mediaUrl(sourceUrl?: string) {
  if (!sourceUrl) return '';
  try {
    return new URL(sourceUrl, normalizeBaseUrl(gatewayUrl.value)).toString();
  } catch {
    return sourceUrl;
  }
}

function normalizeBaseUrl(value: string) {
  const trimmed = value.trim().replace(/\/$/, '');
  if (/^https?:\/\//i.test(trimmed)) return `${trimmed}/`;
  return `http://${trimmed}/`;
}

function openMedia(url: string) {
  window.open(url, '_blank', 'noopener,noreferrer');
}

function mapToSvgPoint(x: number, y: number): [number, number] {
  const map = turtleModel.value.map ?? { widthM: 6, heightM: 3, resolutionM: 0.05, origin: { x: 0, y: 0 } };
  const normalizedX = clampPct(((x - map.origin.x) / Math.max(map.widthM, 0.1)) * 100);
  const normalizedY = clampPct(((y - map.origin.y) / Math.max(map.heightM, 0.1)) * 100);
  return [20 + normalizedX * 4.8, 280 - normalizedY * 2.6];
}

function clampPct(value: number) {
  return Math.min(100, Math.max(0, value));
}

function stateLabel(state: DeviceOperatingState) {
  return state;
}

function stateTone(state: DeviceOperatingState, connection?: DeviceConnectionState) {
  if (connection === 'OFFLINE' || state === 'OFFLINE' || state === 'FAULT') return 'danger';
  if (state === 'WARNING' || connection === 'DEGRADED') return 'warn';
  if (['BUSY', 'MOVING', 'STREAMING'].includes(state)) return 'blue';
  if (['READY', 'RUNNING'].includes(state)) return 'good';
  return 'neutral';
}

function streamTone(status?: DeviceStream['status']) {
  if (status === 'ERROR') return 'danger';
  if (status === 'PAUSED' || status === 'ENDED') return 'warn';
  return 'good';
}

function connectionLabel(connection: DeviceConnectionState) {
  const map: Record<DeviceConnectionState, string> = {
    ONLINE: 'ONLINE',
    DEGRADED: 'DEGRADED',
    OFFLINE: 'OFFLINE',
  };
  return map[connection];
}

function roleLabel(role: DeviceRole) {
  const map: Record<DeviceRole, string> = {
    Manipulator: 'Manipulator',
    MobileRobot: 'Mobile Robot',
    VisionCamera: 'Vision / YOLO',
    Conveyor: 'Conveyor / I/O',
    Simulation: 'Simulation',
    Gateway: 'Gateway',
  };
  return map[role];
}

function shortDeviceName(id: DeviceId) {
  const map: Record<DeviceId, string> = {
    dobot: 'Dobot',
    turtlebot: 'TurtleBot',
    realsense: 'RealSense',
    conveyor: 'Conveyor',
    robodk: 'RoboDK',
    gateway: 'Gateway',
  };
  return map[id];
}

function transportLabel(transport?: DeviceStream['transport']) {
  const map: Record<DeviceStream['transport'], string> = {
    'static-file': 'static media',
    'metadata-only': 'metadata-only',
    'websocket-frame': 'frame stream',
    hls: 'HLS',
    mjpeg: 'MJPEG',
  };
  return transport ? map[transport] : '-';
}

function eventTone(severity: DeviceEventSeverity) {
  if (severity === 'ERROR' || severity === 'CRITICAL') return 'danger';
  if (severity === 'WARN') return 'warn';
  return 'blue';
}

function eventIcon(severity: DeviceEventSeverity) {
  if (severity === 'ERROR' || severity === 'CRITICAL') return '!';
  if (severity === 'WARN') return '△';
  return 'i';
}

function formatClock(timestamp?: string) {
  if (!timestamp) return '--:--:--';
  return new Intl.DateTimeFormat('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date(timestamp));
}

function emptyDevice(): DeviceNode {
  return {
    id: 'dobot',
    name: 'Dobot Magician',
    role: 'Manipulator',
    state: 'READY',
    statusText: '스냅샷 대기',
    online: true,
    connection: 'ONLINE',
    lastUpdated: new Date().toISOString(),
    rttMs: 0,
    retryCount: 0,
    timeoutCount: 0,
  };
}
</script>

<style scoped>
.zd-devices-page {
  height: calc(100% - 86px);
  padding: 22px 28px 24px;
  display: grid;
  grid-template-rows: 58px minmax(0, 1fr);
  gap: 18px;
  color: #132653;
  background:
    radial-gradient(circle at 20% 0%, rgba(26, 112, 255, 0.045), transparent 34%),
    linear-gradient(180deg, #fbfdff 0%, #f7faff 100%);
}

.zd-devices-header {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  align-items: center;
  gap: 28px;
}

.zd-devices-header h1,
.zd-card h2,
.zd-stream-list h3,
.zd-selected-events h3 {
  margin: 0;
  font-weight: 900;
  letter-spacing: -0.04em;
  color: #0e2454;
}

.zd-devices-header h1 { font-size: 31px; }
.zd-card h2 { font-size: 18px; }
.zd-stream-list h3,
.zd-selected-events h3 { font-size: 16px; }

.zd-status-strip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 22px;
}

.zd-status-chip {
  min-width: 172px;
  height: 43px;
  padding: 0 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border: 1px solid #dce6f4;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 8px 20px rgba(26, 43, 88, 0.045);
  font-size: 15px;
  color: #40547c;
}

.zd-status-chip--wide { min-width: 245px; }
.zd-status-chip strong { font-weight: 900; }

.zd-devices-layout {
  min-height: 0;
  display: grid;
  grid-template-columns: 318px minmax(0, 1fr) 348px;
  gap: 20px;
}

.zd-left-column,
.zd-main-column,
.zd-right-column { min-height: 0; }

.zd-left-column {
  display: grid;
  grid-template-rows: 200px 260px minmax(0, 1fr);
  gap: 12px;
}

.zd-main-column {
  display: grid;
  grid-template-rows: 365px minmax(0, 1fr);
  gap: 12px;
}

.zd-card {
  min-height: 0;
  border: 1px solid #dce6f4;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 8px 22px rgba(31, 48, 85, 0.055);
}

.zd-summary-card,
.zd-comm-card,
.zd-events-card,
.zd-selected-card { padding: 16px; }

.zd-summary-list,
.zd-rtt-list,
.zd-event-list,
.zd-stream-list ul,
.zd-selected-events ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.zd-summary-list,
.zd-rtt-list,
.zd-event-list { display: grid; gap: 8px; }
.zd-summary-list { margin-top: 12px; }

.zd-summary-list li,
.zd-rtt-list li,
.zd-stream-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 13px;
  color: #263d6c;
}

.zd-summary-list span,
.zd-rtt-list span {
  display: inline-flex;
  align-items: center;
  gap: 9px;
}

.zd-summary-list strong,
.zd-rtt-list strong,
.zd-metric-list dd,
.zd-selected-facts dd,
.zd-virtual-facts dd,
.zd-source-list dd,
.zd-gateway-grid dd {
  color: #162a5b;
  font-weight: 900;
}

.zd-metric-list,
.zd-selected-facts,
.zd-virtual-facts,
.zd-source-list,
.zd-gateway-grid {
  margin: 0;
  display: grid;
  gap: 8px;
}

.zd-metric-list { margin-top: 12px; }
.zd-rtt-list { margin-top: 10px; padding-top: 10px; border-top: 1px solid #e7edf7; }

.zd-metric-list div,
.zd-selected-facts div,
.zd-virtual-facts div,
.zd-source-list div,
.zd-gateway-grid div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.zd-metric-list dt,
.zd-metric-list dd,
.zd-selected-facts dt,
.zd-selected-facts dd,
.zd-virtual-facts dt,
.zd-virtual-facts dd,
.zd-source-list dt,
.zd-source-list dd,
.zd-gateway-grid dt,
.zd-gateway-grid dd {
  margin: 0;
  font-size: 12px;
}

.zd-metric-list dt,
.zd-selected-facts dt,
.zd-virtual-facts dt,
.zd-source-list dt,
.zd-gateway-grid dt { color: #4c6089; }
.zd-source-list dd { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.zd-events-card {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) 44px;
  gap: 12px;
}

.zd-event-list,
.zd-selected-events ul {
  min-height: 0;
  overflow: auto;
  align-content: start;
}

.zd-event-list li,
.zd-selected-events li {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) 58px;
  align-items: center;
  gap: 8px;
  color: #314774;
  font-size: 12px;
}

.zd-event-list p,
.zd-selected-events p {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.zd-event-list time,
.zd-selected-events time {
  color: #627399;
  text-align: right;
  font-size: 11px;
}

.zd-event-icon {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  color: #fff;
  font-size: 11px;
  font-weight: 900;
}

.zd-event-icon--blue { background: #1477ff; }
.zd-event-icon--warn { background: #ff9900; }
.zd-event-icon--danger { background: #ff351f; }
.zd-event-dot--blue,
.zd-event-dot--warn,
.zd-event-dot--danger { width: 8px; height: 8px; border-radius: 999px; }
.zd-event-dot--blue { background: #1477ff; }
.zd-event-dot--warn { background: #ff9900; }
.zd-event-dot--danger { background: #ff351f; }

.zd-device-board {
  padding: 14px;
  display: grid;
  grid-template-rows: 56px minmax(0, 1fr);
  gap: 12px;
}

.zd-board-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 570px;
  align-items: start;
  gap: 16px;
}

.zd-board-head p,
.zd-preview-head p,
.zd-selected-head p {
  margin: 4px 0 0;
  color: #52668f;
  font-size: 12px;
}

.zd-filters {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) 150px 160px;
  gap: 10px;
}

.zd-search-box,
.zd-filters select {
  height: 36px;
  border: 1px solid #dbe5f3;
  border-radius: 8px;
  background: #fff;
}

.zd-search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  color: #53678e;
}

.zd-search-box input {
  width: 100%;
  border: 0;
  outline: 0;
  color: #142756;
  font: inherit;
  background: transparent;
}

.zd-filters select {
  padding: 0 10px;
  color: #40547a;
  font-weight: 700;
}

.zd-device-grid {
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  grid-auto-rows: minmax(126px, 1fr);
  gap: 12px;
}

.zd-device-card {
  position: relative;
  min-height: 126px;
  display: grid;
  grid-template-columns: 104px minmax(0, 1fr);
  gap: 12px;
  padding: 12px;
  border: 1px solid #dce5f2;
  border-radius: 10px;
  background: linear-gradient(180deg, #fff 0%, #fbfdff 100%);
  cursor: pointer;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
}

.zd-device-card:hover,
.zd-device-card:focus-visible {
  transform: translateY(-1px);
  border-color: rgba(17, 181, 49, 0.42);
  outline: none;
}

.zd-device-card--selected {
  border-color: #14b932;
  box-shadow: inset 0 0 0 1px rgba(20, 185, 50, 0.5), 0 10px 22px rgba(20, 185, 50, 0.1);
}

.zd-device-card figure {
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e2ebf6;
  border-radius: 8px;
  background: #f8fbff;
}

.zd-device-card img {
  max-width: 88px;
  max-height: 86px;
  object-fit: contain;
  filter: drop-shadow(0 8px 9px rgba(16, 31, 67, 0.1));
}

.zd-device-card__body {
  min-width: 0;
  display: grid;
  align-content: center;
  gap: 7px;
}

.zd-device-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.zd-device-card h3 {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 16px;
  color: #10275d;
}

.zd-device-card p,
.zd-device-card small {
  margin: 0;
  color: #475d88;
  font-size: 12px;
}

.zd-device-card dl {
  margin: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.zd-device-card dl div {
  display: grid;
  gap: 2px;
  padding: 6px 8px;
  border-radius: 7px;
  background: #f3f7fc;
}

.zd-device-card dt,
.zd-device-card dd { margin: 0; font-size: 11px; }
.zd-device-card dt { color: #6a7a9b; }
.zd-device-card dd { color: #132653; font-weight: 900; }

.zd-selected-mark {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #12ad2e;
  color: #fff;
  font-weight: 900;
}

.zd-preview-board {
  padding: 14px;
  display: grid;
  grid-template-rows: 58px minmax(0, 1fr);
  gap: 12px;
}

.zd-preview-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: start;
}

.zd-preview-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.zd-preview-body {
  min-height: 0;
  border: 1px solid #dfe8f4;
  border-radius: 10px;
  background: #f8fbff;
  overflow: hidden;
}

.zd-video-panel,
.zd-virtual-panel,
.zd-gateway-panel,
.zd-no-preview {
  height: 100%;
  padding: 14px;
}

.zd-video-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  grid-template-rows: 34px minmax(0, 1fr);
  gap: 12px;
}

.zd-video-panel video {
  grid-row: 1 / -1;
  width: 100%;
  height: 100%;
  min-height: 240px;
  border-radius: 8px;
  background: #0d1930;
  object-fit: contain;
}

.zd-video-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  color: #314774;
  font-size: 12px;
}

.zd-sequence-chip {
  padding: 4px 8px;
  border-radius: 999px;
  background: #eaf2ff;
  color: #0069ff;
  font-weight: 900;
}

.zd-source-list { align-content: start; }

.zd-virtual-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: 14px;
}

.zd-turtle-map {
  width: 100%;
  height: 100%;
  min-height: 260px;
  border-radius: 10px;
  background: #eef5fd;
}

.zd-turtle-map text {
  fill: #1a315f;
  font-size: 12px;
  font-weight: 800;
}

.zd-virtual-facts {
  align-content: start;
  padding: 14px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #e1eaf6;
}

.zd-conveyor-model {
  position: relative;
  min-height: 260px;
  border-radius: 12px;
  background: linear-gradient(180deg, #eef5fd, #f8fbff);
  border: 1px solid #dbe6f4;
  overflow: hidden;
}

.zd-conveyor-belt {
  position: absolute;
  left: 42px;
  right: 42px;
  top: 112px;
  height: 78px;
  border-radius: 22px;
  border: 8px solid #263b65;
  background: repeating-linear-gradient(90deg, #93a4c1 0 22px, #7f91b0 22px 44px);
  box-shadow: inset 0 0 0 5px rgba(255,255,255,0.28);
}

.zd-conveyor-belt span {
  display: none;
}

.zd-conveyor-box {
  position: absolute;
  top: 120px;
  width: 50px;
  height: 42px;
  margin-left: -25px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: linear-gradient(135deg, #d9a65d, #f1c982);
  color: #583b0c;
  font-size: 10px;
  font-weight: 900;
  box-shadow: 0 8px 12px rgba(57, 43, 18, 0.18);
}

.zd-conveyor-box--detected { outline: 4px solid #12b532; }

.zd-conveyor-sensor {
  position: absolute;
  top: 202px;
  width: 56px;
  margin-left: -28px;
  padding: 5px 0;
  border-radius: 999px;
  background: #e4ebf5;
  color: #5b6c8b;
  text-align: center;
  font-size: 10px;
  font-weight: 900;
}

.zd-conveyor-sensor--active { background: #12b532; color: #fff; }

.zd-servo {
  position: absolute;
  top: 36px;
  width: 70px;
  margin-left: -35px;
  display: grid;
  justify-items: center;
  gap: 4px;
}

.zd-servo span {
  width: 12px;
  height: 74px;
  display: block;
  border-radius: 999px;
  transform-origin: bottom center;
  background: #ff7a1a;
  box-shadow: 0 5px 12px rgba(255, 122, 26, 0.25);
}

.zd-servo small {
  color: #8a4a0c;
  font-weight: 900;
}

.zd-belt-arrow {
  position: absolute;
  right: 52px;
  top: 56px;
  color: #0878ff;
  font-size: 52px;
}

.zd-conveyor-model--reverse .zd-belt-arrow { left: 52px; right: auto; }

.zd-gateway-panel,
.zd-no-preview {
  display: grid;
  place-items: center;
}

.zd-gateway-grid {
  width: min(520px, 100%);
  padding: 20px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #e1eaf6;
}

.zd-no-preview {
  align-content: center;
  gap: 10px;
  color: #52668f;
  text-align: center;
}

.zd-no-preview img {
  max-width: 150px;
  max-height: 130px;
  object-fit: contain;
}

.zd-selected-card {
  height: 100%;
  display: grid;
  grid-template-rows: auto 130px auto 120px minmax(0, 1fr);
  gap: 14px;
}

.zd-selected-head {
  display: grid;
  grid-template-columns: 106px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  border-bottom: 1px solid #e5edf7;
  padding-bottom: 14px;
}

.zd-selected-head figure {
  margin: 0;
  height: 108px;
  border: 1px solid #dae5f3;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
}

.zd-selected-head img { max-width: 92px; max-height: 88px; object-fit: contain; }
.zd-selected-head h3 { margin: 0 0 8px; font-size: 21px; color: #10275d; }

.zd-selected-facts {
  padding-bottom: 14px;
  border-bottom: 1px solid #e5edf7;
}

.zd-selected-facts dd { text-align: right; }

.zd-stream-list {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 8px;
  min-height: 0;
}

.zd-stream-list ul {
  display: grid;
  align-content: start;
  gap: 8px;
  overflow: auto;
}

.zd-stream-list li {
  padding: 8px 10px;
  border-radius: 8px;
  background: #f5f8fd;
}

.zd-stream-list span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.zd-stream-list strong { color: #0878ff; font-size: 11px; }

.zd-selected-events {
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 8px;
}

.zd-selected-events ul { display: grid; gap: 10px; }

.zd-test-button,
.zd-primary-action,
.zd-secondary-action {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 7px;
  font-weight: 900;
  cursor: pointer;
  transition: filter 0.16s ease;
}

.zd-test-button:hover,
.zd-primary-action:hover,
.zd-secondary-action:hover { filter: brightness(0.96) saturate(0.95); }

.zd-test-button {
  border: 1px solid #14b531;
  background: #fff;
  color: #12a42d;
}

.zd-primary-action {
  border: 0;
  background: #0878ff;
  color: #fff;
}

.zd-secondary-action {
  border: 1px solid #dae4f2;
  background: #fafdff;
  color: #10275d;
}

.zd-dot {
  width: 11px;
  height: 11px;
  border-radius: 999px;
  display: inline-block;
  flex: none;
}

.zd-dot--good { background: #11b531; }
.zd-dot--blue { background: #1477ff; }
.zd-dot--muted { background: #8c98ac; }
.zd-dot--warn { background: #ff9900; }
.zd-dot--danger { background: #ff351f; }
.zd-dot--offline { background: #7f8da3; }

.zd-check,
.zd-clock,
.zd-warning {
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-weight: 900;
}

.zd-check { background: #12b532; color: #fff; }
.zd-warning { background: #ff9800; color: #fff; }
.zd-clock { color: #344f87; border: 1px solid #91a4c8; }

.zd-state-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-width: 56px;
  height: 23px;
  padding: 0 10px;
  border-radius: 6px;
  border: 1px solid transparent;
  font-size: 12px;
  font-weight: 900;
  line-height: 1;
  white-space: nowrap;
}

.zd-state-badge--good { color: #089726; background: #eaf9ef; border-color: #cbefd2; }
.zd-state-badge--blue { color: #0069ff; background: #eaf2ff; border-color: #cde0ff; }
.zd-state-badge--warn { color: #b56b00; background: #fff5df; border-color: #ffe0a1; }
.zd-state-badge--danger { color: #d51f0f; background: #fff0ee; border-color: #ffc9c2; }
.zd-state-badge--neutral { color: #4e5d76; background: #f3f6fa; border-color: #dce4ef; }

.zd-text-good { color: #0aa82b !important; }
.zd-text-warn { color: #c27400 !important; }
.zd-text-danger { color: #ee2515 !important; }

.zd-empty-card,
.zd-empty-row {
  color: #6c7d9e;
  font-size: 13px;
}

@media (max-width: 1300px) {
  .zd-devices-page { padding: 18px; }
  .zd-devices-layout { grid-template-columns: 292px minmax(0, 1fr) 320px; gap: 14px; }
  .zd-board-head { grid-template-columns: 1fr; grid-template-rows: auto auto; }
  .zd-filters { grid-template-columns: 1fr 140px 140px; }
  .zd-device-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .zd-video-panel,
  .zd-virtual-panel { grid-template-columns: 1fr; }
}
</style>
