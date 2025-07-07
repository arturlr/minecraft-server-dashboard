<script setup>
import { reactive, ref, onMounted } from "vue";
import { generateClient } from 'aws-amplify/api';
import * as subscriptions from '../graphql/subscriptions';
import { Hub } from 'aws-amplify/utils';
import { useServerStore } from "../stores/server";
import VueApexCharts from "vue3-apexcharts";
import moment from "moment";

const serverStore = useServerStore();
const graphQlClient = generateClient();

const cpuOptions = ref({
    chart: {
        type: "area",
        sparkline: {
            enabled: true,
        },
    },
    title: {
        text: "CPU",
        offsetX: 30,
        style: {
            fontSize: '14px',
            cssClass: 'apexcharts-yaxis-title'
        }
    },
    stroke: {
        curve: "straight",
    },
    fill: {
        opacity: 0.3,
    },
    yaxis: {
        min: 0,
    },
    xaxis: {
        type: "datetime",
        labels: {
            formatter: function (val, timestamp) {
                return moment(new Date(timestamp)).format("HH:mm");
            },
        },
    },
    colors: ["#154360"],
})

const memOptions = ref({
    chart: {
        type: "area",
        sparkline: {
            enabled: true,
        },
    },
    title: {
        text: "Memory",
        offsetX: 30,
        style: {
            fontSize: '14px',
            cssClass: 'apexcharts-yaxis-title'
        }
    },
    stroke: {
        curve: "straight",
    },
    fill: {
        opacity: 0.3,
    },
    yaxis: {
        min: 0,
    },
    xaxis: {
        type: "datetime",
        labels: {
            formatter: function (val, timestamp) {
                return moment(new Date(timestamp)).format("HH:mm");
            },
        },
    },
    colors: ["#5DADE2"],
})

const netOptions = ref({
    chart: {
        type: "area",
        sparkline: {
            enabled: true,
        },
    },
    title: {
        text: "Networking",
        offsetX: 30,
        style: {
            fontSize: '14px',
            cssClass: 'apexcharts-yaxis-title'
        }
    },
    stroke: {
        curve: "straight",
    },
    fill: {
        opacity: 0.3,
    },
    yaxis: {
        min: 0,
    },
    xaxis: {
        type: "datetime",
        labels: {
            formatter: function (val, timestamp) {
                return moment(new Date(timestamp)).format("HH:mm");
            },
        },
    },
    colors: ["#D35400"],
})

const usersOptions = ref({
    chart: {
        type: "area",
        sparkline: {
            enabled: true,
        },
    },
    title: {
        text: "Users",
        offsetX: 30,
        style: {
            fontSize: '14px',
            cssClass: 'apexcharts-yaxis-title'
        }
    },
    stroke: {
        curve: "straight",
    },
    fill: {
        opacity: 0.3,
    },
    yaxis: {
        min: 0,
    },
    xaxis: {
        type: "datetime",
        labels: {
            formatter: function (val, timestamp) {
                return moment(new Date(timestamp)).format("HH:mm");
            },
        },
    },
    colors: ["#52B12C"],
})

// Add these refs at the top level of your script
const usersSeries = ref([]);
const cpuSeries = ref([]);
const memSeries = ref([]);
const netSeries = ref([]);

// Also add these for the current values if you're using them
const currentCPU = ref(0);
const currentMemory = ref(0);
const currentNet = ref(0);
const currentUsers = ref(0);

// Optional: You can initialize them with empty data structure
const initSeries = [{
  name: '',
  data: []
}];

usersSeries.value = [...initSeries];
cpuSeries.value = [...initSeries];
memSeries.value = [...initSeries];
netSeries.value = [...initSeries];

// Format data for charts
const formatChartData = (data, key) => {
  return [{
    name: key,
    data: data.map(point => ({
      x: new Date(point.timestamp),
      y: point[key]
    }))
  }];
};

// const cpuData = computed(() => formatChartData(serverStore.metrics || [], 'cpu'));
// const memoryData = computed(() => formatChartData(serverStore.metrics || [], 'memory'));
// const playersData = computed(() => formatChartData(serverStore.metrics || [], 'players'));

function classColor(sState) {
  if (sState === "running" || sState === "ok") {
    return "green";
  } else if (sState === "stopped" || sState === "fail") {
    return "red";
  } else {
    return "orange";
  }
}

function updateMetrics(name, data) {

  if (serverStore.serversDict[serverStore.selectedServerId] && data.alertMsg && data.alertMsg.length > 0) {
    metricAlert.value = true;
    metricMsg.value = serverStore.serversDict[serverStore.selectedServerId].alertMsg
  }
  else {
    metricAlert.value = false;
    metricMsg.value = null
  }

  switch (name) {
    case "users":
      usersSeries.value = [{
        name: "users",
        data: data
      }];
      break;

    case "cpu":
      cpuSeries.value = [{
        name: "cpu",
        data: data
      }];
      break;

    case "mem":
      memSeries.value = [{
        name: "mem",
        data: data
      }];
      break

    case "net":
      netSeries.value = [{
        name: "net",
        data: data
      }]
      break;
  }
}

async function subscribePutServerMetric() {

  await graphQlClient
    .graphql({
      query: subscriptions.onPutServerMetric,
      variables: { id: serverStore.selectedServerId },
    }).subscribe({
      next: (response) => {
        console.log("updating: " + response.data.onPutServerMetric.id)
        const cpuData = JSON.parse(response.data.onPutServerMetric.cpuStats);
        const memData = JSON.parse(response.data.onPutServerMetric.memStats);
        const netData = JSON.parse(response.data.onPutServerMetric.networkStats);
        let usersData = [];
        try {
          const parsedUsers = JSON.parse(response.data.onPutServerMetric.activeUsers);
          usersData = Array.isArray(parsedUsers) ? parsedUsers : [];
        } catch (error) {
          console.warn('Failed to parse activeUsers data:', error);
          usersData = [];
        }

        if (cpuData && cpuData.length > 0) {
          // Get the last CPU value
          currentCPU.value = cpuData[cpuData.length - 1]?.y ?? 0;
          
          // Update chart options
          cpuOptions.value = {
            title: {
              text: `CPU - ${currentCPU.value.toFixed(1)}%`
            }
          };
        }
        //updateMetrics('cpu', cpuData);

        if (netData.length > 0)
          currentNet.value = netData[netData.length - 1].y;
        netOptions.value = {
          title: {
            text: "Network - " + currentNet.value.toString() + " packages"
          }
        }
        updateMetrics('net', netData);

        if (memData.length > 0)
          currentMemory.value = memData[memData.length - 1].y;
        memOptions.value = {
          title: {
            text: "Memory - " + currentMemory.value.toString() + " %"
          }
        }
        updateMetrics('mem', memData);

        if (Array.isArray(usersData) && usersData.length > 0) {
          currentUsers.value = usersData[usersData.length - 1].y;
          usersOptions.value = {
            title: {
              text: "Users - " + currentUsers.value.toString()
            }
          }
          updateMetrics('users', usersData);
        }

      },
      error: (error) => console.warn(error)
    });
}

onMounted(async () => {
  await subscribePutServerMetric()
})


</script>

<template>
  <v-row>
    <v-card variant="plain">
      <VueApexCharts ref="usersChart" height="70" :options="usersOptions" :series="usersSeries" />
    </v-card>

    <v-card variant="plain">
      <VueApexCharts ref="cpuChart" height="70" :options="cpuOptions" :series="cpuSeries" />
    </v-card>

    <v-card variant="plain">
      <VueApexCharts ref="memChart" height="70" :options="memOptions" :series="memSeries" />
    </v-card>

    <v-card variant="plain">
      <VueApexCharts ref="netChart" height="70" :options="netOptions" :series="netSeries" />
    </v-card>
  </v-row>


      <!-- Stats Summary -->
      <!-- <v-row class="mt-4">
        <v-col cols="12" md="4">
          <v-card elevation="1" class="pa-4">
            <div class="text-h6 mb-2">Current CPU</div>
            <div class="d-flex align-center">
              <v-progress-circular :model-value="cpuData[0]?.data.slice(-1)[0]?.y || 0"
                :color="cpuData[0]?.data.slice(-1)[0]?.y > 80 ? 'error' : 'success'" size="64">
                {{ cpuData[0]?.data.slice(-1)[0]?.y.toFixed(0) }}%
              </v-progress-circular>
              <v-icon :color="cpuData[0]?.data.slice(-1)[0]?.y > 80 ? 'error' : 'success'" class="ml-4" size="24">
                {{ cpuData[0]?.data.slice(-1)[0]?.y > 80 ? 'mdi-alert' : 'mdi-check-circle' }}
              </v-icon>
            </div>
          </v-card>
        </v-col>
        <v-col cols="12" md="4">
          <v-card elevation="1" class="pa-4">
            <div class="text-h6 mb-2">Memory Usage</div>
            <div class="d-flex align-center">
              <v-progress-linear :model-value="(memoryData[0]?.data.slice(-1)[0]?.y / serverStore.totalMemory) * 100"
                color="info" height="25">
                <template v-slot:default="{ value }">
                  <strong>{{ value.toFixed(0) }}%</strong>
                </template>
              </v-progress-linear>
            </div>
            <div class="text-caption mt-2">
              {{ (memoryData[0]?.data.slice(-1)[0]?.y / 1024).toFixed(1) }}GB /
              {{ (serverStore.totalMemory / 1024).toFixed(1) }}GB
            </div>
          </v-card>
        </v-col>
        <v-col cols="12" md="4">
          <v-card elevation="1" class="pa-4">
            <div class="text-h6 mb-2">Players Online</div>
            <div class="d-flex align-center">
              <v-icon color="orange" size="32" class="mr-2">mdi-account-group</v-icon>
              <span class="text-h4">{{ playersData[0]?.data.slice(-1)[0]?.y || 0 }}</span>
              <span class="text-caption ml-2">players</span>
            </div>
            <v-divider class="my-2"></v-divider>
            <div class="text-caption">
              Peak today: {{Math.max(...(playersData[0]?.data.map(d => d.y) || [0]))}}
            </div>
          </v-card>
        </v-col>
      </v-row> -->

</template>

<style scoped>
.v-card {
  transition: all 0.3s ease;
}

.v-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}
</style>
