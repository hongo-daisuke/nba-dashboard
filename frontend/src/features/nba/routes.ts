import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/teams',
    component: () => import('./views/TeamsView.vue'),
  },
  {
    path: '/players',
    component: () => import('./views/PlayersView.vue'),
  },
  {
    path: '/players/:playerId',
    component: () => import('./views/PlayerDetailView.vue'),
  },
  {
    path: '/games',
    component: () => import('./views/GamesView.vue'),
  },
  {
    path: '/games/:gameId',
    component: () => import('./views/GameDetailView.vue'),
  },
  {
    path: '/standings',
    component: () => import('./views/StandingsView.vue'),
  },
  {
    path: '/leaders',
    component: () => import('./views/LeadersView.vue'),
  },
]

export default routes
