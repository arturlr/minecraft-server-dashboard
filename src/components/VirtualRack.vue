<template>
<div>
  <v-card>
    <div>
          <apexchart
              ref="barCost"
              height="35"
              width="100" 
              type="bar"
              :options="barCost"
              :series="series"
            ></apexchart>
        </div> 
  </v-card>
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
              @click="$router.push({name: 'server', params: { id: item.id }})"
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
                small
                v-bind:color="
                  serversDict[item.id].state === 'stopped'
                    ? 'error'
                    : serversDict[item.id].state === 'running'
                    ? 'success'
                    : 'warning'
                "
              >
                lightbulb_circle</v-icon
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
import VueApexCharts from "vue-apexcharts";

export default {
  name: "VirtualRack",
  components: {
    apexchart: VueApexCharts,
  },
  data: () => ({
    stateChange: null,
    serverLoading: true,
    series: [{
          data: [{
            x: "Feb",
            y: 44
          },
          {
            x: "Mar",
            y: 51
          }, 
          {
            x: "Apr",
            y: 15
          }]
        }],
    barCost: {
      chart: {
          sparkline: {
            enabled: true
          }
        },
        labels: ['ff', 2, 3],
        xaxis: {
          crosshairs: {
            width: 1
          },
        },
        tooltip: {
          fixed: {
            enabled: false
          },
          marker: {
            show: false
          }
        },
        
    }
  
  }),
  props: {
    source: String,
  },
  created() {
    this.$nextTick(async () => {
      await this.$store.dispatch("general/createServersList");
      this.serverLoading = false
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
          this.$store.dispatch("general/upadateServersList", {
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
