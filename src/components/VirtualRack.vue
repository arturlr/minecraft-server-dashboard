<template>
  <v-card width="250">
    <v-navigation-drawer permanent>
      <v-list>
        <v-list-item>
          <v-list-item-content>
            <v-list-item-title class="text-h6">
              {{ fullName }}
            </v-list-item-title>
            <v-list-item-subtitle>
              {{ email }}
              <v-btn icon color="gray" @click="signOut">
                <v-icon>mdi-export</v-icon>
              </v-btn>
            </v-list-item-subtitle>
          </v-list-item-content>
        </v-list-item>

        <v-divider></v-divider>

        <v-list-item link :to="{ name: 'home' }">
          <v-list-item-icon>
            <v-icon>mdi-home</v-icon>
          </v-list-item-icon>
          <v-list-item-content>
            <v-list-item-title>home</v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </v-list>

      <v-divider />
      <v-subheader>Virtual Server Rack</v-subheader>

      <div v-if="serversList && serversList.length > 0">
        <v-virtual-scroll
          :items="serversList"
          :item-height="70"
          height="250"
          shaped
        >
          <template v-slot:default="{ item }">
            <v-list-item link :to="{ name: 'server', params: { id: item.id } }">
              <v-list-item-icon>
                <v-icon
                  v-bind:color="
                    serversDict[item.id].state === 'stopped'
                      ? 'error'
                      : serversDict[item.id].state === 'running'
                      ? 'success'
                      : 'warning'
                  "
                >
                  mdi-power</v-icon
                >
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title
                  class="font-weight-medium"
                  v-if="serversDict[item.id].name && serversDict[item.id].name.length > 2"
                >
                  {{ serversDict[item.id].name }}
                </v-list-item-title>
                <v-list-item-title class="font-weight-medium" v-else>
                  {{ item.id }}
                </v-list-item-title>
                <v-list-item-subtitle class="text-caption"
                  >{{ serversDict[item.id].vCpus }} CPU /
                  {{ serversDict[item.id].memSize }} MB</v-list-item-subtitle
                >
              </v-list-item-content>
            </v-list-item>
            <v-divider />
          </template>
        </v-virtual-scroll>
      </div>
    </v-navigation-drawer>
  </v-card>
</template>
<script>
import { mapGetters, mapState } from "vuex";
import { Auth, API } from "aws-amplify";
import { onChangeServerInfo } from "../graphql/subscriptions";

export default {
  name: "DefaultLayout",
  data: () => ({
    stateChange: null,
  }),
  props: {
    source: String,
  },
  created() {
     this.$nextTick(async () => {
      await this.$store.dispatch("general/createServersList");
      this.subscribeChangeServerInfo();
    });
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
    subscribeChangeServerInfo() {
      API.graphql({
        query: onChangeServerInfo,
        variables: { },
      }).subscribe({
        next: (eventData) => {
          this.$store.dispatch("general/upadateServersList", {
            serverData: eventData.value.data.onChangeServerInfo
          });
        },
      });
    },
  },
  computed: {
    ...mapState({
      serversList: (state) => state.general.serversList,
      serversDict: (state) => state.general.serversDict,
      serverStats: (state) => state.general.serverStats,
      isLoading: (state) => state.general.loading,
    }),
    ...mapGetters({
      isAuthenticated: "profile/isAuthenticated",
      email: "profile/email",
      fullName: "profile/fullName",
    }),
  },
};
</script>
