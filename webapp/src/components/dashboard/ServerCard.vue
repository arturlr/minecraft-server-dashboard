<template>
  <v-card class="server-card">
    <div class="server-header">
      <div class="server-info">
        <div class="d-flex align-center ga-2 mb-1">
          <span class="status-dot" :class="statusClass" />
          <span class="server-name">{{ server.name }}</span>
          <span class="status-badge" :class="statusClass">{{ statusText }}</span>
        </div>
        <div v-if="isRunning" class="server-ip-container">
          <span class="server-ip">{{ server.ip }}</span>
          <v-btn 
            icon 
            size="x-small"
            variant="text"
            @click="copyAddress"
          >
            <span class="material-symbols-outlined" style="font-size: 16px;">content_copy</span>
          </v-btn>
        </div>
      </div>
      <div class="server-actions">
        <v-btn 
          icon 
          size="small"
          variant="text"
          :loading="actionLoading" 
          :disabled="isDisabled" 
          @click="isRunning ? confirmStop = true : confirmStart = true"
        >
          <span class="material-symbols-outlined">power_settings_new</span>
        </v-btn>
        <v-btn 
          icon 
          size="small"
          variant="text"
          :disabled="!isRunning || isDisabled"
          @click="$emit('settings', server)"
        >
          <span class="material-symbols-outlined">settings</span>
        </v-btn>
      </div>
    </div>

    <template v-if="isRunning">
      <div v-if="shutdownPattern" class="shutdown-info">
        <span class="material-symbols-outlined" style="font-size: 14px;">schedule</span>
        <span>{{ shutdownPattern }}</span>
      </div>
      <div class="metrics-grid">
        <div class="metric">
          <div class="metric-label">CPU</div>
          <div class="metric-value">{{ cpu.toFixed(0) }}%</div>
          <SparkLine :data="history.cpu" :width="120" :height="32" color="#171717" />
        </div>
        <div class="metric">
          <div class="metric-label">Memory</div>
          <div class="metric-value">{{ memory.toFixed(0) }}%</div>
          <SparkLine :data="history.mem" :width="120" :height="32" color="#171717" />
        </div>
        <div class="metric">
          <div class="metric-label">Players</div>
          <div class="metric-value">{{ players }}</div>
        </div>
        <div class="metric">
          <div class="metric-label">Network</div>
          <div class="metric-value">{{ networkRx }}</div>
        </div>
      </div>
    </template>

    <div v-else class="offline-state">
      {{ statusText }}
    </div>

    <v-dialog v-model="confirmStart" max-width="400">
      <v-card>
        <v-card-title>Start Server?</v-card-title>
        <v-card-text>Start {{ server.name }}?</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="confirmStart = false">Cancel</v-btn>
          <v-btn color="#171717" @click="handleStart">Start</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="confirmStop" max-width="400">
      <v-card>
        <v-card-title>Stop Server?</v-card-title>
        <v-card-text>Stop {{ server.name }}? Active players will be disconnected.</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="confirmStop = false">Cancel</v-btn>
          <v-btn color="error" @click="handleStop">Stop</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import SparkLine from '../common/SparkLine.vue'

const props = defineProps({
  server: { type: Object, required: true },
  metrics: { type: Object, default: null },
  history: { type: Object, default: () => ({ cpu: [], mem: [], net: [], players: [] }) },
  config: { type: Object, default: null }
})

const emit = defineEmits(['start', 'stop', 'restart', 'settings'])

const actionLoading = ref(false)
const confirmStart = ref(false)
const confirmStop = ref(false)
const copied = ref(false)

const serverState = computed(() => props.server.state || 'stopped')
const isRunning = computed(() => serverState.value === 'running')
const isTransitioning = computed(() => ['pending', 'stopping', 'shutting-down'].includes(serverState.value))
const isDisabled = computed(() => actionLoading.value || isTransitioning.value)

const statusClass = computed(() => {
  if (isRunning.value) return 'online'
  if (isTransitioning.value) return 'warning'
  return 'offline'
})

const statusText = computed(() => {
  const stateMap = {
    'running': 'Running',
    'stopped': 'Stopped',
    'pending': 'Starting',
    'stopping': 'Stopping',
    'shutting-down': 'Shutting down'
  }
  return stateMap[serverState.value] || serverState.value
})

watch(isTransitioning, (transitioning) => {
  if (!transitioning) actionLoading.value = false
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

const handleStart = () => {
  confirmStart.value = false
  actionLoading.value = true
  emit('start', props.server)
}

const handleStop = () => {
  confirmStop.value = false
  actionLoading.value = true
  emit('stop', props.server)
}

const copyAddress = async () => {
  try {
    await navigator.clipboard.writeText(props.server.ip)
    copied.value = true
    setTimeout(() => copied.value = false, 2000)
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

const shutdownPattern = computed(() => {
  if (!props.config) return null
  
  const patterns = []
  if (props.config.alarmThreshold > 0) {
    patterns.push(`CPU < ${props.config.alarmThreshold}%`)
  }
  if (props.config.stopScheduleExpression && props.config.stopScheduleExpression.trim()) {
    patterns.push('Scheduled')
  }
  
  console.log('Shutdown pattern for', props.server.name, ':', patterns, props.config)
  return patterns.length > 0 ? `Auto-shutdown: ${patterns.join(' • ')}` : null
})
</script>

<style scoped>
.server-card {
  padding: 24px;
  border: 1px solid #e5e5e5;
}
.server-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}
.server-info {
  flex: 1;
}
.server-name {
  font-size: 18px;
  font-weight: 500;
  color: #171717;
}
.server-ip {
  font-size: 13px;
  color: #737373;
  font-family: monospace;
}
.server-ip-container {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
}
.server-actions {
  display: flex;
  gap: 4px;
}
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}
.metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.metric-label {
  font-size: 11px;
  font-weight: 500;
  color: #a3a3a3;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.metric-value {
  font-size: 24px;
  font-weight: 300;
  color: #171717;
  line-height: 1;
  margin-bottom: 8px;
}
.offline-state {
  padding: 32px 0;
  text-align: center;
  font-size: 13px;
  color: #a3a3a3;
}
.status-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.status-badge.online {
  background: #dcfce7;
  color: #166534;
}
.status-badge.warning {
  background: #fef3c7;
  color: #92400e;
}
.status-badge.offline {
  background: #f5f5f5;
  color: #737373;
}
.shutdown-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #737373;
  margin-bottom: 16px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 6px;
}
</style>
