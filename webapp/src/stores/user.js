import { defineStore } from "pinia";
import { fetchUserAttributes, getCurrentUser, fetchAuthSession, signInWithRedirect, signOut } from 'aws-amplify/auth';
import { configAmplify } from "../configAmplify";

configAmplify();

export const useUserStore = defineStore("user", {
  state: () => ({
    user: null,
    userAttributes: null,
    groups: [],
    loading: false
  }),

  getters: {
    isAuthenticated: (state) => !!state.user,
    email: (state) => state.userAttributes?.email,
    fullname: (state) => {
      const given = state.userAttributes?.given_name || '';
      const family = state.userAttributes?.family_name || '';
      return `${given} ${family}`.trim() || state.userAttributes?.email;
    },
    isAdmin: (state) => state.groups.includes("admin"),
  },

  actions: {
    async getSession() {
      this.loading = true;
      try {
        this.user = await getCurrentUser();
        this.userAttributes = await fetchUserAttributes();
        
        const session = await fetchAuthSession();
        const idToken = session.tokens?.idToken;
        this.groups = idToken?.payload?.['cognito:groups'] || [];
        
        this.loading = false;
        return true;
      } catch (err) {
        this.loading = false;
        return false;
      }
    },

    async login() {
      await signInWithRedirect({ provider: 'Google' });
    },

    async logout() {
      await signOut();
      this.user = null;
      this.userAttributes = null;
      this.groups = [];
    }
  }
});
