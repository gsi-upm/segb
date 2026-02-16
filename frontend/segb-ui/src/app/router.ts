import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '@/app/layout/AppLayout.vue'
import ReportsView from '@/features/reports/ReportsView.vue'
import KgGraphView from '@/features/kg/KgGraphView.vue'
import InsertLogView from '@/features/logs/InsertLogView.vue'
import ModificationsView from '@/features/modifications/ModificationsView.vue'
import QueryWorkbenchView from '@/features/query/QueryWorkbenchView.vue'
import SharedContextView from '@/features/shared-context/SharedContextView.vue'
import HealthView from '@/features/health/HealthView.vue'
import SessionView from '@/features/session/SessionView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', redirect: '/session' },
    {
      path: '/',
      component: AppLayout,
      children: [
        { path: '', redirect: '/reports' },
        { path: 'reports', component: ReportsView },
        { path: 'kg-graph', component: KgGraphView },
        { path: 'logs/insert', component: InsertLogView },
        { path: 'logs/modifications', component: ModificationsView },
        { path: 'query', component: QueryWorkbenchView },
        { path: 'shared-context', component: SharedContextView },
        { path: 'health', component: HealthView },
        { path: 'session', component: SessionView },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/reports' },
  ],
})

export default router
