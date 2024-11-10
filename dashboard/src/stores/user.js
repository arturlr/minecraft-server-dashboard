import { defineStore } from "pinia";
import { fetchUserAttributes, getCurrentUser } from 'aws-amplify/auth';
import { ConsoleLogger } from 'aws-amplify/utils';
import { configAmplify } from "../configAmplify";

const logger = new ConsoleLogger('minecraftDashboard');
configAmplify();

export const useUserStore = defineStore("user", {
  state: () => ({
    user: null,
    userAttributes: null,
    userTokens: null
  }),

  getters: {
    isAuthenticated: (state) => !!state.user,
    userId: (state) => state.userAttributes?.sub,
    email: (state) => state.userAttributes?.email,
    fullname: (state) => state.userAttributes?.given_name + " " + state.userAttributes?.family_name,
  },
  actions: {
    async getSession() {
      try {
        // Attempt to get the current user
        this.user = await getCurrentUser();
        this.userAttributes = await fetchUserAttributes();
        console.log("User authenticated and attributes fetched successfully");
        return true
      } catch (err) {  
        console.log("User is not authenticated");     
        return false
      }
    }
  }
});