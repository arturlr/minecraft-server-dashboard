<template>
  <v-card color="surface" class="border-green overflow-hidden" border="thin" :class="{ 'opacity-80': !server.online }">
    <!-- Hero Image -->
    <div class="server-hero" :style="{ backgroundImage: `url(${server.image})` }" :class="{ grayscale: !server.online }">
      <div class="hero-overlay" />
      <v-chip :color="server.online ? 'primary' : 'grey'" variant="flat" size="small" class="status-badge">
        <span v-if="server.online" class="status-dot pulse" />
        <span v-else class="status-dot offline" />
        {{ server.online ? 'ONLINE' : 'OFFLINE' }}
      </v-chip>
    </div>

    <div class="pa-5 d-flex flex-column ga-5">
      <!-- Header -->
      <div class="d-flex justify-space-between align-start">
        <div>
          <h3 class="text-white text-h6 font-weight-bold">{{ server.name }}</h3>
          <div class="d-flex align-center ga-2 mt-1">
            <span class="material-symbols-outlined text-muted" style="font-size: 16px">lan</span>
            <span class="text-muted text-body-2 font-mono">{{ server.ip }}</span>
          </div>
        </div>
        <v-btn icon variant="text" size="small" color="secondary" @click="$emit('settings', server)">
          <span class="material-symbols-outlined">settings</span>
        </v-btn>
      </div>

      <!-- CPU Chart -->
      <div>
        <div class="d-flex justify-space-between text-caption text-muted mb-2">
          <div class="d-flex align-center ga-1">
            <span class="material-symbols-outlined" style="font-size: 14px">memory</span>
            <span>CPU Load ({{ cpu }}%)</span>
          </div>
          <span v-if="server.online" class="text-warning">Threshold: >90% (Auto-stop)</span>
          <span v-else>Auto-Start: 18:00 EST</span>
        </div>
        <div v-if="server.online" class="cpu-bars">
          <div v-for="(h, i) in cpuBars" :key="i" class="cpu-bar" :style="{ height: h + '%' }" />
        </div>
        <div v-else class="dormant-box">DORMANT</div>
      </div>

      <!-- Metrics -->
      <v-row dense>
        <v-col cols="4">
          <div class="metric-card">
            <div class="d-flex justify-space-between align-center text-muted mb-2">
              <div class="d-flex align-center ga-1">
                <span class="material-symbols-outlined" style="font-size: 14px">group</span>
                <span class="text-uppercase text-caption">Players</span>
              </div>
              <span class="text-white text-caption font-weight-bold">{{ players }}</span>
            </div>
            <v-progress-linear :model-value="(players / server.maxPlayers) * 100" color="blue" bg-color="white" bg-opacity="0.1" height="6" rounded />
            <div class="text-right text-caption text-grey mt-1">Max: {{ server.maxPlayers }}</div>
          </div>
        </v-col>
        <v-col cols="4">
          <div class="metric-card">
            <div class="d-flex justify-space-between align-center text-muted mb-2">
              <div class="d-flex align-center ga-1">
                <span class="material-symbols-outlined" style="font-size: 14px">hard_drive</span>
                <span class="text-uppercase text-caption">Memory</span>
              </div>
              <span class="text-white text-caption font-weight-bold">{{ memory }} GB</span>
            </div>
            <v-progress-linear :model-value="(memory / server.maxMemory) * 100" color="purple" bg-color="white" bg-opacity="0.1" height="6" rounded />
            <div class="text-right text-caption text-grey mt-1">of {{ server.maxMemory }} GB</div>
          </div>
        </v-col>
        <v-col cols="4">
          <div class="metric-card">
            <div class="d-flex align-center ga-1 text-muted mb-2">
              <span class="material-symbols-outlined" style="font-size: 14px">network_check</span>
              <span class="text-uppercase text-caption">Network</span>
            </div>
            <div class="d-flex justify-space-between text-caption mb-1">
              <span class="text-grey">↓ RX</span>
              <span class="text-white font-mono">{{ networkRx }}</span>
            </div>
            <div class="d-flex justify-space-between text-caption">
              <span class="text-grey">↑ TX</span>
              <span class="text-white font-mono">{{ networkTx }}</span>
            </div>
          </div>
        </v-col>
      </v-row>

      <!-- Last Update -->
      <div v-if="lastUpdate" class="text-caption text-muted text-right">
        <span class="material-symbols-outlined" style="font-size: 12px; vertical-align: middle">update</span>
        Updated {{ lastUpdate }}
      </div>

      <!-- Actions -->
      <v-divider class="border-green" />
      <v-row dense>
        <v-col cols="6" sm="3">
          <v-btn v-if="server.online" block color="error" variant="tonal" :loading="actionLoading" :disabled="actionLoading" @click="handleStop">
            <span class="material-symbols-outlined">stop_circle</span>
            <span class="ml-1">STOP</span>
          </v-btn>
          <v-btn v-else block color="primary" class="glow-primary" :loading="actionLoading" :disabled="actionLoading" @click="handleStart">
            <span class="material-symbols-outlined">play_arrow</span>
            <span class="ml-1">START</span>
          </v-btn>
        </v-col>
        <v-col cols="6" sm="3">
          <v-btn block variant="tonal" color="secondary" :disabled="!server.online || actionLoading">
            <span class="material-symbols-outlined" style="font-size: 18px">restart_alt</span>
            <span class="ml-1 text-caption">Restart</span>
          </v-btn>
        </v-col>
        <v-col cols="6" sm="3">
          <v-btn block variant="tonal" color="secondary" :disabled="actionLoading">
            <span class="material-symbols-outlined" style="font-size: 18px">schedule</span>
            <span class="ml-1 text-caption">Schedule</span>
          </v-btn>
        </v-col>
        <v-col cols="6" sm="3">
          <v-btn block variant="tonal" color="secondary" :disabled="actionLoading">
            <span class="material-symbols-outlined" style="font-size: 18px">speed</span>
            <span class="ml-1 text-caption">Limits</span>
          </v-btn>
        </v-col>
      </v-row>
    </div>
  </v-card>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  server: { type: Object, required: true },
  metrics: { type: Object, default: null }
})

const emit = defineEmits(['start', 'stop', 'settings'])

const actionLoading = ref(false)

const cpuBars = computed(() => {
  const bars = []
  for (let i = 0; i < 12; i++) {
    bars.push(Math.random() * 60 + 20)
  }
  return bars
})

const cpu = computed(() => props.metrics?.cpuStats || props.server.cpu || 0)
const memory = computed(() => {
  if (props.metrics?.memStats) return (props.metrics.memStats / 1024).toFixed(1)
  return props.server.memory || 0
})
const players = computed(() => props.metrics?.activeUsers ?? props.server.players ?? 0)
const networkRx = computed(() => {
  if (props.metrics?.networkStats) return `${(props.metrics.networkStats.rx / 1024 / 1024).toFixed(1)} MB/s`
  return props.server.rx || '0 KB/s'
})
const networkTx = computed(() => {
  if (props.metrics?.networkStats) return `${(props.metrics.networkStats.tx / 1024 / 1024).toFixed(1)} MB/s`
  return props.server.tx || '0 KB/s'
})
const lastUpdate = computed(() => {
  if (!props.metrics?.lastUpdate) return null
  const diff = Math.floor((Date.now() - props.metrics.lastUpdate.getTime()) / 1000)
  if (diff < 60) return `${diff}s ago`
  return `${Math.floor(diff / 60)}m ago`
})

const handleStart = async () => {
  actionLoading.value = true
  try {
    await emit('start', props.server)
  } finally {
    setTimeout(() => { actionLoading.value = false }, 2000)
  }
}

const handleStop = async () => {
  actionLoading.value = true
  try {
    await emit('stop', props.server)
  } finally {
    setTimeout(() => { actionLoading.value = false }, 2000)
  }
}
</script>

<style scoped lang="scss">
.server-hero {
  position: relative;
  height: 128px;
  background-size: cover;
  background-position: center;
  &.grayscale { filter: grayscale(1); }
}
.hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, #1c2e24, transparent);
}
.status-badge {
  position: absolute;
  top: 16px;
  right: 16px;
  font-weight: 700;
  font-size: 11px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #13ec5b;
  margin-right: 6px;
  &.offline { background: #6b7280; }
}
.cpu-bars {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 40px;
}
.cpu-bar {
  width: 6px;
  background: #13ec5b;
  border-radius: 2px;
  opacity: 0.7;
}
.dormant-box {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed rgba(255,255,255,0.1);
  border-radius: 8px;
  background: rgba(0,0,0,0.2);
  color: #6b7280;
  font-size: 10px;
  letter-spacing: 2px;
}
.metric-card {
  background: rgba(0,0,0,0.2);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 8px;
  padding: 12px;
}
.font-mono { font-family: monospace; }
</style>
