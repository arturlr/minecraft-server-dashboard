<template>
  <div class="server-table-container">
    <!-- Search Input -->
    <v-text-field
      v-model="search"
      prepend-inner-icon="mdi-magnify"
      label="Search servers"
      variant="outlined"
      density="compact"
      clearable
      hide-details
      class="mb-4"
    ></v-text-field>

    <!-- Data Table -->
    <v-data-table
      :headers="headers"
      :items="servers"
      :search="debouncedSearch"
      :loading="loading"
      :items-per-page="25"
      :sort-by="[{ key: 'name', order: 'asc' }]"
      :height="useVirtualScroll ? 600 : undefined"
      :fixed-header="useVirtualScroll"
      class="elevation-1"
      hover
    >
      <!-- Name Column Slot with Power Button -->
      <template v-slot:item.name="{ item }">
        <div class="d-flex align-center ga-2">
          <v-tooltip text="Power Control" location="top">
            <template v-slot:activator="{ props }">
              <v-btn 
                icon 
                size="small" 
                variant="text"
                v-bind="props" 
                @click.stop="$emit('open-power', item.id)"
              >
                <v-icon size="x-large" :color="getPowerIconColor(item.state)">mdi-power</v-icon>
              </v-btn>
            </template>
          </v-tooltip>
          
          <!-- Editable Server Name with Instance ID Tooltip -->
          <div class="d-flex align-center ga-1 flex-grow-1">
            <v-text-field
              v-if="editingName === item.id"
              v-model="editNameValue"
              density="compact"
              variant="outlined"
              hide-details
              autofocus
              @blur="handleNameBlur(item.id, item.name || item.id)"
              @keyup.enter="saveServerName(item.id)"
              @keyup.escape="cancelEditName"
              class="edit-name-field"
            ></v-text-field>
            
            <v-tooltip v-else :text="`Instance ID: ${item.id}`" location="top">
              <template v-slot:activator="{ props }">
                <span 
                  v-bind="props"
                  class="font-weight-bold server-name-text"
                  @click="startEditName(item.id, item.name || item.id)"
                >
                  {{ item.name || item.id }}
                </span>
              </template>
            </v-tooltip>
            
            <v-tooltip v-if="editingName !== item.id" text="Click to edit server name" location="top">
              <template v-slot:activator="{ props }">
                <v-btn 
                  icon 
                  size="x-small" 
                  variant="text"
                  v-bind="props"
                  @click.stop="startEditName(item.id, item.name || item.id)"
                >
                  <v-icon size="small" color="grey-lighten-1">mdi-pencil</v-icon>
                </v-btn>
              </template>
            </v-tooltip>
            
            <div v-if="editingName === item.id" class="d-flex ga-1">
              <v-tooltip text="Save" location="top">
                <template v-slot:activator="{ props }">
                  <v-btn 
                    icon 
                    size="x-small" 
                    variant="text"
                    color="success"
                    v-bind="props"
                    @click.stop="saveServerName(item.id)"
                    :loading="savingName"
                  >
                    <v-icon size="small">mdi-check</v-icon>
                  </v-btn>
                </template>
              </v-tooltip>
              
              <v-tooltip text="Cancel" location="top">
                <template v-slot:activator="{ props }">
                  <v-btn 
                    icon 
                    size="x-small" 
                    variant="text"
                    color="error"
                    v-bind="props"
                    @click.stop="cancelEditName"
                  >
                    <v-icon size="small">mdi-close</v-icon>
                  </v-btn>
                </template>
              </v-tooltip>
            </div>
          </div>
        </div>
      </template>

      <!-- State Column Slot -->
      <template v-slot:item.state="{ item }">
        <v-chip
          :color="getChipColor(item.state)"
          size="small"
          variant="flat"
        >
          <v-icon :icon="getChipIcon(item.state)" start></v-icon>
          {{ item.state }}
        </v-chip>
      </template>

      <!-- Public IP Column Slot with Copy Button -->
      <template v-slot:item.publicIp="{ item }">
        <div class="d-flex align-center ga-2">
          <span>{{ item.publicIp || '-' }}</span>
          <v-tooltip v-if="item.publicIp" text="Copy IP Address" location="top">
            <template v-slot:activator="{ props }">
              <v-btn 
                icon 
                size="x-small" 
                variant="text"
                v-bind="props" 
                @click.stop="$emit('copy-ip', item.id)"
              >
                <v-icon size="small">mdi-content-copy</v-icon>
              </v-btn>
            </template>
          </v-tooltip>
        </div>
      </template>

      <!-- Specs Column Slot (CPU, RAM, Disk) -->
      <template v-slot:item.specs="{ item }">
        <v-list density="compact" class="pa-0">
          <v-list-item class="pa-0 specs-item">
            <template v-slot:prepend>
              <v-icon size="small" color="primary">mdi-cpu-64-bit</v-icon>
            </template>
            <v-list-item-title class="specs-text">{{ item.vCpus }} vCPU{{ item.vCpus !== 1 ? 's' : '' }}</v-list-item-title>
          </v-list-item>
          
          <v-list-item class="pa-0 specs-item">
            <template v-slot:prepend>
              <v-icon size="small" color="success">mdi-memory</v-icon>
            </template>
            <v-list-item-title class="specs-text">{{ formatRamSize(item.memSize) }}</v-list-item-title>
          </v-list-item>
          
          <v-list-item class="pa-0 specs-item">
            <template v-slot:prepend>
              <v-icon size="small" color="warning">mdi-harddisk</v-icon>
            </template>
            <v-list-item-title class="specs-text">{{ item.diskSize }} GB</v-list-item-title>
          </v-list-item>
        </v-list>
      </template>

      <!-- Running Time Column Slot -->
      <template v-slot:item.runningMinutes="{ item }">
        <v-tooltip v-if="item.runningMinutesCacheTimestamp" location="top">
          <template v-slot:activator="{ props }">
            <span v-bind="props" class="d-flex align-center ga-1">
              {{ formatRunningTime(item.runningMinutes) }}
              <v-icon size="x-small" color="grey-lighten-1">mdi-clock-outline</v-icon>
            </span>
          </template>
          <span>Last updated: {{ formatCacheTimestamp(item.runningMinutesCacheTimestamp) }}</span>
        </v-tooltip>
        <span v-else>{{ formatRunningTime(item.runningMinutes) }}</span>
      </template>

      <!-- Actions Column Slot -->
      <template v-slot:item.actions="{ item }">
        <v-list density="compact" class="pa-0">
          <v-list-item class="pa-0 action-item" @click="$emit('open-stats', item.id)">
            <template v-slot:prepend>
              <v-icon size="small" color="info">mdi-chart-line</v-icon>
            </template>
            <v-list-item-title class="action-text">Stats</v-list-item-title>
          </v-list-item>
          
          <v-list-item class="pa-0 action-item" @click="$emit('open-config', item.id)">
            <template v-slot:prepend>
              <v-icon size="small" color="primary">mdi-cog</v-icon>
            </template>
            <v-list-item-title class="action-text">Config</v-list-item-title>
          </v-list-item>
          
          <v-list-item class="pa-0 action-item" @click="openUserManagement(item.id, item.name || item.id)">
            <template v-slot:prepend>
              <v-icon size="small" color="success">mdi-account-multiple</v-icon>
            </template>
            <v-list-item-title class="action-text">Users</v-list-item-title>
          </v-list-item>
        </v-list>
      </template>

      <!-- Loading Skeleton -->
      <template v-slot:loading>
        <v-skeleton-loader
          v-for="n in 5"
          :key="n"
          type="table-row"
          class="mx-auto"
        ></v-skeleton-loader>
      </template>

      <!-- Empty State -->
      <template v-slot:no-data>
        <div class="text-center py-8">
          <v-icon size="64" color="grey-lighten-1">mdi-server-off</v-icon>
          <div class="text-h6 mt-4 text-grey">No servers available</div>
          <div class="text-body-2 text-grey-darken-1">
            No Minecraft servers found in your account
          </div>
        </div>
      </template>
    </v-data-table>

    <!-- User Management Dialog -->
    <UserManagementDialog
      v-if="selectedServerId"
      v-model="userManagementDialog"
      :server-id="selectedServerId"
      :server-name="selectedServerName"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { generateClient } from 'aws-amplify/api'
import UserManagementDialog from './UserManagementDialog.vue'
import { updateServerName } from '@/graphql/mutations'

const props = defineProps({
  servers: {
    type: Array,
    required: true,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['open-config', 'open-stats', 'open-power', 'copy-ip', 'server-name-updated'])

// User management dialog state
const userManagementDialog = ref(false)
const selectedServerId = ref('')
const selectedServerName = ref('')

// Server name editing state
const editingName = ref(null)
const editNameValue = ref('')
const savingName = ref(false)

// Amplify GraphQL client
const client = generateClient()

/**
 * Open user management dialog for a specific server
 * Requirements: 1.2
 * 
 * @param {string} serverId - The EC2 instance ID
 * @param {string} serverName - The display name of the server
 */
const openUserManagement = (serverId, serverName) => {
  selectedServerId.value = serverId
  selectedServerName.value = serverName
  userManagementDialog.value = true
}

/**
 * Start editing server name
 * @param {string} serverId - The EC2 instance ID
 * @param {string} currentName - The current server name
 */
const startEditName = (serverId, currentName) => {
  editingName.value = serverId
  editNameValue.value = currentName
}

/**
 * Cancel editing server name
 */
const cancelEditName = () => {
  editingName.value = null
  editNameValue.value = ''
}

/**
 * Handle blur event on name field - save if changed, cancel if not
 * @param {string} serverId - The EC2 instance ID
 * @param {string} originalName - The original server name
 */
const handleNameBlur = (serverId, originalName) => {
  const trimmedValue = editNameValue.value.trim()
  
  // If the name has changed and is not empty, save it
  if (trimmedValue && trimmedValue !== originalName) {
    saveServerName(serverId)
  } else {
    // Otherwise, cancel the edit
    cancelEditName()
  }
}

/**
 * Save the new server name
 * @param {string} serverId - The EC2 instance ID
 */
const saveServerName = async (serverId) => {
  if (!editNameValue.value.trim()) {
    // Don't save empty names
    cancelEditName()
    return
  }

  if (editNameValue.value.trim().length > 255) {
    // Show error for names that are too long
    // You could add a snackbar notification here
    return
  }

  savingName.value = true
  
  try {
    console.log('Updating server name:', { serverId, newName: editNameValue.value.trim() })
    
    const result = await client.graphql({
      query: updateServerName,
      variables: {
        instanceId: serverId,
        newName: editNameValue.value.trim()
      }
    })
    
    console.log('Server name update result:', result)
    
    // Emit event to parent to refresh server list
    emit('server-name-updated', serverId, editNameValue.value.trim())
    
    // Reset editing state
    cancelEditName()
    
  } catch (error) {
    console.error('Failed to update server name:', error)
    console.error('Error details:', {
      message: error.message,
      errors: error.errors,
      data: error.data,
      extensions: error.extensions
    })
    
    // Show user-friendly error message
    // You could emit an error event here or show a notification
    alert(`Failed to update server name: ${error.message || 'Unknown error'}`)
  } finally {
    savingName.value = false
  }
}

// Status chip helpers (merged from ServerStatusChip.vue)
const getChipColor = (state) => {
  const stateMap = {
    'running': 'success',
    'stopped': 'error',
    'starting': 'warning',
    'stopping': 'warning',
    'pending': 'warning',
    'shutting-down': 'warning',
    'terminated': 'error',
    'rebooting': 'warning'
  }
  return stateMap[state?.toLowerCase()] || 'default'
}

const getChipIcon = (state) => {
  const stateMap = {
    'running': 'mdi-play',
    'stopped': 'mdi-stop',
    'starting': 'mdi-loading',
    'stopping': 'mdi-loading',
    'pending': 'mdi-loading',
    'shutting-down': 'mdi-loading',
    'terminated': 'mdi-close-circle',
    'rebooting': 'mdi-loading'
  }
  return stateMap[state?.toLowerCase()] || 'mdi-help-circle'
}

const getPowerIconColor = (state) => {
  if (state === 'running') {
    return 'success'
  } else if (state === 'stopped') {
    return 'error'
  } else {
    return 'warning'
  }
}

const search = ref('')
const debouncedSearch = ref('')
let debounceTimeout = null

// Debounce search input with 300ms delay
watch(search, (newValue) => {
  if (debounceTimeout) {
    clearTimeout(debounceTimeout)
  }
  
  debounceTimeout = setTimeout(() => {
    debouncedSearch.value = newValue
  }, 300)
})

// Enable virtual scrolling for large server lists (>50 servers)
const useVirtualScroll = computed(() => props.servers.length > 50)

const headers = ref([
  { 
    title: 'Name', 
    key: 'name', 
    sortable: true,
    class: 'font-weight-bold'
  },
  { 
    title: 'State', 
    key: 'state', 
    sortable: true,
    align: 'center'
  },
  { 
    title: 'Public IP', 
    key: 'publicIp', 
    sortable: false,
    class: 'text-no-wrap'
  },
  { 
    title: 'Specs', 
    key: 'specs', 
    sortable: false,
    align: 'center',
    class: 'responsive-hide-mobile',
    width: '140px'
  },
  { 
    title: 'Running Time', 
    key: 'runningMinutes', 
    sortable: true,
    align: 'center',
    class: 'responsive-hide-mobile'
  },
  { 
    title: 'Actions', 
    key: 'actions', 
    sortable: false,
    align: 'center',
    width: '100px'
  }
])

// Memoized running time formatter to avoid recalculation on every render
const runningTimeCache = new Map()

function formatRunningTime(minutes) {
  // Validate input is a valid number
  const numMinutes = Number(minutes)
  if (!minutes || minutes === 0 || isNaN(numMinutes) || numMinutes < 0) {
    return '-'
  }
  
  // Check cache first
  if (runningTimeCache.has(numMinutes)) {
    return runningTimeCache.get(numMinutes)
  }
  
  const hours = Math.floor(numMinutes / 60)
  const mins = Math.floor(numMinutes % 60)
  
  let result
  if (hours > 24) {
    const days = Math.floor(hours / 24)
    const remainingHours = hours % 24
    result = `${days}d ${remainingHours}h`
  } else if (hours > 0) {
    result = `${hours}h ${mins}m`
  } else {
    result = `${mins}m`
  }
  
  // Cache the result (limit cache size to prevent memory leaks)
  if (runningTimeCache.size > 1000) {
    const firstKey = runningTimeCache.keys().next().value
    runningTimeCache.delete(firstKey)
  }
  runningTimeCache.set(numMinutes, result)
  
  return result
}

// Memoized RAM formatter to avoid recalculation on every render
const ramCache = new Map()

function formatRamSize(memSize) {
  if (!memSize) return '0 GB'
  
  // Check cache first
  if (ramCache.has(memSize)) {
    return ramCache.get(memSize)
  }
  
  const result = `${(memSize / 1024).toFixed(1)} GB`
  
  // Cache the result (limit cache size to prevent memory leaks)
  if (ramCache.size > 1000) {
    const firstKey = ramCache.keys().next().value
    ramCache.delete(firstKey)
  }
  ramCache.set(memSize, result)
  
  return result
}

// Format cache timestamp to relative time
function formatCacheTimestamp(timestamp) {
  if (!timestamp) return 'Unknown'
  
  try {
    const cacheTime = new Date(timestamp)
    const now = new Date()
    const diffMs = now - cacheTime
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)
    
    if (diffMins < 1) {
      return 'Just now'
    } else if (diffMins < 60) {
      return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`
    } else {
      return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`
    }
  } catch (e) {
    return 'Unknown'
  }
}
</script>

<style scoped>
.server-table-container {
  width: 100%;
}

/* Mobile breakpoint - hide instance ID, CPU, RAM, disk, and running time columns on screens < 600px */
@media (max-width: 599px) {
  :deep(.responsive-hide-mobile) {
    display: none !important;
  }
  
  :deep(.d-none.d-sm-table-cell) {
    display: none !important;
  }
  
  /* Reduce table padding on mobile */
  :deep(.v-data-table) {
    font-size: 0.875rem;
  }
  
  :deep(.v-data-table .v-data-table__td),
  :deep(.v-data-table .v-data-table__th) {
    padding: 0 8px !important;
  }
  
  /* Make action buttons more touch-friendly */
  :deep(.v-btn) {
    min-width: 44px !important;
    min-height: 44px !important;
  }
}

/* Tablet breakpoint - adjust spacing for screens 600px - 960px */
@media (min-width: 600px) and (max-width: 959px) {
  :deep(.v-data-table .v-data-table__td),
  :deep(.v-data-table .v-data-table__th) {
    padding: 0 12px !important;
  }
  
  /* Slightly reduce font size on tablet */
  :deep(.v-data-table) {
    font-size: 0.9375rem;
  }
}

@media (max-width: 959px) {
  :deep(.d-none.d-md-table-cell) {
    display: none !important;
  }
}

@media (max-width: 1279px) {
  :deep(.d-none.d-lg-table-cell) {
    display: none !important;
  }
}

/* Desktop - optimal spacing */
@media (min-width: 960px) {
  :deep(.v-data-table .v-data-table__td),
  :deep(.v-data-table .v-data-table__th) {
    padding: 0 16px !important;
  }
}

/* Table hover effect */
:deep(.v-data-table tbody tr:hover) {
  background-color: rgba(0, 0, 0, 0.04);
  cursor: pointer;
}

/* Dark mode hover effect */
:deep(.v-theme--dark .v-data-table tbody tr:hover) {
  background-color: rgba(255, 255, 255, 0.08);
}

/* Touch-friendly action buttons on mobile */
@media (max-width: 599px) {
  :deep(.v-btn--icon) {
    width: 44px !important;
    height: 44px !important;
  }
}

/* Improve search field on mobile */
@media (max-width: 599px) {
  .server-table-container :deep(.v-text-field) {
    font-size: 16px; /* Prevents zoom on iOS */
  }
}

/* Server name editing styles */
.server-name-text {
  cursor: pointer;
  transition: color 0.2s ease;
}

.server-name-text:hover {
  color: rgb(var(--v-theme-primary));
}

.edit-name-field {
  max-width: 200px;
  min-width: 150px;
}

.edit-name-field :deep(.v-field) {
  font-size: 0.875rem;
}

.edit-name-field :deep(.v-field__input) {
  padding: 4px 8px;
  min-height: 32px;
}

/* Specs column styles */
.specs-item {
  min-height: 24px !important;
  height: 24px;
}

.specs-item :deep(.v-list-item__prepend) {
  width: 20px;
  margin-inline-end: 8px;
}

.specs-item :deep(.v-list-item__content) {
  padding: 0;
}

.specs-text {
  font-size: 0.75rem;
  line-height: 1.2;
  font-weight: 500;
}

/* Actions column styles */
.action-item {
  min-height: 24px !important;
  height: 24px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.action-item:hover {
  background-color: rgba(var(--v-theme-primary), 0.08);
}

.action-item :deep(.v-list-item__prepend) {
  width: 20px;
  margin-inline-end: 8px;
}

.action-item :deep(.v-list-item__content) {
  padding: 0;
}

.action-text {
  font-size: 0.75rem;
  line-height: 1.2;
  font-weight: 500;
  cursor: pointer;
}

/* Compact specs and actions lists */
:deep(.v-list.pa-0) {
  background: transparent;
}

:deep(.v-list.pa-0 .v-list-item) {
  padding-left: 0 !important;
  padding-right: 0 !important;
  min-height: 24px !important;
}
</style>
