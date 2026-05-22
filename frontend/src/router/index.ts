import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/views/DashboardView.vue'),
      redirect: '/sessions',
      children: [
        { path: 'overview',  name: 'overview',  component: () => import('@/views/tabs/OverviewTab.vue')  },
        { path: 'events',    name: 'events',    component: () => import('@/views/tabs/EventsTab.vue')    },
        { path: 'sessions',  name: 'sessions',  component: () => import('@/views/tabs/SessionsTab.vue')  },
      ],
    },
    {
      path: '/session/:id',
      component: () => import('@/views/SessionDetailView.vue'),
    },
    { path: '/:pathMatch(.*)*', redirect: '/sessions' },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.token) return '/login'
})

export default router
