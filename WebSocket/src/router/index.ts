import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
import HomeGraphPage from '../pages/HomeGraphPage.vue';
import DevicesPage from '../pages/DevicesPage.vue';
import SimulationPage from '../pages/SimulationPage.vue';
import TelemetryPage from '../pages/TelemetryPage.vue';
import ServersPage from '../pages/ServersPage.vue';
import { ALL_APP_ROUTES, type AppRouteName } from '../../shared/navigation';

export type DashboardRouteName = AppRouteName;

const routeComponentMap: Record<AppRouteName, RouteRecordRaw['component']> = {
  home: HomeGraphPage,
  devices: DevicesPage,
  simulation: SimulationPage,
  telemetry: TelemetryPage,
  servers: ServersPage,
};

const routes: RouteRecordRaw[] = ALL_APP_ROUTES.map<RouteRecordRaw>((route) => ({
  path: route.path,
  name: route.name,
  component: routeComponentMap[route.name]!,
}));

routes.push({
  path: '/:pathMatch(.*)*',
  redirect: { name: 'home' },
});

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

export default router;
