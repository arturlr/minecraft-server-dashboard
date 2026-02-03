<template>
  <AppLayout title="Dashboard">
    <StatsCards 
      :online="onlineCount" 
      :total="servers.length" 
      :players="totalPlayers" 
      class="mb-12" 
    />

    <div class="section-header">
      <h2 class="section-title">Servers</h2>
      <v-text-field
        v-model="search"
        placeholder="Search..."
        density="compact"
        hide-details
        style="max-width: 240px"
      />
    </div>

    <v-progress-linear v-if="loading" indeterminate height="1" class="mb-8" />

    <v-row>
      <v-col v-for="server in filteredServers" :key="server.id" cols="12" lg="6">
        <ServerCard 
          :server="mapServer(server)" 
          :metrics="serverStore.getMetricsById(server.id)"
          :history="serverStore.getMetricsHistory(server.id)"
          @settings="goToSettings"
          @start="handleStart"
          @stop="handleStop"
        />
      </v-col>
    </v-row>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000" location="bottom">
      {{ snackbar.text }}
    </v-snackbar>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useServerStore } from '../stores/server'
import AppLayout from '../components/layout/AppLayout.vue'
import StatsCards from '../components/dashboard/StatsCards.vue'
import ServerCard from '../components/dashboard/ServerCard.vue'

const router = useRouter()
const serverStore = useServerStore()
const search = ref('')

const servers = computed(() => serverStore.servers)
const loading = computed(() => serverStore.loading)
const onlineCount = computed(() => serverStore.onlineServers.length)
const totalPlayers = computed(() => serverStore.totalPlayers)

const filteredServers = computed(() => {
  if (!search.value) return servers.value
  return servers.value.filter(s => 
    s.name?.toLowerCase().includes(search.value.toLowerCase()) ||
    s.id.toLowerCase().includes(search.value.toLowerCase())
  )
})

const mapServer = (server) => ({
  id: server.id,
  name: server.name || server.id,
  publicIp: server.publicIp ? `${server.publicIp}:25565` : 'Not assigned',
  ip: server.publicIp ? `${server.publicIp}:25565` : 'Not assigned',
  state: server.state || 'stopped',
  online: server.state === 'running',
  cpu: server.cpuStats || 0,
  players: server.activeUsers || 0,
  maxPlayers: 20,
  memory: server.memSize ? (server.memSize / 1024).toFixed(1) : 0,
  maxMemory: server.memSize ? Math.ceil(server.memSize / 1024) : 8,
})

const snackbar = ref({ show: false, text: '', color: 'success' })

const showNotification = (text, color = 'success') => {
  snackbar.value = { show: true, text, color }
}

const goToSettings = (server) => {
  serverStore.setSelectedServer(server.id)
  router.push({ name: 'server-settings', params: { id: server.id } })
}

const handleStart = async (server) => {
  try {
    await serverStore.startServer(server.id)
    serverStore.updateServerState(server.id, 'pending')
    showNotification(`Starting ${server.name}...`)
  } catch (e) {
    showNotification('Failed to start server', 'error')
  }
}

const handleStop = async (server) => {
  try {
    await serverStore.stopServer(server.id)
    serverStore.updateServerState(server.id, 'stopping')
    showNotification(`Stopping ${server.name}...`)
  } catch (e) {
    showNotification('Failed to stop server', 'error')
  }
}

onMounted(() => {
  serverStore.ec2Discovery()
  serverStore.subscribeToStateChanges()
})

watch(() => serverStore.onlineServers, (onlineServers) => {
  onlineServers.forEach(server => {
    serverStore.subscribeToMetrics(server.id)
  })
}, { immediate: true })

onUnmounted(() => {
  serverStore.unsubscribeAll()
})
</script>

<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.section-title {
  font-size: 20px;
  font-weight: 500;
  color: #171717;
}
</style>
