<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useServerStore } from "../stores/server";
import VueApexCharts from "vue3-apexcharts";
import moment from "moment";

const serverStore = useServerStore();

const chartOptions = computed(() => ({
  chart: {
    type: 'area',
    animations: {
      enabled: true,
      easing: 'easeinout',
      speed: 800,
    },
    background: 'transparent',
    toolbar: {
      show: false
    },
    zoom: {
      enabled: false
    }
  },
  stroke: {
    curve: 'smooth',
    width: 2
  },
  grid: {
    borderColor: '#f1f1f1',
    row: {
      colors: ['transparent', 'transparent'],
      opacity: 0.5
    }
  },
  tooltip: {
    theme: 'dark',
    x: {
      format: 'HH:mm'
    }
  },
  dataLabels: {
    enabled: false
  },
  xaxis: {
    type: 'datetime',
    labels: {
      datetimeFormatter: {
        hour: 'HH:mm'
      }
    }
  },
  yaxis: {
    labels: {
      formatter: function (value) {
        return value.toFixed(0);
      }
    }
  },
  fill: {
    type: 'gradient',
    gradient: {
      shadeIntensity: 1,
      opacityFrom: 0.7,
      opacityTo: 0.2,
      stops: [0, 100]
    }
  }
}));

const cpuChartOptions = computed(() => ({
  ...chartOptions.value,
  title: {
    text: 'CPU Utilization',
    align: 'left',
    style: {
      fontSize: '16px',
      fontWeight: 600
    }
  },
  colors: ['#00C853'],
  yaxis: {
    min: 0,
    max: 100,
    title: {
      text: 'CPU Usage (%)'
    },
    labels: {
      formatter: (value) => `${value.toFixed(0)}%`
    }
  }
}));

const memoryChartOptions = computed(() => ({
  ...chartOptions.value,
  title: {
    text: 'Memory Usage',
    align: 'left',
    style: {
      fontSize: '16px',
      fontWeight: 600
    }
  },
  colors: ['#2196F3'],
  yaxis: {
    title: {
      text: 'Memory (MB)'
    },
    labels: {
      formatter: (value) => `${(value / 1024).toFixed(1)}GB`
    }
  }
}));

const playersChartOptions = computed(() => ({
  ...chartOptions.value,
  title: {
    text: 'Active Players',
    align: 'left',
    style: {
      fontSize: '16px',
      fontWeight: 600
    }
  },
  colors: ['#FF6D00'],
  yaxis: {
    min: 0,
    title: {
      text: 'Players Count'
    },
    labels: {
      formatter: (value) => Math.round(value)
    }
  }
}));

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

const cpuData = computed(() => formatChartData(serverStore.metrics || [], 'cpu'));
const memoryData = computed(() => formatChartData(serverStore.metrics || [], 'memory'));
const playersData = computed(() => formatChartData(serverStore.metrics || [], 'players'));

</script>

<template>
  <v-card flat class="mt-4">
    <v-card-text>
      <v-row>
        <v-col cols="12" md="6">
          <v-card elevation="1" class="pa-2">
            <apexchart
              type="area"
              height="200"
              :options="cpuChartOptions"
              :series="cpuData"
            />
          </v-card>
        </v-col>
        <v-col cols="12" md="6">
          <v-card elevation="1" class="pa-2">
            <apexchart
              type="area"
              height="200"
              :options="memoryChartOptions"
              :series="memoryData"
            />
          </v-card>
        </v-col>
        <v-col cols="12">
          <v-card elevation="1" class="pa-2">
            <apexchart
              type="area"
              height="200"
              :options="playersChartOptions"
              :series="playersData"
            />
          </v-card>
        </v-col>
      </v-row>

      <!-- Stats Summary -->
      <v-row class="mt-4">
        <v-col cols="12" md="4">
          <v-card elevation="1" class="pa-4">
            <div class="text-h6 mb-2">Current CPU</div>
            <div class="d-flex align-center">
              <v-progress-circular
                :model-value="cpuData[0]?.data.slice(-1)[0]?.y || 0"
                :color="cpuData[0]?.data.slice(-1)[0]?.y > 80 ? 'error' : 'success'"
                size="64"
              >
                {{ cpuData[0]?.data.slice(-1)[0]?.y.toFixed(0) }}%
              </v-progress-circular>
              <v-icon
                :color="cpuData[0]?.data.slice(-1)[0]?.y > 80 ? 'error' : 'success'"
                class="ml-4"
                size="24"
              >
                {{ cpuData[0]?.data.slice(-1)[0]?.y > 80 ? 'mdi-alert' : 'mdi-check-circle' }}
              </v-icon>
            </div>
          </v-card>
        </v-col>
        <v-col cols="12" md="4">
          <v-card elevation="1" class="pa-4">
            <div class="text-h6 mb-2">Memory Usage</div>
            <div class="d-flex align-center">
              <v-progress-linear
                :model-value="(memoryData[0]?.data.slice(-1)[0]?.y / serverStore.totalMemory) * 100"
                color="info"
                height="25"
              >
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
              Peak today: {{ Math.max(...(playersData[0]?.data.map(d => d.y) || [0])) }}
            </div>
          </v-card>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.v-card {
  transition: all 0.3s ease;
}

.v-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}
</style>
