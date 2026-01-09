<template>
  <AppLayout title="Command Center">
    <!-- Stats -->
    <StatsCards 
      :online="onlineCount" 
      :total="servers.length" 
      :players="totalPlayers" 
      class="mb-8" 
    />

    <!-- Active Instances -->
    <div class="mb-8">
      <div class="d-flex flex-wrap align-center justify-space-between ga-4 mb-4">
        <h2 class="text-white text-h5 font-weight-bold">Active Instances</h2>
        <v-text-field
          v-model="search"
          placeholder="Search servers by name..."
          prepend-inner-icon="mdi-magnify"
          density="compact"
          hide-details
          class="search-field"
          style="max-width: 400px"
        />
        <v-btn variant="text" color="primary" size="small">
          View All
          <span class="material-symbols-outlined ml-1" style="font-size: 16px">arrow_forward</span>
        </v-btn>
      </div>

      <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

      <v-row>
        <v-col v-for="server in filteredServers" :key="server.id" cols="12" xl="6">
          <ServerCard 
            :server="mapServer(server)" 
            :metrics="serverStore.getMetricsById(server.id)"
            @settings="goToSettings"
            @start="handleStart"
            @stop="handleStop"
          />
        </v-col>
      </v-row>

      <v-alert v-if="!loading && servers.length === 0" type="info" variant="tonal" class="mt-4">
        No servers found. Create a new instance to get started.
      </v-alert>
    </div>

    <!-- Access Control -->
    <div>
      <div class="d-flex flex-wrap align-center justify-space-between ga-4 mb-4">
        <div>
          <h2 class="text-white text-h5 font-weight-bold">Access Control</h2>
          <p class="text-muted text-body-2 mt-1">Manage users who have access to the dashboard.</p>
        </div>
        <v-btn variant="tonal" color="white">
          <span class="material-symbols-outlined mr-2" style="font-size: 18px">person_add</span>
          Invite Member
        </v-btn>
      </div>
      <AccessControlTable :users="users" />
    </div>

    <!-- Snackbar for notifications -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useServerStore } from '../stores/server'
import { useUserStore } from '../stores/user'
import AppLayout from '../components/layout/AppLayout.vue'
import StatsCards from '../components/dashboard/StatsCards.vue'
import ServerCard from '../components/dashboard/ServerCard.vue'
import AccessControlTable from '../components/dashboard/AccessControlTable.vue'

const router = useRouter()
const serverStore = useServerStore()
const userStore = useUserStore()
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

// Map API server data to ServerCard format
const mapServer = (server) => ({
  id: server.id,
  name: server.name || server.id,
  ip: server.publicIp ? `${server.publicIp}:25565` : 'Not assigned',
  online: server.state === 'running',
  cpu: server.cpuStats || 0,
  players: server.activeUsers || 0,
  maxPlayers: 20,
  memory: server.memSize ? (server.memSize / 1024).toFixed(1) : 0,
  maxMemory: server.memSize ? Math.ceil(server.memSize / 1024) : 8,
  rx: '0 KB/s',
  tx: '0 KB/s',
  image: 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=600&q=80'
})

const users = ref([])
const loadingUsers = ref(false)
const snackbar = ref({ show: false, text: '', color: 'success' })

const showNotification = (text, color = 'success') => {
  snackbar.value = { show: true, text, color }
}

const loadAdminUsers = async () => {
  loadingUsers.value = true
  try {
    const adminUsers = await serverStore.getAdminUsers()
    users.value = adminUsers.map(u => ({
      name: u.fullName || u.email,
      email: u.email,
      role: 'Administrator',
      lastActive: '-',
      color: 'primary'
    }))
  } catch (e) {
    console.error('Failed to load admin users:', e)
  } finally {
    loadingUsers.value = false
    // Fallback: show current user if no users loaded
    if (users.value.length === 0 && userStore.isAuthenticated) {
      users.value = [{
        name: userStore.fullname,
        email: userStore.email,
        role: userStore.isAdmin ? 'Administrator' : 'Member',
        lastActive: 'Now',
        color: 'primary'
      }]
    }
  }
}

const goToSettings = (server) => {
  serverStore.setSelectedServer(server.id)
  router.push({ name: 'server-settings', params: { id: server.id } })
}

const handleStart = async (server) => {
  try {
    await serverStore.startServer(server.id)
    serverStore.updateServerState(server.id, 'pending')
    showNotification(`Starting ${server.name}...`, 'success')
  } catch (e) {
    console.error('Failed to start server:', e)
    showNotification('Failed to start server', 'error')
  }
}

const handleStop = async (server) => {
  try {
    await serverStore.stopServer(server.id)
    serverStore.updateServerState(server.id, 'stopping')
    showNotification(`Stopping ${server.name}...`, 'success')
  } catch (e) {
    console.error('Failed to stop server:', e)
    showNotification('Failed to stop server', 'error')
  }
}

onMounted(() => {
  serverStore.listServers()
  loadAdminUsers()
})

// Subscribe to metrics for online servers
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
.search-field :deep(.v-field) {
  background: rgba(0,0,0,0.2);
  border: 1px solid rgba(255,255,255,0.1);
}
</style>
