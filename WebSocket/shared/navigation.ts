export type AppRouteName = 'home' | 'devices' | 'simulation' | 'telemetry' | 'servers';

export interface AppRouteMeta {
  name: AppRouteName;
  path: string;
  label: string;
  eyebrow: string;
  title: string;
  description: string;
}

export const ALL_APP_ROUTES: AppRouteMeta[] = [
  {
    name: 'home',
    path: '/',
    label: '대시보드',
    eyebrow: 'Dashboard',
    title: 'ZDnix 대시보드',
    description: 'Gateway, 라인, 장비 상태 요약',
  },
  {
    name: 'devices',
    path: '/devices',
    label: '장비',
    eyebrow: 'Devices',
    title: '장비 상태',
    description: 'MockModbusAdapter 기반 장비·통신·영상 상태',
  },
  {
    name: 'simulation',
    path: '/simulation',
    label: '공정',
    eyebrow: 'Process',
    title: '공정 흐름',
    description: '후공정 단계 흐름과 현재 담당 장비',
  },
  {
    name: 'telemetry',
    path: '/telemetry',
    label: '알림',
    eyebrow: 'Alerts / Log',
    title: '알림 / 로그',
    description: '최근 WARN/ERROR와 Gateway 이벤트 로그',
  },
  {
    name: 'servers',
    path: '/servers',
    label: '진단',
    eyebrow: 'Gateway Diagnostics',
    title: '관리자 진단',
    description: 'Gateway, WebSocket, Adapter 상태 진단',
  },
];

export const APP_ROUTES: AppRouteMeta[] = ALL_APP_ROUTES.filter((route) =>
  ['home', 'devices', 'simulation'].includes(route.name),
);

export const ADMIN_ROUTES: AppRouteMeta[] = ALL_APP_ROUTES.filter((route) =>
  ['telemetry', 'servers'].includes(route.name),
);

export const APP_ROUTE_MAP: Record<AppRouteName, AppRouteMeta> = Object.fromEntries(
  ALL_APP_ROUTES.map((route) => [route.name, route]),
) as Record<AppRouteName, AppRouteMeta>;
