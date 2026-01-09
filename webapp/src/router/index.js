import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'
import DashboardView from '../views/DashboardView.vue'
import ServerSettingsView from '../views/ServerSettingsView.vue'
import AuthView from '../views/AuthView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/auth', name: 'auth', component: AuthView },
    { path: '/', name: 'dashboard', component: DashboardView, meta: { requiresAuth: true } },
    { path: '/servers/:id/settings', name: 'server-settings', component: ServerSettingsView, meta: { requiresAuth: true } },
  ]
})

router.beforeEach(async (to) => {
  const userStore = useUserStore()
  const authenticated = await userStore.getSession()
  
  // Redirect authenticated users away from auth page
  if (to.name === 'auth' && authenticated) {
    return '/'
  }
  
  // Redirect unauthenticated users to auth page
  if (to.meta.requiresAuth && !authenticated) {
    return '/auth'
  }
})

export default router
