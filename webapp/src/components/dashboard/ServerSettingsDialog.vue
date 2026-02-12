<template>
  <v-card>
    <v-card-title class="dialog-header">
      <div class="header-info">
        <div class="server-title">
          <h2>{{ serverName }}</h2>
          <span class="status-dot" :class="{ online: isOnline }" />
        </div>
        <div class="server-meta">{{ serverInfo }}</div>
      </div>
      <div class="header-actions">
        <v-btn icon variant="text" size="small" @click="$emit('close')">
          <span class="material-symbols-outlined">close</span>
        </v-btn>
      </div>
    </v-card-title>

    <v-progress-linear v-if="loading" indeterminate color="#171717" />

    <v-card-text class="dialog-content">
      <div v-if="isOnline" class="settings-section">
        <div class="section-header">
          <span class="material-symbols-outlined">monitoring</span>
          <h3>Performance Metrics</h3>
        </div>
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-header">
              <div class="metric-label">CPU</div>
              <div class="metric-value">{{ cpu.toFixed(0) }}%</div>
            </div>
            <SparkLine :data="history.cpu" :width="240" :height="60" color="#171717" />
          </div>
          <div class="metric-card">
            <div class="metric-header">
              <div class="metric-label">Memory</div>
              <div class="metric-value">{{ memory.toFixed(0) }}%</div>
            </div>
            <SparkLine :data="history.mem" :width="240" :height="60" color="#171717" />
          </div>
          <div class="metric-card">
            <div class="metric-header">
              <div class="metric-label">Players</div>
              <div class="metric-value">{{ players }}</div>
            </div>
            <SparkLine :data="history.players" :width="240" :height="60" color="#171717" />
          </div>
          <div class="metric-card">
            <div class="metric-header">
              <div class="metric-label">Network</div>
              <div class="metric-value">{{ networkRx }}</div>
            </div>
            <SparkLine :data="history.net" :width="240" :height="60" color="#171717" />
          </div>
        </div>
      </div>

      <div v-if="isOnline" class="settings-section">
        <div class="section-header">
          <span class="material-symbols-outlined">description</span>
          <h3>Server Logs</h3>
          <v-btn 
            size="small" 
            variant="text" 
            :loading="logsLoading"
            @click="fetchLogs"
          >
            <span class="material-symbols-outlined">refresh</span>
            Refresh
          </v-btn>
        </div>
        <div class="logs-container">
          <div v-if="logsError" class="logs-error">
            <span class="material-symbols-outlined">error</span>
            {{ logsError }}
          </div>
          <pre v-else-if="logs" class="logs-content">{{ logs }}</pre>
          <div v-else class="logs-empty">
            Click refresh to load logs
          </div>
        </div>
      </div>

      <div class="settings-section">
        <div class="section-header">
          <span class="material-symbols-outlined">dns</span>
          <h3>Server Specifications</h3>
        </div>
        <div class="specs-grid">
          <div class="spec-card">
            <span class="material-symbols-outlined">memory</span>
            <div class="spec-label">vCPUs</div>
            <div class="spec-value">{{ server?.vCpus || '-' }}</div>
          </div>
          <div class="spec-card">
            <span class="material-symbols-outlined">hard_drive</span>
            <div class="spec-label">Memory</div>
            <div class="spec-value">{{ server?.memSize ? (server.memSize / 1024).toFixed(1) : '-' }} GB</div>
          </div>
          <div class="spec-card">
            <span class="material-symbols-outlined">storage</span>
            <div class="spec-label">Disk</div>
            <div class="spec-value">{{ server?.diskSize || '-' }} GB</div>
          </div>
          <div class="spec-card">
            <span class="material-symbols-outlined">lan</span>
            <div class="spec-label">Public IP</div>
            <div class="spec-value mono">{{ server?.publicIp || 'Not assigned' }}</div>
          </div>
        </div>
      </div>

      <GeneralProperties v-model="config" />

      <div class="settings-section">
        <div class="section-header">
          <span class="material-symbols-outlined">bolt</span>
          <h3>Automation</h3>
        </div>
        <div class="automation-grid">
          <ResourceWatchdog v-model="config" />
          <TaskScheduler v-model="config" />
        </div>
      </div>

      <AccessControlSection :server-id="serverId" />
    </v-card-text>

    <v-card-actions class="dialog-actions">
      <v-btn variant="text" @click="$emit('close')">Cancel</v-btn>
      <v-btn variant="outlined" :disabled="!isOnline" @click="handleRestart">
        <span class="material-symbols-outlined">restart_alt</span>
        Restart
      </v-btn>
      <v-btn color="#171717" :loading="saving" @click="saveConfig">
        <span class="material-symbols-outlined">save</span>
        Save
      </v-btn>
    </v-card-actions>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useServerStore } from '../../stores/server'
import GeneralProperties from '../settings/GeneralProperties.vue'
import ResourceWatchdog from '../settings/ResourceWatchdog.vue'
import TaskScheduler from '../settings/TaskScheduler.vue'
import AccessControlSection from '../settings/AccessControlSection.vue'
import SparkLine from '../common/SparkLine.vue'

const props = defineProps({ serverId: String })
const emit = defineEmits(['close'])

const serverStore = useServerStore()

const server = computed(() => serverStore.getServerById(props.serverId))
const serverName = computed(() => server.value?.name || props.serverId)
const isOnline = computed(() => server.value?.state === 'running')
const serverInfo = computed(() => {
  if (!server.value) return 'Loading...'
  return `IP: ${server.value.publicIp || 'Not assigned'}`
})

const metrics = computed(() => serverStore.getMetricsById(props.serverId))
const history = computed(() => serverStore.getMetricsHistory(props.serverId))

const cpu = computed(() => metrics.value?.cpuStats || 0)
const memory = computed(() => metrics.value?.memStats || 0)
const players = computed(() => metrics.value?.activeUsers ?? 0)
const networkRx = computed(() => {
  const net = history.value?.net
  if (!net || net.length === 0) return '0 KB/s'
  const latest = net[net.length - 1] || 0
  if (latest > 1024 * 1024) return `${(latest / 1024 / 1024).toFixed(1)} MB/s`
  if (latest > 1024) return `${(latest / 1024).toFixed(1)} KB/s`
  return `${latest.toFixed(0)} B/s`
})

const loading = ref(false)
const saving = ref(false)
const logsLoading = ref(false)
const logs = ref('')
const logsError = ref('')
const snackbar = ref({ show: false, text: '', color: 'success' })
const config = ref({
  id: '',
  runCommand: '',
  workDir: '',
  alarmThreshold: 0,
  alarmEvaluationPeriod: 10,
  stopScheduleExpression: '',
  startScheduleExpression: '',
  timezone: 'America/New_York'
})

const loadConfig = async () => {
  if (!props.serverId) return
  loading.value = true
  try {
    const serverConfig = await serverStore.getServerConfig(props.serverId)
    if (serverConfig) {
      config.value = { ...config.value, ...serverConfig }
    }
  } catch (e) {
    console.error('Failed to load config:', e)
  } finally {
    loading.value = false
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    await serverStore.putServerConfig({
      id: props.serverId,
      ...config.value
    })
    snackbar.value = { show: true, text: 'Settings saved', color: 'success' }
    setTimeout(() => emit('close'), 1000)
  } catch (e) {
    console.error('Failed to save config:', e)
    snackbar.value = { show: true, text: 'Failed to save', color: 'error' }
  } finally {
    saving.value = false
  }
}

const handleRestart = async () => {
  try {
    await serverStore.restartServer(props.serverId)
    snackbar.value = { show: true, text: 'Restarting server...', color: 'success' }
  } catch (e) {
    console.error('Failed to restart:', e)
  }
}

const fetchLogs = async () => {
  if (!props.serverId) return
  logsLoading.value = true
  logsError.value = ''
  try {
    const result = await serverStore.getServerLogs(props.serverId, 100)
    if (result.success) {
      logs.value = result.logs
    } else {
      logsError.value = result.error || 'Failed to fetch logs'
    }
  } catch (e) {
    console.error('Failed to fetch logs:', e)
    logsError.value = e.message || 'Failed to fetch logs'
  } finally {
    logsLoading.value = false
  }
}

onMounted(loadConfig)
</script>

<style scoped>
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px;
  border-bottom: 1px solid #e5e5e5;
}
.header-info {
  flex: 1;
}
.server-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}
.server-title h2 {
  font-size: 20px;
  font-weight: 500;
  color: #171717;
  margin: 0;
}
.server-meta {
  font-size: 13px;
  color: #737373;
}
.dialog-content {
  max-height: 70vh;
  overflow-y: auto;
}
.dialog-actions {
  padding: 16px 24px;
  border-top: 1px solid #e5e5e5;
  gap: 12px;
}
.settings-section {
  margin-bottom: 32px;
}
.settings-section:last-child {
  margin-bottom: 0;
}
.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e5e5;
}
.section-header .material-symbols-outlined {
  font-size: 20px;
  color: #171717;
}
.section-header h3 {
  font-size: 15px;
  font-weight: 500;
  color: #171717;
  margin: 0;
}
.specs-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.spec-card {
  padding: 16px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}
.spec-card .material-symbols-outlined {
  font-size: 20px;
  color: #171717;
  margin-bottom: 8px;
}
.spec-label {
  font-size: 11px;
  font-weight: 500;
  color: #a3a3a3;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}
.spec-value {
  font-size: 16px;
  font-weight: 500;
  color: #171717;
}
.spec-value.mono {
  font-family: monospace;
  font-size: 12px;
}
.automation-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.metric-card {
  padding: 16px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
}
.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 12px;
}
.metric-label {
  font-size: 11px;
  font-weight: 500;
  color: #a3a3a3;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.metric-value {
  font-size: 20px;
  font-weight: 300;
  color: #171717;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d4d4d4;
}
.status-dot.online {
  background: #22c55e;
}
.logs-container {
  background: #fafafa;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  padding: 16px;
  max-height: 400px;
  overflow-y: auto;
}
.logs-content {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #171717;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}
.logs-error {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #ef4444;
  font-size: 14px;
}
.logs-empty {
  color: #a3a3a3;
  font-size: 14px;
  text-align: center;
  padding: 32px;
}
</style>
