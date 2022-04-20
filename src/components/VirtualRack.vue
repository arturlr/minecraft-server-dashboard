<template>
  <div>
    <div v-if="serversList && serversList.length > 0">
      <v-card>
        <v-slide-group v-model="serversList" show-arrows>
          <!-- <v-btn
            text
            color="black"
            large
          >
            Virtual Rack
          </v-btn> -->
          <v-slide-item v-for="(item, i) in serversList" :key="i">
            <v-btn
              class="ma-2"
              outlined
              small
              @click="$router.push({ name: 'server', params: { id: item.id } })"
            >
              <span
                v-if="
                  serversDict[item.id].name &&
                  serversDict[item.id].name.length > 2
                "
              >
                {{ serversDict[item.id].name }}
              </span>
              <span v-else>
                {{ item.id }}
              </span>
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
            </v-btn>
          </v-slide-item>
        </v-slide-group>
      </v-card>
    </div>
  </div>
</template>
<script>
import { mapGetters, mapState } from "vuex";
import { API } from "aws-amplify";
import { onChangeServerInfo } from "../graphql/subscriptions";

export default {
  name: "VirtualRack",
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
    subscribeChangeServerInfo() {
      API.graphql({
        query: onChangeServerInfo,
        variables: {},
      }).subscribe({
        next: (eventData) => {
          this.$store.dispatch("general/upadateServersState", {
            serverData: eventData.value.data.onChangeServerInfo,
          });
        },
      });
    },
  },
  computed: {
    ...mapState({
      serversList: (state) => state.general.serversList,
      serversDict: (state) => state.general.serversDict,
      serverStats: (state) => state.general.serverStats
    }),
    ...mapGetters({
      isAuthenticated: "profile/isAuthenticated",
      email: "profile/email",
      fullName: "profile/fullName",
    }),
  },
};
</script>
