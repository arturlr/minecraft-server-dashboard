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

      <!-- CPU & Memory Charts -->
      <v-row dense :class="{ 'opacity-50': !server.online }">
        <v-col cols="6">
          <div class="metric-card">
            <div class="d-flex justify-space-between text-caption text-muted mb-2">
              <div class="d-flex align-center ga-1">
                <span class="material-symbols-outlined" style="font-size: 14px">memory</span>
                <span>CPU ({{ cpu.toFixed(1) }}%)</span>
              </div>
              <span v-if="lastUpdate" class="text-grey">{{ lastUpdate }}</span>
            </div>
            <SparkLine :data="history.cpu" :width="130" :height="36" color="#13ec5b" />
          </div>
        </v-col>
        <v-col cols="6">
          <div class="metric-card">
            <div class="d-flex justify-space-between text-caption text-muted mb-2">
              <div class="d-flex align-center ga-1">
                <span class="material-symbols-outlined" style="font-size: 14px">hard_drive</span>
                <span>Memory ({{ memory.toFixed(1) }}%)</span>
              </div>
            </div>
            <SparkLine :data="history.mem" :width="130" :height="36" color="#a855f7" />
          </div>
        </v-col>
      </v-row>

      <!-- Metrics -->
      <v-row dense :class="{ 'opacity-50': !server.online }">
        <v-col cols="6">
          <div class="metric-card">
            <div class="d-flex justify-space-between align-center text-muted mb-1">
              <div class="d-flex align-center ga-1">
                <span class="material-symbols-outlined" style="font-size: 14px">group</span>
                <span class="text-uppercase text-caption">Players</span>
              </div>
              <span class="text-white text-caption font-weight-bold">{{ players }}</span>
            </div>
            <SparkLine :data="history.players || []" :width="110" :height="24" color="#60a5fa" />
          </div>
        </v-col>
        <v-col cols="6">
          <div class="metric-card">
            <div class="d-flex justify-space-between align-center text-muted mb-1">
              <div class="d-flex align-center ga-1">
                <span class="material-symbols-outlined" style="font-size: 14px">network_check</span>
                <span class="text-uppercase text-caption">Network</span>
              </div>
              <span class="text-white text-caption font-weight-bold">{{ networkRx }}</span>
            </div>
            <SparkLine :data="history.net" :width="110" :height="24" color="#3b82f6" />
          </div>
        </v-col>
      </v-row>

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
import SparkLine from '../common/SparkLine.vue'

const props = defineProps({
  server: { type: Object, required: true },
  metrics: { type: Object, default: null },
  history: { type: Object, default: () => ({ cpu: [], mem: [], net: [] }) }
})

const emit = defineEmits(['start', 'stop', 'settings'])

const actionLoading = ref(false)

const cpu = computed(() => props.metrics?.cpuStats || props.server.cpu || 0)
const memory = computed(() => props.metrics?.memStats || 0)
const players = computed(() => props.metrics?.activeUsers ?? props.server.players ?? 0)
const networkRx = computed(() => {
  const net = props.history?.net || []
  if (net.length === 0) return '0 KB/s'
  const latest = net[net.length - 1] || 0
  if (latest > 1024 * 1024) return `${(latest / 1024 / 1024).toFixed(1)} MB/s`
  if (latest > 1024) return `${(latest / 1024).toFixed(1)} KB/s`
  return `${latest.toFixed(0)} B/s`
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
.metric-card {
  background: rgba(0,0,0,0.2);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 8px;
  padding: 12px;
}
.font-mono { font-family: monospace; }
</style>
