import { createRouter, createWebHistory } from 'vue-router'
import nbaRoutes from '@/features/nba/routes'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/teams' },
    ...nbaRoutes,
  ],
})

export default router
