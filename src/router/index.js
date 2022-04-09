import Vue from 'vue'
import VueRouter from 'vue-router'
import store from "../store";

import DefaultLayout from '../layouts/Default.vue'
import SimpleLayout from '../layouts/Simple.vue' 
import Home from '../views/HomeView.vue'
import Server from '../views/ServerCard.vue'
import Auth from '../views/AuthView.vue'


Vue.use(VueRouter)

const router = new VueRouter({
  routes: [
    {
      path: "/",
      component: DefaultLayout,
      children: [
        {
          path: "/",
          name: "home",
          component: Home,
          meta: { requiresAuth: true, name: 'Home' }
        },
        {
          path: "server/:id",
          name: "server",
          component: Server,
          meta: { requiresAuth: true, name: 'Server' }
        }
      ]
    },
    {
      path: "/auth",
      component: SimpleLayout,
      children: [
        {
          path: "",
          name: "auth",
          component: Auth,
          props: route => ({ ...route.params, ...route.query }), // converts query strings and params to props
          meta: { name: 'Auth' }
        }
      ]
    }

  ]
})

/**
 * Authentication Guard for routes with requiresAuth metadata
 *
 * @param {Object} to - Intended route navigation
 * @param {Object} from - Previous route navigation
 * @param {Object} next - Next route navigation
 * @returns {Object} next - Next route
 */

 router.beforeEach(async (to, from, next) => {
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!store.getters["profile/isAuthenticated"]) {
      try {
        console.log("dispatch profile/getSession");
        await store.dispatch("profile/getSession");
        next({ name: "home", query: { redirectTo: to.name } });
        //next();
      } catch (err) {
        //console.log("router beforeEach Error: " + err);
        next({ name: "auth", query: { redirectTo: to.name } });
      }
    }
  }
  next();
});

export default router;