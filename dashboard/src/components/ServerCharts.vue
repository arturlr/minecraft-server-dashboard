<script setup>
import { reactive, ref, onMounted, onUnmounted, watch } from "vue";
import { generateClient } from 'aws-amplify/api';
import * as subscriptions from '../graphql/subscriptions';
import * as queries from '../graphql/queries';
import { Hub } from 'aws-amplify/utils';
import { useServerStore } from "../stores/server";
import VueApexCharts from "vue3-apexcharts";
import dayjs from "dayjs";

const serverStore = useServerStore();
const graphQlClient = generateClient();

const cpuOptions = ref({
    chart: {
        type: "area",
        group: 'server-metrics', // Synchronized charts
        height: 150,
        toolbar: {
            show: true,
            tools: {
                download: false,
                selection: true,
                zoom: true,
                zoomin: true,
                zoomout: true,
                pan: false,
                reset: true
            }
        },
        zoom: {
            enabled: true,
            type: 'x',
            autoScaleYaxis: true
        },
        animations: {
            enabled: true,
            easing: 'easeinout',
            speed: 800,
            animateGradually: {
                enabled: true,
                delay: 150
            },
            dynamicAnimation: {
                enabled: true,
                speed: 350
            }
        }
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
        width: 2
    },
    fill: {
        type: 'gradient',
        gradient: {
            shadeIntensity: 1,
            opacityFrom: 0.7,
            opacityTo: 0.3,
            stops: [0, 90, 100]
        }
    },
    dataLabels: {
        enabled: false
    },
    yaxis: {
        min: 0,
        max: 100,
        labels: {
            formatter: function (val) {
                return val.toFixed(0) + '%';
            }
        }
    },
    xaxis: {
        type: "datetime",
        labels: {
            formatter: function (val, timestamp) {
                return dayjs(timestamp).format("HH:mm");
            },
        },
    },
    tooltip: {
        enabled: true,
        x: {
            format: 'HH:mm:ss'
        },
        y: {
            formatter: (val) => `${val.toFixed(1)}%`
        }
    },
    annotations: {
        yaxis: [{
            y: 80,
            borderColor: '#FF4560',
            label: {
                text: 'High CPU',
                style: {
                    color: '#fff',
                    background: '#FF4560'
                }
            }
        }]
    },
    colors: ["#154360"],
})

const memOptions = ref({
    chart: {
        type: "area",
        group: 'server-metrics', // Synchronized charts
        height: 150,
        toolbar: {
            show: true,
            tools: {
                download: false,
                selection: true,
                zoom: true,
                zoomin: true,
                zoomout: true,
                pan: false,
                reset: true
            }
        },
        zoom: {
            enabled: true,
            type: 'x',
            autoScaleYaxis: true
        },
        animations: {
            enabled: true,
            easing: 'easeinout',
            speed: 800,
            animateGradually: {
                enabled: true,
                delay: 150
            },
            dynamicAnimation: {
                enabled: true,
                speed: 350
            }
        }
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
        width: 2
    },
    fill: {
        type: 'gradient',
        gradient: {
            shadeIntensity: 1,
            opacityFrom: 0.7,
            opacityTo: 0.3,
            stops: [0, 90, 100]
        }
    },
    dataLabels: {
        enabled: false
    },
    yaxis: {
        min: 0,
        max: 100,
        labels: {
            formatter: function (val) {
                return val.toFixed(0) + '%';
            }
        }
    },
    xaxis: {
        type: "datetime",
        labels: {
            formatter: function (val, timestamp) {
                return dayjs(timestamp).format("HH:mm");
            },
        },
    },
    tooltip: {
        enabled: true,
        x: {
            format: 'HH:mm:ss'
        },
        y: {
            formatter: (val) => `${val.toFixed(1)}%`
        }
    },
    annotations: {
        yaxis: [{
            y: 80,
            borderColor: '#FF9800',
            label: {
                text: 'High Memory',
                style: {
                    color: '#fff',
                    background: '#FF9800'
                }
            }
        }]
    },
    colors: ["#5DADE2"],
})

const netOptions = ref({
    chart: {
        type: "area",
        group: 'server-metrics', // Synchronized charts
        height: 150,
        toolbar: {
            show: true,
            tools: {
                download: false,
                selection: true,
                zoom: true,
                zoomin: true,
                zoomout: true,
                pan: false,
                reset: true
            }
        },
        zoom: {
            enabled: true,
            type: 'x',
            autoScaleYaxis: true
        },
        animations: {
            enabled: true,
            easing: 'easeinout',
            speed: 800,
            animateGradually: {
                enabled: true,
                delay: 150
            },
            dynamicAnimation: {
                enabled: true,
                speed: 350
            }
        }
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
        width: 2
    },
    fill: {
        type: 'gradient',
        gradient: {
            shadeIntensity: 1,
            opacityFrom: 0.7,
            opacityTo: 0.3,
            stops: [0, 90, 100]
        }
    },
    dataLabels: {
        enabled: false
    },
    yaxis: {
        min: 0,
        labels: {
            formatter: function (val) {
                return val.toFixed(0);
            }
        }
    },
    xaxis: {
        type: "datetime",
        labels: {
            formatter: function (val, timestamp) {
                return dayjs(timestamp).format("HH:mm");
            },
        },
    },
    tooltip: {
        enabled: true,
        x: {
            format: 'HH:mm:ss'
        },
        y: {
            formatter: (val) => `${val.toFixed(0)} packets`
        }
    },
    colors: ["#D35400"],
})

const usersOptions = ref({
    chart: {
        type: "area",
        group: 'server-metrics', // Synchronized charts
        height: 150,
        toolbar: {
            show: true,
            tools: {
                download: false,
                selection: true,
                zoom: true,
                zoomin: true,
                zoomout: true,
                pan: false,
                reset: true
            }
        },
        zoom: {
            enabled: true,
            type: 'x',
            autoScaleYaxis: true
        },
        animations: {
            enabled: true,
            easing: 'easeinout',
            speed: 800,
            animateGradually: {
                enabled: true,
                delay: 150
            },
            dynamicAnimation: {
                enabled: true,
                speed: 350
            }
        }
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
        curve: "stepline", // Step line for discrete user counts
        width: 2
    },
    fill: {
        type: 'gradient',
        gradient: {
            shadeIntensity: 1,
            opacityFrom: 0.7,
            opacityTo: 0.3,
            stops: [0, 90, 100]
        }
    },
    dataLabels: {
        enabled: false
    },
    yaxis: {
        min: 0,
        labels: {
            formatter: function (val) {
                return val.toFixed(0);
            }
        }
    },
    xaxis: {
        type: "datetime",
        labels: {
            formatter: function (val, timestamp) {
                return dayjs(timestamp).format("HH:mm");
            },
        },
    },
    tooltip: {
        enabled: true,
        x: {
            format: 'HH:mm:ss'
        },
        y: {
            formatter: (val) => `${val.toFixed(0)} users`
        }
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
const metricAlert = ref(false);
const metricMsg = ref(null);
const metricsSubscription = ref(null);
const lastUpdateTime = ref(null);

// Expose lastUpdateTime to parent component
defineExpose({
  lastUpdateTime
});

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
        data: [...data]
      }];
      break;

    case "cpu":
      cpuSeries.value = [{
        name: "cpu",
        data: [...data]
      }];
      break;

    case "mem":
      memSeries.value = [{
        name: "mem",
        data: [...data]
      }];
      break

    case "net":
      netSeries.value = [{
        name: "net",
        data: [...data]
      }]
      break;
  }
}

async function loadHistoricalMetrics() {
  if (!serverStore.selectedServerId) {
    console.warn('[ServerCharts] Cannot load metrics: no selectedServerId');
    return;
  }

  console.log('[ServerCharts] Loading historical metrics for server:', serverStore.selectedServerId);

  // Clear existing data first
  cpuSeries.value = [{ name: 'cpu', data: [] }];
  memSeries.value = [{ name: 'mem', data: [] }];
  netSeries.value = [{ name: 'net', data: [] }];
  usersSeries.value = [{ name: 'users', data: [] }];

  try {
    const response = await graphQlClient.graphql({
      query: queries.getServerMetrics,
      variables: { id: serverStore.selectedServerId }
    });

    const metrics = response.data.getServerMetrics;
    if (metrics) {
      console.log('[ServerCharts] Historical metrics loaded');
      processMetricData(metrics);
    } else {
      console.warn('[ServerCharts] No metrics data returned from query');
    }
  } catch (error) {
    console.error('[ServerCharts] Error loading historical metrics:', error);
  }
}

function processMetricData(metricsData) {
  // Parse the JSON strings - handle double-encoded JSON from AppSync
  let cpuData = [];
  let memData = [];
  let netData = [];
  let usersData = [];
  
  try {
    if (typeof metricsData.cpuStats === 'string') {
      cpuData = JSON.parse(metricsData.cpuStats);
      // Check if it's still a string (double-encoded)
      if (typeof cpuData === 'string') {
        cpuData = JSON.parse(cpuData);
      }
    } else {
      cpuData = metricsData.cpuStats || [];
    }
  } catch (e) {
    console.error('[ServerCharts] Error parsing cpuStats:', e);
    cpuData = [];
  }
  
  try {
    if (typeof metricsData.memStats === 'string') {
      memData = JSON.parse(metricsData.memStats);
      if (typeof memData === 'string') {
        memData = JSON.parse(memData);
      }
    } else {
      memData = metricsData.memStats || [];
    }
  } catch (e) {
    console.error('[ServerCharts] Error parsing memStats:', e);
    memData = [];
  }
  
  try {
    if (typeof metricsData.networkStats === 'string') {
      netData = JSON.parse(metricsData.networkStats);
      if (typeof netData === 'string') {
        netData = JSON.parse(netData);
      }
    } else {
      netData = metricsData.networkStats || [];
    }
  } catch (e) {
    console.error('[ServerCharts] Error parsing networkStats:', e);
    netData = [];
  }
  
  try {
    if (typeof metricsData.activeUsers === 'string') {
      usersData = JSON.parse(metricsData.activeUsers);
      if (typeof usersData === 'string') {
        usersData = JSON.parse(usersData);
      }
    } else {
      usersData = metricsData.activeUsers || [];
    }
  } catch (e) {
    console.error('[ServerCharts] Error parsing activeUsers:', e);
    usersData = [];
  }

  console.log('[ServerCharts] Loaded metrics:', {
    cpu: cpuData?.length,
    mem: memData?.length,
    net: netData?.length,
    users: usersData?.length
  });

  // Update last update timestamp
  lastUpdateTime.value = new Date();

  if (cpuData && cpuData.length > 0) {
    const lastValue = cpuData[cpuData.length - 1];
    if (lastValue && lastValue.y !== undefined) {
      currentCPU.value = lastValue.y;
      cpuOptions.value.title.text = `CPU - ${currentCPU.value.toFixed(1)}%`;
      updateMetrics('cpu', cpuData);
    }
  }

  if (netData && netData.length > 0) {
    const lastValue = netData[netData.length - 1];
    if (lastValue && lastValue.y !== undefined) {
      currentNet.value = lastValue.y;
      netOptions.value.title.text = `Network - ${currentNet.value.toFixed(0)} packages`;
      updateMetrics('net', netData);
    }
  }

  if (memData && memData.length > 0) {
    const lastValue = memData[memData.length - 1];
    if (lastValue && lastValue.y !== undefined) {
      currentMemory.value = lastValue.y;
      memOptions.value.title.text = `Memory - ${currentMemory.value.toFixed(1)}%`;
      updateMetrics('mem', memData);
    }
  }

  if (Array.isArray(usersData) && usersData.length > 0) {
    const lastValue = usersData[usersData.length - 1];
    if (lastValue && lastValue.y !== undefined) {
      currentUsers.value = lastValue.y;
      usersOptions.value.title.text = `Users - ${currentUsers.value.toFixed(0)}`;
      updateMetrics('users', usersData);
    }
  }
}

async function subscribePutServerMetric() {
  // Unsubscribe from any existing subscription
  if (metricsSubscription.value) {
    metricsSubscription.value.unsubscribe();
    metricsSubscription.value = null;
  }

  if (!serverStore.selectedServerId) {
    console.warn('[ServerCharts] Cannot subscribe: no selectedServerId');
    return;
  }

  console.log('[ServerCharts] Subscribing to metrics for server:', serverStore.selectedServerId);

  // Load historical data first
  await loadHistoricalMetrics();

  metricsSubscription.value = await graphQlClient
    .graphql({
      query: subscriptions.onPutServerMetric,
      variables: { id: serverStore.selectedServerId },
    }).subscribe({
      next: (response) => {
        console.log("[ServerCharts] Metric update received:", response.data.onPutServerMetric.id);
        processMetricData(response.data.onPutServerMetric);
      },
      error: (error) => console.warn('[ServerCharts] Subscription error:', error)
    });
}

// Watch for selectedServerId changes
watch(() => serverStore.selectedServerId, (newId) => {
  console.log('[ServerCharts] selectedServerId changed to:', newId);
  if (newId) {
    subscribePutServerMetric();
  }
}, { immediate: true });

// Cleanup on unmount
onUnmounted(() => {
  console.log('[ServerCharts] Component unmounting, cleaning up subscription');
  if (metricsSubscription.value) {
    metricsSubscription.value.unsubscribe();
    metricsSubscription.value = null;
  }
});


</script>

<template>
  <v-row>
    <v-col cols="12" md="6">
      <v-card elevation="2" class="pa-2">
        <VueApexCharts ref="usersChart" height="150" :options="usersOptions" :series="usersSeries" />
      </v-card>
    </v-col>

    <v-col cols="12" md="6">
      <v-card elevation="2" class="pa-2">
        <VueApexCharts ref="cpuChart" height="150" :options="cpuOptions" :series="cpuSeries" />
      </v-card>
    </v-col>

    <v-col cols="12" md="6">
      <v-card elevation="2" class="pa-2">
        <VueApexCharts ref="memChart" height="150" :options="memOptions" :series="memSeries" />
      </v-card>
    </v-col>

    <v-col cols="12" md="6">
      <v-card elevation="2" class="pa-2">
        <VueApexCharts ref="netChart" height="150" :options="netOptions" :series="netSeries" />
      </v-card>
    </v-col>
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
