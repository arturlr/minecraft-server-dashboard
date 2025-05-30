import { defineStore } from "pinia";
import { fetchUserAttributes, getCurrentUser, fetchAuthSession } from 'aws-amplify/auth';
import { ConsoleLogger } from 'aws-amplify/utils';
import { configAmplify } from "../configAmplify";

const logger = new ConsoleLogger('minecraftDashboard');
configAmplify();

export const useUserStore = defineStore("user", {
  state: () => ({
    user: null,
    userAttributes: null,
    userTokens: null,
    groups: []
  }),

  getters: {
    isAuthenticated: (state) => !!state.user,
    userId: (state) => state.userAttributes?.sub,
    email: (state) => state.userAttributes?.email,
    fullname: (state) => state.userAttributes?.given_name + " " + state.userAttributes?.family_name,
    isAdmin: (state) => state.groups.includes("admin"),
  },
  actions: {
    async getSession() {
      try {
        // Attempt to get the current user
        this.user = await getCurrentUser();
        this.userAttributes = await fetchUserAttributes();
        
        // Get user groups from Cognito
        try {
          const session = await fetchAuthSession();
          const idToken = session.tokens?.idToken;
          if (idToken && idToken.payload && idToken.payload['cognito:groups']) {
            this.groups = idToken.payload['cognito:groups'];
          } else {
            this.groups = [];
          }
        } catch (groupErr) {
          console.error("Error fetching user groups:", groupErr);
          this.groups = [];
        }
        
        console.log("User authenticated and attributes fetched successfully");
        return true
      } catch (err) {  
        console.log("User is not authenticated");     
        return false
      }
    }
  }
});