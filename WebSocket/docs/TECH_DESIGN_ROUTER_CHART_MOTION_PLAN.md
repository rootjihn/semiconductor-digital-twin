# P0 기술 설계: Vue Router / Chart.js / 모션 라이브러리 적용 계획

## 1. 목적

`WebSocket` 대시보드를 MVP1 범위 안에서 안전하게 정리한다. 목표는 라우팅 구조를 명확히 하고, Chart.js 사용 범위를 텔레메트리/상세 화면의 일부 지표로 제한하며, 현재 SVG/CSS 기반 공정 플로우와 GSAP 중심 모션을 유지해 과한 라이브러리 확장을 막는 것이다.

이 문서는 구현 전에 작업 범위, 금지 범위, 단계별 순서, 검증 명령, 롤백 기준을 고정하기 위한 기술 설계서다.

## 2. 현재 확인된 상태

- 프로젝트 루트: `/home/quincy/HDD/Throughline_PJT/WebSocket`
- 프레임워크: Vue 3 + TypeScript + Vite
- 주요 진입점:
  - `src/main.ts`
  - `src/App.vue`
  - `src/components/MainLanding.vue`
  - `src/components/MetricsChart.vue`
  - `src/lib/dashboardClient.ts`
  - `shared/telemetry.ts`
- 게이트웨이 기본 URL: `VITE_GATEWAY_URL` 우선, 없으면 `http://localhost:8765`
- 게이트웨이 계약:
  - HTTP: `/api/health`, `/api/snapshot`, `/api/events`, `/api/commands/:command`
  - WebSocket: `/ws`
  - 메시지 타입: `snapshot`, `event`, `command_result`
- 공용 상태 모델:
  - `ConnectionState = 'mock' | 'connecting' | 'online' | 'degraded' | 'offline'`
  - `LineState = 'RUNNING' | 'PAUSED' | 'STOPPED' | 'FAULT'`
  - `PROCESS_STAGES = infeed, conveyor, vision, pick, outfeed`
- `package-lock.json` 기준으로 `chart.js`, `gsap`, `pixi.js` 의존성이 존재한다.
- 현재 화면 구조는 `App.vue`에 많은 상태/페이지/유틸/템플릿이 집중되어 있어 라우터 도입 시 우선 분리가 필요하다.

## 3. 설계 원칙

1. 웹 앱은 ROS2, Modbus, 로봇 SDK를 직접 호출하지 않는다.
   - 모든 실시간 상태와 명령은 Gateway HTTP/WebSocket 계약을 통한다.
2. MVP1은 실제 장비 연동보다 UI 정보구조, mock snapshot, command payload 생성, 안전 UX를 우선한다.
3. 기존 한국어 라벨, 상태 매핑, 공정 단계 명칭은 유지한다.
4. `Chart.js`는 텔레메트리/상세 지표의 일부에만 사용한다.
   - 전체 공정 플로우, 랜딩 히어로, 장비 카드, 상태 배지는 Chart.js로 만들지 않는다.
5. 모션은 현재 SVG/CSS/GSAP 기반을 우선 사용한다.
   - 새 모션 라이브러리는 MVP1에서 추가하지 않는다.
   - `pixi.js`는 MVP1에서 사용하지 않으며, 필요성이 검증되기 전까지 신규 구현에 투입하지 않는다.
6. 위험 명령은 즉시 실행하지 않고 확인 UI를 거친다.
   - 대상: `process.stop`, `process.reset_error`, `robot.home`
7. 구현은 라우터/뷰 분리 → 상태 주입 → 차트 제한 → 모션 정리 → 검증 순서로 진행한다.

## 4. 허용 수정 경로

구현 작업자는 아래 경로 안에서만 수정한다.

- `WebSocket/package.json`
- `WebSocket/package-lock.json`
- `WebSocket/src/main.ts`
- `WebSocket/src/App.vue`
- `WebSocket/src/router/**`
- `WebSocket/src/views/**`
- `WebSocket/src/components/**`
- `WebSocket/src/composables/**`
- `WebSocket/src/lib/**`
- `WebSocket/src/styles.css`
- `WebSocket/shared/**`
- `WebSocket/docs/**`

단, `shared/**`는 타입 또는 mock 데이터 정리에 한정한다.

## 5. 금지 수정 경로와 금지 작업

- `node_modules/**` 직접 수정 금지
- `dist/**` 직접 수정 금지
- 게이트웨이 계약을 깨는 서버 API 변경 금지
  - `server/index.ts`는 라우터/프런트 구조 변경 때문에 수정하지 않는다.
  - smoke test 실패 원인이 명확한 계약 불일치일 때만 별도 승인 후 수정한다.
- ROS2, Modbus, 로봇 SDK 직접 호출 코드 추가 금지
- React 기반 라우팅/상태관리 패턴 도입 금지
- Chart.js로 공정 플로우 전체를 그리는 방식 금지
- MVP1에서 `pixi.js` 기반 캔버스 씬 신규 구현 금지
- 위험 명령을 확인 없이 실행하는 버튼 추가 금지

## 6. 라우팅 설계

### 6.1 의존성

`vue-router`가 없으면 추가한다.

```bash
npm install vue-router@4
```

이미 설치되어 있으면 버전을 확인하고 불필요한 재설치를 피한다.

### 6.2 라우터 파일

신규 파일:

- `src/router/index.ts`

권장 구조:

```ts
import { createRouter, createWebHistory } from 'vue-router';

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
    { path: '/overview', name: 'overview', component: () => import('../views/OverviewView.vue') },
    { path: '/flow', name: 'flow', component: () => import('../views/FlowView.vue') },
    { path: '/camera', name: 'camera', component: () => import('../views/CameraView.vue') },
    { path: '/robot', name: 'robot', component: () => import('../views/RobotView.vue') },
    { path: '/comm', name: 'comm', component: () => import('../views/CommView.vue') },
    { path: '/history', name: 'history', component: () => import('../views/HistoryView.vue') },
    { path: '/telemetry', name: 'telemetry', component: () => import('../views/TelemetryView.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
});
```

### 6.3 `main.ts`

`router`를 등록한다.

```ts
import { createApp } from 'vue';
import App from './App.vue';
import { router } from './router';
import './styles.css';

createApp(App).use(router).mount('#app');
```

### 6.4 `App.vue`의 역할 축소

`App.vue`는 앱 셸과 공통 상태 소유자로 축소한다.

유지할 책임:

- Gateway URL 입력/연결/새로고침/Mock 전환
- WebSocket 연결 상태 관리
- `DashboardSnapshot`, events, command result 상태 보유
- 공통 헤더/네비게이션/배너 표시
- `RouterView`에 필요한 상태 전달

제거하거나 분리할 책임:

- 개별 페이지 템플릿
- 공정 플로우 상세 UI
- 카메라/로봇/통신/히스토리 화면 템플릿
- 큰 유틸 묶음

### 6.5 상태 전달 방식

MVP1에서는 Pinia 같은 전역 상태 라이브러리를 추가하지 않는다.

권장안:

1. `App.vue`에서 `provide`로 dashboard context 제공
2. 각 view에서 `inject`로 읽기
3. 타입은 `src/composables/useDashboardContext.ts` 또는 `src/lib/dashboardContext.ts`로 분리

예시 책임:

- `snapshot`
- `events`
- `connectionState`
- `gatewayUrl`
- `sendCommand(command)`
- `refreshSnapshot()`
- `useMockMode()`

Pinia 도입은 라우터 분리 후 상태가 복잡해질 때 별도 P1 작업으로 판단한다.

## 7. View 분리 계획

### 7.1 HomeView

파일: `src/views/HomeView.vue`

내용:

- `MainLanding.vue` 유지
- 공정 6개 노드 프리뷰 유지
- 상세 화면으로 이동하는 링크는 `<RouterLink>` 사용
- 기존 SVG/CSS/GSAP 모션 유지

### 7.2 OverviewView

파일: `src/views/OverviewView.vue`

내용:

- 라인 상태 요약
- Gateway 상태 요약
- 핵심 KPI 카드
- 최근 알람/이벤트 일부
- 공정 단계 요약

Chart.js는 여기서 기본 사용하지 않는다. 필요하면 아주 작은 요약 차트 1개만 허용하되, 기본 설계는 `/telemetry`로 분리한다.

### 7.3 FlowView

파일: `src/views/FlowView.vue`

내용:

- `PROCESS_STAGES` 기반 공정 플로우
- 상태 배지/설비 상태 표시
- 선택한 단계의 설명과 관련 장비 표시

구현 방식:

- SVG/CSS 기반 유지
- `Chart.js` 미사용
- `pixi.js` 미사용

### 7.4 CameraView

파일: `src/views/CameraView.vue`

내용:

- Vision/camera 상태
- inspection 결과 요약
- 정상/불량 카운트
- 마지막 이벤트

실제 이미지 스트림은 MVP1 범위 밖이다. mock placeholder만 둔다.

### 7.5 RobotView

파일: `src/views/RobotView.vue`

내용:

- 로봇 상태
- 현재 동작/홈 상태/오류 상태
- `robot.home` 명령 버튼

`robot.home`은 확인 모달을 거쳐야 한다.

### 7.6 CommView

파일: `src/views/CommView.vue`

내용:

- Gateway/PLC/Modbus/Robot bridge 상태 요약
- 연결 상태별 라벨
- refresh 명령

웹 앱에서 Modbus 직접 연결 코드를 추가하지 않는다.

### 7.7 HistoryView

파일: `src/views/HistoryView.vue`

내용:

- `events` 목록
- command result 목록
- alarm 목록
- 필터는 MVP1에서는 간단한 상태/키워드 필터만 허용

### 7.8 TelemetryView

파일: `src/views/TelemetryView.vue`

내용:

- `MetricsChart.vue`를 사용하는 주 화면
- cycle time, good/reject count, throughput 등 일부 지표만 선그래프로 표시
- 나머지는 카드/표로 표시

Chart.js 사용 범위를 이 파일과 `MetricsChart.vue` 중심으로 제한한다.

## 8. Chart.js 적용 계획

### 8.1 유지할 컴포넌트

- `src/components/MetricsChart.vue`

### 8.2 변경 방향

- `MetricsChart.vue`는 순수 차트 컴포넌트로 유지한다.
- props는 `snapshot` 또는 필요한 `metrics`만 받는다.
- DOM 생성/해제는 `onMounted`, `watch`, `onBeforeUnmount`에서 명확히 처리한다.
- 차트 인스턴스 중복 생성 방지 로직을 유지한다.
- 색상은 `styles.css`의 CSS 변수와 맞춘다.

### 8.3 사용 제한

허용:

- `/telemetry` 상세 화면의 cycle time trend
- `/telemetry` 상세 화면의 good/reject count trend
- 필요 시 `/overview`의 축소 KPI 차트 1개

금지:

- 공정 플로우 전체 구현
- 장비 상태 카드 구현
- 알람/이벤트 목록 구현
- 랜딩 페이지 히어로 구현

### 8.4 데이터 정책

MVP1에서는 mock snapshot 또는 gateway snapshot의 `metrics`를 사용한다.

실시간 히스토리 배열이 없으면 다음 순서로 처리한다.

1. 현재 `metrics` 기반 단일 시점 표시
2. 클라이언트에서 최근 N개 snapshot을 메모리에 축적
3. 서버 저장형 히스토리는 MVP2 이후로 미룬다.

## 9. 모션 라이브러리 적용 계획

### 9.1 GSAP

현재 의존성에 `gsap`이 존재하므로 MVP1 모션은 GSAP + CSS transition으로 제한한다.

허용 범위:

- 랜딩 히어로 진입 애니메이션
- 공정 노드 hover/selected 강조
- 상태 변화 시 짧은 pulse
- 메뉴 dropdown 전환

금지 범위:

- 상태가 바뀔 때마다 과도한 timeline 재생
- 실시간 WebSocket 메시지마다 전체 화면 reflow를 유발하는 모션
- 접근성 설정을 무시하는 반복 애니메이션

### 9.2 CSS transition

간단한 hover, chip, panel, dropdown 전환은 CSS transition을 우선한다.

### 9.3 Pixi.js

`pixi.js`는 현재 lockfile에 존재하지만 MVP1에서 사용하지 않는다.

사용 보류 사유:

- 공정 플로우는 SVG/CSS로 충분하다.
- canvas 기반 씬은 테스트/접근성/유지보수 비용이 크다.
- 실시간 설비 대시보드의 우선순위는 안정적인 상태 표현과 명령 안전성이다.

Pixi.js는 다음 조건을 모두 만족할 때 별도 P2 검토로 넘긴다.

- SVG/CSS로 표현하기 어려운 다수 객체 실시간 애니메이션 필요
- 60fps canvas 렌더링 요구가 명확함
- 접근성 대체 텍스트/상태 패널을 함께 제공할 수 있음

## 10. 명령 UX 안전 정책

명령 분류:

- 일반 명령:
  - `process.start`
  - `process.pause`
  - `process.resume`
  - `system.refresh`
- 위험 명령:
  - `process.stop`
  - `process.reset_error`
  - `robot.home`

위험 명령 처리 순서:

1. 버튼 클릭
2. 확인 모달 표시
3. 명령명, 예상 영향, 현재 라인 상태 표시
4. 사용자가 확인
5. `sendGatewayCommand(command)` 호출
6. command result 표시
7. event/history에 결과 반영

실패 시:

- 실패 chip 표시
- 최근 이벤트에 실패 이유 표시
- 버튼은 재시도 가능 상태로 복구

## 11. 단계별 구현 순서

### Phase 0. 기준점 확인

작업 전 실행:

```bash
cd /home/quincy/HDD/Throughline_PJT/WebSocket
git status --short
npm run build
npm run smoke
```

통과하지 않으면 구현 전에 실패 원인을 기록한다. 기존 실패는 새 작업의 실패와 구분한다.

### Phase 1. 라우터 최소 도입

1. `vue-router@4` 설치 여부 확인
2. 없으면 설치
3. `src/router/index.ts` 생성
4. `src/main.ts`에 router 등록
5. `App.vue`에 `<RouterView />` 배치
6. 기존 active page 상태는 라우터 경로와 동기화하거나 제거

검증:

```bash
npm run build
```

### Phase 2. App.vue 분리

1. `App.vue`에서 공통 shell/header/gateway 상태만 남김
2. 기존 페이지별 템플릿을 `src/views/**`로 이동
3. 공통 유틸은 `src/lib` 또는 `src/composables`로 분리
4. 라벨 함수는 한 곳에서 export

검증:

```bash
npm run build
npm run smoke
```

### Phase 3. Chart.js 사용 범위 정리

1. `MetricsChart.vue`를 `/telemetry` 중심으로 배치
2. overview에는 KPI 카드 중심 구성
3. 차트가 필요한 경우 props와 lifecycle을 단순화
4. snapshot 히스토리 축적 로직이 필요하면 composable로 분리

검증:

```bash
npm run build
```

수동 확인 항목:

- `/telemetry`에서 차트가 표시됨
- 다른 화면이 Chart.js에 의존하지 않음
- 화면 전환 후 차트 인스턴스 누수가 없음

### Phase 4. 모션 정리

1. 랜딩/공정 플로우 모션은 기존 CSS/GSAP 유지
2. 불필요한 반복 모션 제거
3. hover/active/selected 상태 스타일 정리
4. `prefers-reduced-motion` 대응 확인

검증:

```bash
npm run build
```

수동 확인 항목:

- hover/selected 상태가 자연스럽게 보임
- 라우트 이동 시 과한 깜빡임 없음
- reduced motion 환경에서 핵심 정보가 사라지지 않음

### Phase 5. 안전 명령 UX 연결

1. 위험 명령 확인 모달 추가
2. `sendGatewayCommand` 결과 표시 통일
3. 명령 실패/거절 상태 표시
4. event/history에 command result 노출

검증:

```bash
npm run build
npm run smoke
```

수동 확인 항목:

- `process.stop`, `process.reset_error`, `robot.home`은 확인 없이 실행되지 않음
- 일반 명령은 즉시 실행 가능
- 실패 응답이 사용자에게 보임

### Phase 6. 최종 회귀 확인

```bash
cd /home/quincy/HDD/Throughline_PJT/WebSocket
npm run build
npm run smoke
git status --short
git diff --stat
```

필요 시 로컬 화면 확인:

```bash
npm run dev -- --host 127.0.0.1
```

별도 터미널에서:

```bash
npm run gateway
```

브라우저 확인 경로:

- `/`
- `/overview`
- `/flow`
- `/camera`
- `/robot`
- `/comm`
- `/history`
- `/telemetry`

## 12. 롤백 기준

즉시 롤백:

- `npm run build` 실패
- `npm run smoke` 실패가 새 변경에서 발생
- Gateway 계약이 깨짐
- WebSocket snapshot 수신이 중단됨
- 위험 명령이 확인 없이 실행됨
- 라우트 이동 후 주요 상태가 사라짐

부분 롤백 순서:

1. 마지막 phase 변경만 되돌림
2. 라우터 자체는 유지 가능한지 확인
3. 차트/모션 변경은 개별 컴포넌트 단위로 되돌림
4. 여전히 실패하면 `git diff` 기준 전체 작업 되돌림

권장 명령:

```bash
git diff --stat
git diff -- src/main.ts src/App.vue src/router src/views src/components src/composables src/lib src/styles.css package.json package-lock.json
```

되돌릴 때는 사용자 승인 후 다음 중 하나를 사용한다.

```bash
git checkout -- <path>
```

또는 아직 커밋 전이면 승인 후 관련 파일만 선택적으로 복원한다.

## 13. Codex 구현 지시문 초안

아래 지시문은 구현 작업자에게 그대로 전달할 수 있다.

```text
작업 디렉터리: /home/quincy/HDD/Throughline_PJT/WebSocket

목표:
Vue 3 + TypeScript 대시보드에 vue-router 기반 페이지 구조를 도입하고, App.vue를 공통 shell/state owner로 축소한다. Chart.js는 /telemetry 상세 화면의 일부 지표에만 사용하고, 공정 플로우/랜딩/상태카드는 기존 SVG/CSS/GSAP 방식으로 유지한다.

허용 경로:
package.json, package-lock.json, src/main.ts, src/App.vue, src/router/**, src/views/**, src/components/**, src/composables/**, src/lib/**, src/styles.css, shared/**, docs/**

금지:
node_modules/dist 직접 수정 금지. 서버 API 계약 변경 금지. 웹에서 ROS2/Modbus/로봇 SDK 직접 호출 금지. Pixi.js 신규 구현 금지. Chart.js로 공정 플로우 전체를 구현하지 말 것. process.stop/process.reset_error/robot.home은 확인 모달 없이 실행하지 말 것.

구현 순서:
1. git status 확인
2. npm run build, npm run smoke 기준점 확인
3. vue-router@4 설치 여부 확인 후 없으면 추가
4. src/router/index.ts 생성
5. src/main.ts에 router 등록
6. App.vue를 shell/header/gateway 상태/RouterView 중심으로 축소
7. 기존 화면을 HomeView, OverviewView, FlowView, CameraView, RobotView, CommView, HistoryView, TelemetryView로 분리
8. MetricsChart.vue는 TelemetryView 중심으로 사용
9. 위험 명령 확인 UI 유지/추가
10. npm run build, npm run smoke 실행
11. git diff --stat과 핵심 diff를 보고

검증 명령:
npm run build
npm run smoke
git status --short
git diff --stat

중단 조건:
기존 Gateway 계약을 바꿔야만 진행 가능한 경우, build/smoke가 기존 원인 없이 실패하는 경우, 위험 명령 안전 정책을 만족하지 못하는 경우 즉시 중단하고 보고한다.
```

## 14. 완료 기준

- 라우트별 화면 파일이 분리되어 있다.
- `App.vue`가 거대한 단일 페이지 구현이 아니라 공통 shell과 상태 소유자로 축소되어 있다.
- `/telemetry`에서만 Chart.js 중심 차트가 사용된다.
- 랜딩/공정 플로우는 SVG/CSS/GSAP 기반으로 유지된다.
- 위험 명령은 확인 UI를 거친다.
- `npm run build`가 통과한다.
- `npm run smoke`가 통과한다.
- 변경 diff가 허용 경로 안에만 있다.
