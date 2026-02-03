<template>
  <div class="settings-view">
    <div class="settings-content">
      <header class="settings-header">
        <div class="header-content">
          <div class="header-info">
            <div class="server-title">
              <h2>{{ serverName }}</h2>
              <span class="status-dot" :class="{ online: isOnline }" />
            </div>
            <div class="server-meta">{{ serverInfo }}</div>
          </div>
          <div class="header-actions">
            <v-btn variant="text" @click="$router.push('/')">Cancel</v-btn>
            <v-btn variant="outlined" :disabled="!isOnline" @click="handleRestart">
              <span class="material-symbols-outlined">restart_alt</span>
            </v-btn>
            <v-btn color="#171717" :loading="saving" @click="saveConfig">
              <span class="material-symbols-outlined">save</span>
              Save
            </v-btn>
          </div>
        </div>
      </header>

      <v-progress-linear v-if="loading" indeterminate color="#171717" />
      
      <div class="settings-body">
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
      </div>

      <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
        {{ snackbar.text }}
      </v-snackbar>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useServerStore } from '../stores/server'
import GeneralProperties from '../components/settings/GeneralProperties.vue'
import ResourceWatchdog from '../components/settings/ResourceWatchdog.vue'
import TaskScheduler from '../components/settings/TaskScheduler.vue'
import AccessControlSection from '../components/settings/AccessControlSection.vue'
import SparkLine from '../components/common/SparkLine.vue'

const route = useRoute()
const router = useRouter()
const serverStore = useServerStore()

const serverId = computed(() => route.params.id)
const server = computed(() => serverStore.getServerById(serverId.value))
const serverName = computed(() => server.value?.name || serverId.value)
const isOnline = computed(() => server.value?.state === 'running')
const serverInfo = computed(() => {
  if (!server.value) return 'Loading...'
  return `IP: ${server.value.publicIp || 'Not assigned'}`
})

const metrics = computed(() => serverStore.getMetricsById(serverId.value))
const history = computed(() => serverStore.getMetricsHistory(serverId.value))

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
  if (!serverId.value) return
  loading.value = true
  try {
    const serverConfig = await serverStore.getServerConfig(serverId.value)
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
    const configToSave = {
      id: serverId.value,
      ...config.value
    }
    console.log('Saving config:', configToSave)
    await serverStore.putServerConfig(configToSave)
    snackbar.value = { show: true, text: 'Settings saved successfully', color: 'success' }
    setTimeout(() => router.push('/'), 1500)
  } catch (e) {
    console.error('Failed to save config:', e)
    snackbar.value = { show: true, text: 'Failed to save settings', color: 'error' }
  } finally {
    saving.value = false
  }
}

const handleRestart = async () => {
  try {
    await serverStore.restartServer(serverId.value)
  } catch (e) {
    console.error('Failed to restart:', e)
  }
}

onMounted(() => {
  if (serverId.value) {
    serverStore.setSelectedServer(serverId.value)
    if (!server.value) {
      serverStore.ec2Discovery()
    }
    loadConfig()
  }
})
</script>

<style scoped>
.settings-view {
  min-height: 100vh;
  background: white;
}
.settings-content {
  width: 100%;
  display: flex;
  flex-direction: column;
}
.settings-header {
  padding: 24px 32px;
  border-bottom: 1px solid #e5e5e5;
}
.header-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
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
  font-size: 24px;
  font-weight: 500;
  color: #171717;
  margin: 0;
}
.server-meta {
  font-size: 13px;
  color: #737373;
}
.header-actions {
  display: flex;
  gap: 12px;
}
.settings-body {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
}
.settings-body > * {
  max-width: 1200px;
  margin: 0 auto 48px;
}
.settings-body > *:last-child {
  margin-bottom: 0;
}
.settings-section {
  margin-bottom: 48px;
}
.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e5e5;
}
.section-header .material-symbols-outlined {
  font-size: 20px;
  color: #171717;
}
.section-header h3 {
  font-size: 16px;
  font-weight: 500;
  color: #171717;
  margin: 0;
}
.specs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}
.spec-card {
  padding: 20px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}
.spec-card .material-symbols-outlined {
  font-size: 24px;
  color: #171717;
  margin-bottom: 12px;
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
  font-size: 18px;
  font-weight: 500;
  color: #171717;
}
.spec-value.mono {
  font-family: monospace;
  font-size: 14px;
}
.automation-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}
.metric-card {
  padding: 20px;
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
  font-size: 24px;
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
</style>
