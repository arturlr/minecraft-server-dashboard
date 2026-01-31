<template>
  <v-card color="surface" class="border-green overflow-hidden" border="thin" :class="{ 'opacity-80': !isRunning }">
    <!-- Hero Image -->
    <div class="server-hero" :style="{ backgroundImage: `url(${server.image})` }" :class="{ grayscale: !isRunning }">
      <div class="hero-overlay" />
      <v-chip :color="statusColor" variant="flat" size="small" class="status-badge">
        <v-progress-circular v-if="isTransitioning" indeterminate size="12" width="2" class="mr-2" />
        <span v-else-if="isRunning" class="status-dot pulse" />
        <span v-else class="status-dot offline" />
        {{ statusText }}
      </v-chip>
    </div>

    <div class="pa-5 d-flex flex-column ga-5">
      <!-- Header -->
      <div class="d-flex justify-space-between align-start">
        <div class="d-flex align-center ga-3">
          <div class="d-flex ga-2">
            <v-btn 
              icon 
              variant="text"
              :loading="actionLoading" 
              :disabled="isDisabled" 
              @click="isRunning ? handleStop() : handleStart()"
            >
              <span class="material-symbols-outlined" :style="{ color: isRunning ? '#ef4444' : '#13ec5b' }">power_settings_new</span>
            </v-btn>
            <v-btn 
              icon 
              color="secondary"
              variant="tonal"
              :disabled="!isRunning || isDisabled"
              @click="handleRestart"
            >
              <span class="material-symbols-outlined">restart_alt</span>
            </v-btn>
            <v-btn 
              icon 
              color="secondary"
              variant="tonal"
              :disabled="!isRunning || isDisabled"
              @click="openLogsDialog"
            >
              <span class="material-symbols-outlined">description</span>
            </v-btn>
          </div>
          <div>
            <h3 class="text-white text-h6 font-weight-bold">{{ server.name }}</h3>
            <div v-if="isRunning" class="d-flex align-center ga-2 mt-1">
              <span class="material-symbols-outlined text-muted" style="font-size: 16px">lan</span>
              <span class="text-muted text-body-2 font-mono">{{ server.ip }}</span>
              <v-btn icon variant="text" size="x-small" @click="copyIpAddress">
                <span class="material-symbols-outlined" style="font-size: 14px">content_copy</span>
              </v-btn>
            </div>
          </div>
        </div>
        <v-btn icon variant="text" size="small" color="secondary" @click="$emit('settings', server)">
          <span class="material-symbols-outlined">settings</span>
        </v-btn>
      </div>

      <!-- Running Instance Metrics -->
      <template v-if="isRunning">
        <!-- CPU & Memory Charts -->
        <v-row dense>
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
        <v-row dense>
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
      </template>

      <!-- Inactive Instance Info -->
      <template v-else>
        <div class="inactive-panel">
          <div class="d-flex align-center justify-center ga-2 text-muted">
            <span class="material-symbols-outlined">power_settings_new</span>
            <span class="text-body-2">Server is currently offline</span>
          </div>
          <div v-if="server.instanceType" class="text-center text-caption text-muted mt-2">
            {{ server.instanceType }}
          </div>
        </div>
      </template>

      <!-- Actions -->
      <v-divider class="border-green" />
    </div>

    <!-- Logs Dialog -->
    <v-dialog v-model="logsDialog" max-width="800">
      <v-card>
        <v-card-title class="d-flex justify-space-between align-center">
          <span>Server Logs - {{ server.name }}</span>
          <v-btn icon variant="text" @click="logsDialog = false">
            <span class="material-symbols-outlined">close</span>
          </v-btn>
        </v-card-title>
        <v-card-text>
          <v-progress-linear v-if="logsLoading" indeterminate color="primary" />
          <v-alert v-else-if="logsError" type="error" variant="tonal">
            {{ logsError }}
          </v-alert>
          <pre v-else class="logs-content">{{ logs }}</pre>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" variant="text" @click="fetchLogs">Refresh</v-btn>
          <v-btn variant="text" @click="logsDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { generateClient } from 'aws-amplify/api'
import SparkLine from '../common/SparkLine.vue'
import { GET_SERVER_LOGS } from '@/graphql/queries'

const client = generateClient()

const props = defineProps({
  server: { type: Object, required: true },
  metrics: { type: Object, default: null },
  history: { type: Object, default: () => ({ cpu: [], mem: [], net: [], players: [] }) }
})

const emit = defineEmits(['start', 'stop', 'restart', 'settings'])

const actionLoading = ref(false)

// Logs dialog state
const logsDialog = ref(false)
const logs = ref('')
const logsLoading = ref(false)
const logsError = ref(null)

// Server state computed properties
const serverState = computed(() => props.server.state || 'stopped')
const isRunning = computed(() => serverState.value === 'running')
const isTransitioning = computed(() => ['pending', 'stopping', 'shutting-down'].includes(serverState.value))
const isDisabled = computed(() => actionLoading.value || isTransitioning.value)

// Reset loading state when server finishes transitioning
watch(isTransitioning, (transitioning) => {
  if (!transitioning) {
    actionLoading.value = false
  }
})

// Cleanup logs when dialog closes
watch(logsDialog, (isOpen) => {
  if (!isOpen) {
    logs.value = ''
    logsError.value = null
    logsLoading.value = false
  }
})

const statusText = computed(() => {
  const stateMap = {
    'running': 'ONLINE',
    'stopped': 'OFFLINE',
    'pending': 'STARTING',
    'stopping': 'STOPPING',
    'shutting-down': 'STOPPING'
  }
  return stateMap[serverState.value] || serverState.value.toUpperCase()
})

const statusColor = computed(() => {
  const colorMap = {
    'running': 'primary',
    'stopped': 'grey',
    'pending': 'warning',
    'stopping': 'warning',
    'shutting-down': 'warning'
  }
  return colorMap[serverState.value] || 'grey'
})

const cpu = computed(() => props.metrics?.cpuStats || props.server.cpu || 0)
const memory = computed(() => props.metrics?.memStats || 0)
const players = computed(() => props.metrics?.activeUsers ?? props.server.players ?? 0)
const networkRx = computed(() => {
  const net = props.history?.net
  if (!net || net.length === 0) return '0 KB/s'
  
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

const handleStart = () => {
  try {
    actionLoading.value = true
    emit('start', props.server)
  } catch (error) {
    console.error('Failed to start server:', error)
    actionLoading.value = false
  }
}

const handleStop = () => {
  try {
    actionLoading.value = true
    emit('stop', props.server)
  } catch (error) {
    console.error('Failed to stop server:', error)
    actionLoading.value = false
  }
}

const handleRestart = () => {
  try {
    actionLoading.value = true
    emit('restart', props.server)
  } catch (error) {
    console.error('Failed to restart server:', error)
    actionLoading.value = false
  }
}

const copyIpAddress = async () => {
  try {
    const port = props.server.port || '25565'
    const address = `${props.server.ip}:${port}`
    await navigator.clipboard.writeText(address)
  } catch (error) {
    console.error('Failed to copy IP address:', error)
  }
}

const fetchLogs = async () => {
  logsLoading.value = true
  logsError.value = null
  logs.value = ''
  
  try {
    const result = await client.graphql({
      query: GET_SERVER_LOGS,
      variables: {
        instanceId: props.server.id,
        lines: 50
      }
    })
    
    if (result?.data?.getServerLogs?.success) {
      logs.value = result.data.getServerLogs.logs || 'No logs available'
    } else {
      logsError.value = result?.data?.getServerLogs?.error || 'Failed to fetch logs'
    }
  } catch (error) {
    logsError.value = error.message || 'Failed to fetch logs'
  } finally {
    logsLoading.value = false
  }
}

const openLogsDialog = () => {
  logsDialog.value = true
  fetchLogs()
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
.inactive-panel {
  background: rgba(0,0,0,0.2);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 8px;
  padding: 24px;
}
.font-mono { font-family: monospace; }
.logs-content {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  max-height: 500px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
