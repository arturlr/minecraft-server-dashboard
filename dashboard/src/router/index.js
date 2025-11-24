import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'
import SimpleLayout from '../layouts/SimpleLayout.vue'
  
import HomeView from '../views/HomeView.vue'
import AuthView from '../views/AuthView.vue'
import VerifyEmail from '../views/VerifyEmail.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { 
    path: "/",
      component: SimpleLayout,
      children: [
        {
          path: '/',
          name: 'home', 
          component: HomeView,
          meta: { requiresAuth: true }
        },
        { 
          path: "/auth",
          name: "auth",
          component: AuthView,
          props: route => ({ ...route.params, ...route.query }), // converts query strings and params to props
          meta: { name: 'AuthView' }  
        },
        {
          path: "/verify-email",
          name: 'verifyEmail',
          component: VerifyEmail,
          meta: { requiresAuth: true }
        }    
      ]
    }
  ]
})


router.beforeEach(async (to) => {
  const store = useUserStore()
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!store.isAuthenticated) {
      try {
        console.log("dispatch getSession");
        const session = await store.getSession();
        if (session) {          
          return to.fullPath;
        }
        else {
          return '/auth'
        }
      } catch (err) {
        console.log("router beforeEach Error: " + err);
      }
    }
  }
});

export default router
