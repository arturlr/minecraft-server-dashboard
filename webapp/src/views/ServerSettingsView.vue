<template>
  <div class="d-flex h-100">
    <SettingsSidebar />
    
    <v-main class="bg-background">
      <!-- Header -->
      <header class="px-8 py-6 border-b border-green bg-background">
        <div class="d-flex flex-wrap align-center justify-space-between ga-4" style="max-width: 1200px; margin: 0 auto">
          <div>
            <div class="d-flex align-center ga-3">
              <h2 class="text-white text-h4 font-weight-black">{{ serverName }}</h2>
              <v-chip :color="isOnline ? 'primary' : 'grey'" variant="tonal" size="small">
                <span class="status-dot mr-1" :class="{ pulse: isOnline }" />
                {{ isOnline ? 'Online' : 'Offline' }}
              </v-chip>
            </div>
            <p class="text-muted text-body-2 mt-1">{{ serverInfo }}</p>
          </div>
          <div class="d-flex ga-3">
            <v-btn variant="text" color="secondary" @click="$router.push('/')">
              Cancel
            </v-btn>
            <v-btn variant="outlined" color="white" :disabled="!isOnline" @click="handleRestart">
              <span class="material-symbols-outlined mr-2" style="font-size: 18px">restart_alt</span>
              Restart
            </v-btn>
            <v-btn color="primary" class="glow-primary" :loading="saving" @click="saveConfig">
              <span class="material-symbols-outlined mr-2" style="font-size: 18px">save</span>
              Save Changes
            </v-btn>
          </div>
        </div>
      </header>

      <!-- Content -->
      <v-progress-linear v-if="loading" indeterminate color="primary" />
      
      <div class="pa-8" style="max-width: 1200px; margin: 0 auto">
        <div class="d-flex flex-column ga-10">
          <!-- Server Specs -->
          <div>
            <div class="d-flex align-center ga-2 mb-5 pb-3 border-b border-green">
              <span class="material-symbols-outlined text-primary">dns</span>
              <h3 class="text-white text-h6 font-weight-bold">Server Specifications</h3>
            </div>
            <v-row>
              <v-col cols="6" sm="3">
                <div class="spec-card">
                  <span class="material-symbols-outlined text-primary mb-2">memory</span>
                  <p class="text-muted text-caption">vCPUs</p>
                  <p class="text-white text-h6 font-weight-bold">{{ server?.vCpus || '-' }}</p>
                </div>
              </v-col>
              <v-col cols="6" sm="3">
                <div class="spec-card">
                  <span class="material-symbols-outlined text-primary mb-2">hard_drive</span>
                  <p class="text-muted text-caption">Memory</p>
                  <p class="text-white text-h6 font-weight-bold">{{ server?.memSize ? (server.memSize / 1024).toFixed(1) : '-' }} GB</p>
                </div>
              </v-col>
              <v-col cols="6" sm="3">
                <div class="spec-card">
                  <span class="material-symbols-outlined text-primary mb-2">storage</span>
                  <p class="text-muted text-caption">Disk</p>
                  <p class="text-white text-h6 font-weight-bold">{{ server?.diskSize || '-' }} GB</p>
                </div>
              </v-col>
              <v-col cols="6" sm="3">
                <div class="spec-card">
                  <span class="material-symbols-outlined text-primary mb-2">lan</span>
                  <p class="text-muted text-caption">Public IP</p>
                  <p class="text-white text-body-2 font-weight-bold font-mono">{{ server?.publicIp || 'Not assigned' }}</p>
                </div>
              </v-col>
            </v-row>
          </div>

          <GeneralProperties v-model="config" />

          <div>
            <div class="d-flex align-center ga-2 mb-5 pb-3 border-b border-green">
              <span class="material-symbols-outlined text-primary">bolt</span>
              <h3 class="text-white text-h6 font-weight-bold">Automation & Performance</h3>
            </div>
            <v-row>
              <v-col cols="12" lg="6">
                <ResourceWatchdog v-model="config" />
              </v-col>
              <v-col cols="12" lg="6">
                <TaskScheduler v-model="config" />
              </v-col>
            </v-row>
          </div>

          <AccessControlSection :server-id="serverId" />
        </div>
      </div>

      <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
        {{ snackbar.text }}
      </v-snackbar>
    </v-main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useServerStore } from '../stores/server'
import SettingsSidebar from '../components/settings/SettingsSidebar.vue'
import GeneralProperties from '../components/settings/GeneralProperties.vue'
import ResourceWatchdog from '../components/settings/ResourceWatchdog.vue'
import TaskScheduler from '../components/settings/TaskScheduler.vue'
import AccessControlSection from '../components/settings/AccessControlSection.vue'

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
    await serverStore.putServerConfig({
      id: serverId.value,
      ...config.value
    })
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
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.spec-card {
  background: #1c2e24;
  border: 1px solid #28392e;
  border-radius: 12px;
  padding: 16px;
  text-align: center;
}
.font-mono {
  font-family: monospace;
}
</style>
