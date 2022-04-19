<template>
  <div>
    <v-app-bar dense dark>
      <div v-if="monthlyUsage[0]">
       <v-btn 
        class="ma-2"
        outlined
        small
      >
        {{ monthlyUsage[0].UnblendedCost }}
        <v-icon>
          attach_money
        </v-icon>
      </v-btn>

      <v-btn 
        class="ma-2"
        outlined
        small
      >
        {{ monthlyUsage[0].UsageQuantity }}
        <v-icon>
          av_timer
        </v-icon>
      </v-btn>
      </div>
      <v-spacer></v-spacer>
      <v-toolbar-title>Minecraft Dashboard</v-toolbar-title>
      <v-spacer></v-spacer>
      <v-tooltip bottom>
        <template v-slot:activator="{ on, attrs }">
          <v-btn text color="warning" v-bind="attrs" v-on="on">
            {{ fullName }}
          </v-btn>
        </template>
        <span>{{ email }}</span>
      </v-tooltip>
      <v-btn icon color="warning" @click="signOut">
        <v-icon>mdi-export</v-icon>
      </v-btn>
    </v-app-bar>
    <v-progress-linear
        v-if="isLoading"
        indeterminate
        height="15"
        color="warning"
        striped
      ></v-progress-linear>

    <v-main>
      <v-container>
        <virtual-rack />
        <v-layout row>
           <v-flex md-12>
            <router-view></router-view>
           </v-flex>
        </v-layout>
      </v-container>
    </v-main>
  </div>
</template>
<script>
import VirtualRack from "../components/VirtualRack.vue";
import { Auth } from "aws-amplify";
import { mapGetters, mapState } from "vuex";

export default {
  name: "DefaultLayout",
  components: {
    VirtualRack,
  },
  data: () => ({}),
  async beforeCreate() {
    await this.$store.dispatch("general/getCostUsage");
  },
  computed: {
    ...mapState({
      isLoading: (state) => state.general.loading,
      monthlyUsage: (state) => state.general.monthlyUsage
    }),
    ...mapGetters({
      isAuthenticated: "profile/isAuthenticated",
      email: "profile/email",
      fullName: "profile/fullName",
    }),
  },
  methods: {
    async signOut() {
      try {
        await Auth.signOut();
        this.$router.push("/auth");
      } catch (error) {
        console.log("error signing out: ", error);
      }
    },
  }
};
</script>
