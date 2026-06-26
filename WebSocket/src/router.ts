import { createRouter, createWebHistory } from 'vue-router';

export const dashboardRouteNames = ['home', 'overview', 'flow', 'camera', 'robot', 'comm', 'history'] as const;

export type DashboardRouteName = (typeof dashboardRouteNames)[number];

const routes = [
  { path: '/', name: 'home', component: { template: '<div />' } },
  { path: '/overview', name: 'overview', component: { template: '<div />' } },
  { path: '/flow', name: 'flow', component: { template: '<div />' } },
  { path: '/camera', name: 'camera', component: { template: '<div />' } },
  { path: '/robot', name: 'robot', component: { template: '<div />' } },
  { path: '/comm', name: 'comm', component: { template: '<div />' } },
  { path: '/history', name: 'history', component: { template: '<div />' } },
  { path: '/:pathMatch(.*)*', redirect: { name: 'home' } },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});