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
          <span class="font-weight-bold">{{ item.name || item.id }}</span>
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

      <!-- RAM Column Slot (convert to GB) -->
      <template v-slot:item.memSize="{ item }">
        {{ formatRamSize(item.memSize) }}
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
        <ServerActionsMenu
          :server-id="item.id"
          :server-state="item.state"
          :iam-status="item.iamStatus"
          @open-config="$emit('open-config', item.id)"
          @open-stats="$emit('open-stats', item.id)"
        />
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
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import ServerActionsMenu from './ServerActionsMenu.vue'

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

const emit = defineEmits(['open-config', 'open-stats', 'open-power', 'copy-ip'])

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
    title: 'Instance ID', 
    key: 'id', 
    sortable: true,
    class: 'text-no-wrap responsive-hide-mobile'
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
    title: 'CPU', 
    key: 'vCpus', 
    sortable: true,
    align: 'center',
    class: 'responsive-hide-mobile'
  },
  { 
    title: 'RAM', 
    key: 'memSize', 
    sortable: true,
    align: 'center',
    class: 'responsive-hide-mobile'
  },
  { 
    title: 'Disk (GB)', 
    key: 'diskSize', 
    sortable: true,
    align: 'center',
    class: 'responsive-hide-mobile'
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
    align: 'end',
    width: '120px'
  }
])

// Memoized running time formatter to avoid recalculation on every render
const runningTimeCache = new Map()

function formatRunningTime(minutes) {
  if (!minutes || minutes === 0) {
    return '-'
  }
  
  // Check cache first
  if (runningTimeCache.has(minutes)) {
    return runningTimeCache.get(minutes)
  }
  
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  
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
  runningTimeCache.set(minutes, result)
  
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
</style>
