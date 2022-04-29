<template>
  <div>
    <v-app-bar dense dark>
      <div v-if="monthlyUsage[0]">
      <v-tooltip bottom>
        <template v-slot:activator="{ on, attrs }">
       <v-btn 
        class="ma-2"
        outlined
        small
        v-bind="attrs" v-on="on"
      >
        {{ monthlyUsage[0].UnblendedCost }} $
      </v-btn>
      </template>
        <span> Total cost-to-date</span>
      </v-tooltip>

      <v-tooltip bottom>
        <template v-slot:activator="{ on, attrs }">
      <v-btn 
        class="ma-2"
        outlined
        small
        v-bind="attrs" v-on="on"
      >
        {{ monthlyUsage[0].UsageQuantity }} H
      </v-btn>
      </template>
        <span> Total usage hours-to-date</span>
      </v-tooltip>
      </div>
      <v-spacer></v-spacer>
      <v-toolbar-title v-if="!isMobile">Minecraft Dashboard</v-toolbar-title>
      <v-toolbar-title v-else>MD</v-toolbar-title>
      <v-spacer></v-spacer>

      <v-menu
        bottom
        min-width="200px"
        rounded
        offset-y
      >
      <template v-slot:activator="{ on }">
            <v-btn text color="warning" v-on="on">
              <v-icon>account_circle</v-icon>
            </v-btn>
      </template>
        <v-card>
          <v-list-item-content class="justify-center">
            <div class="mx-auto text-center">
              <h3>{{ fullName }}</h3>
              <p class="text-caption mt-1">
                {{ email }}
              </p>

              <v-divider class="my-3"></v-divider>
                    <v-tooltip bottom>
                <template v-slot:activator="{ on, attrs }">
              <v-btn icon color="warning" @click="signOut" v-bind="attrs" v-on="on">
                <v-icon>mdi-export</v-icon>
              </v-btn>
              </template>
                <span>Logout</span>
              </v-tooltip>
            </div>
          </v-list-item-content>
        </v-card>
      </v-menu>

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
    isMobile() {
      return this.$vuetify.breakpoint.xsOnly;
    },
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
