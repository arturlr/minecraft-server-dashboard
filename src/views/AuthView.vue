<template>
<v-container fill-height fluid>
  <v-card
      class="mx-auto"
      max-width="400"
      outlined
    >
      <v-list-item three-line>
        <v-list-item-content>
          <div class="text-overline mb-4">
            Minecraft Dashboard by GeckoByte 
          </div>
          <v-list-item-subtitle>This application requires you to login using your Google Account.</v-list-item-subtitle>
        </v-list-item-content>
      </v-list-item>

      <v-card-actions>
        <v-btn
          color="error"
          depressed
          @click="signIn"
        >
          Login
        </v-btn>
      </v-card-actions>
      <v-card-text>
        {{ loginError}}
      </v-card-text>
    </v-card>
</v-container>
</template>

<script>
import { Auth } from "aws-amplify";

export default {
  name: "AuthView",
  data() {
    return {
      hasLoginError: false,
      loginError: '',
      isAuthenticated: false,
      email: null
    };
  },
  methods: {
    signIn: async function() {
      try {
        await Auth.federatedSignIn({provider: 'Google'});
        console.log("federatedSignIn")
      } catch (error) {
        this.loginError = error.message;
        this.hasLoginError = true;
      }         
    }
  }
};
</script>
