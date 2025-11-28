<script setup>
import { ref, computed, watch, onUnmounted } from 'vue';
import { generateClient } from 'aws-amplify/api';
import * as subscriptions from '../graphql/subscriptions';
import { useServerStore } from '../stores/server';
import ServerCharts from './ServerCharts.vue';
import { parseGraphQLError } from '../utils/errorHandler';

const props = defineProps({
  visible: {
    type: Boolean,
    required: true
  },
  serverId: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['update:visible']);

const serverStore = useServerStore();
const graphQlClient = generateClient();

// Reactive state for subscriptions and loading
const metricsSubscription = ref(null);
const stateSubscription = ref(null);
const loading = ref(false);
const error = ref(null);
const reconnectAttempts = ref(0);
const maxReconnectAttempts = 3;
const serverChartsRef = ref(null);

// Computed properties for server data with proper memoization
const server = computed(() => serverStore.serversDict[props.serverId] || {});

const serverName = computed(() => {
  const srv = server.value;
  if (srv.name && srv.name.length > 2) {
    return srv.name;
  }
  return srv.id || 'Unknown Server';
});

const vCpus = computed(() => server.value.vCpus || 0);

// Memoized memory size calculation
const memSize = computed(() => {
  const mem = server.value.memSize;
  return mem ? (mem / 1024).toFixed(1) : '0';
});

const diskSize = computed(() => server.value.diskSize || 0);

// Memoized running time display
const runningTime = computed(() => {
  const minutes = server.value.runningMinutes;
  const numMinutes = Number(minutes);
  
  // Validate input is a valid number
  if (!minutes || isNaN(numMinutes) || numMinutes <= 0) {
    return '0 hours';
  }
  
  const hours = (numMinutes / 60).toFixed(1);
  return `${hours} hours`;
});

// Format cache timestamp to relative time
const cacheTimestamp = computed(() => {
  const timestamp = server.value.runningMinutesCacheTimestamp;
  if (!timestamp) return null;
  
  try {
    const cacheTime = new Date(timestamp);
    const now = new Date();
    const diffMs = now - cacheTime;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    
    if (diffMins < 1) {
      return 'Just now';
    } else if (diffMins < 60) {
      return `${diffMins} min ago`;
    } else if (diffHours < 24) {
      return `${diffHours} hr ago`;
    } else {
      return cacheTime.toLocaleDateString();
    }
  } catch (e) {
    return null;
  }
});

// Computed property for formatted last update time
const lastUpdateFormatted = computed(() => {
  if (!serverChartsRef.value?.lastUpdateTime) {
    return 'No data yet';
  }
  const date = serverChartsRef.value.lastUpdateTime;
  const now = new Date();
  const diffSeconds = Math.floor((now - date) / 1000);
  
  if (diffSeconds < 60) {
    return 'Just now';
  } else if (diffSeconds < 3600) {
    const minutes = Math.floor(diffSeconds / 60);
    return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
  } else {
    return date.toLocaleTimeString();
  }
});

// Subscribe to metrics
const subscribeToMetrics = async () => {
  if (!props.serverId) {
    console.warn('Cannot subscribe to metrics: serverId is not provided');
    error.value = 'No server selected';
    return;
  }

  try {
    loading.value = true;
    error.value = null;
    
    // Set selected server ID in store
    serverStore.setSelectedServerId(props.serverId);

    // Subscribe to metrics updates
    metricsSubscription.value = await graphQlClient
      .graphql({
        query: subscriptions.onPutServerMetric,
        variables: { id: props.serverId }
      })
      .subscribe({
        next: (response) => {
          console.log('Metrics update received for server:', props.serverId);
          // The ServerCharts component will handle the metric updates
          loading.value = false;
          error.value = null;
          reconnectAttempts.value = 0; // Reset reconnect attempts on success
        },
        error: (subscriptionError) => {
          console.error('Metrics subscription error:', subscriptionError);
          loading.value = false;
          
          const errorMessage = parseGraphQLError(subscriptionError);
          error.value = `Failed to load metrics: ${errorMessage}`;
          
          // Attempt to reconnect if we haven't exceeded max attempts
          if (reconnectAttempts.value < maxReconnectAttempts) {
            reconnectAttempts.value++;
            const delay = 2000 * reconnectAttempts.value; // Exponential backoff
            
            console.log(`Attempting to reconnect (${reconnectAttempts.value}/${maxReconnectAttempts}) in ${delay}ms...`);
            
            setTimeout(() => {
              if (props.visible) {
                subscribeToMetrics();
              }
            }, delay);
          } else {
            error.value = 'Unable to connect to metrics service. Please close and try again.';
          }
        }
      });

    console.log('Subscribed to metrics for server:', props.serverId);
    
    // Set a timeout to hide loading indicator even if no data arrives
    setTimeout(() => {
      loading.value = false;
    }, 3000);
  } catch (error) {
    console.error('Failed to subscribe to metrics:', error);
    loading.value = false;
    const errorMessage = parseGraphQLError(error);
    error.value = `Failed to initialize metrics: ${errorMessage}`;
  }
};

// Unsubscribe from metrics
const unsubscribeFromMetrics = () => {
  if (metricsSubscription.value) {
    try {
      metricsSubscription.value.unsubscribe();
      console.log('Unsubscribed from metrics for server:', props.serverId);
    } catch (error) {
      console.error('Error unsubscribing from metrics:', error);
    }
    metricsSubscription.value = null;
  }
  loading.value = false;
  error.value = null;
  reconnectAttempts.value = 0;
};

// Watch visible prop to manage subscriptions
watch(() => props.visible, (newValue) => {
  if (newValue) {
    subscribeToMetrics();
  } else {
    unsubscribeFromMetrics();
  }
});

// Cleanup on unmount
onUnmounted(() => {
  unsubscribeFromMetrics();
});

// Close dialog handler
const closeDialog = () => {
  emit('update:visible', false);
};
</script>

<template>
  <v-dialog
    :model-value="visible"
    @update:model-value="emit('update:visible', $event)"
    max-width="1000px"
    :fullscreen="$vuetify.display.mobile"
    scrollable
    transition="dialog-bottom-transition"
  >
    <v-card>
      <v-overlay
        :model-value="loading"
        contained
        class="align-center justify-center"
      >
        <v-progress-circular
          indeterminate
          size="64"
          color="primary"
        ></v-progress-circular>
        <div class="text-white mt-4">Loading metrics...</div>
      </v-overlay>

      <v-card-title class="bg-primary text-white d-flex align-center">
        <v-icon class="mr-2">mdi-chart-line</v-icon>
        Server Statistics - {{ serverName }}
        <v-spacer></v-spacer>
        <v-btn
          icon
          variant="text"
          @click="closeDialog"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pt-4">
        <!-- Error Alert -->
        <v-alert
          v-if="error"
          type="error"
          variant="tonal"
          border="start"
          border-color="error"
          class="mb-4"
        >
          <template v-slot:prepend>
            <v-icon>mdi-alert-circle</v-icon>
          </template>
          <div class="font-weight-medium mb-2">Connection Error</div>
          <div>{{ error }}</div>
          <v-btn
            v-if="reconnectAttempts >= maxReconnectAttempts"
            color="error"
            variant="elevated"
            size="small"
            class="mt-3"
            @click="subscribeToMetrics"
            prepend-icon="mdi-refresh"
          >
            Retry Connection
          </v-btn>
        </v-alert>

        <!-- Server Specs Section -->
        <v-row class="mb-4">
          <v-col cols="12" md="8">
            <v-chip-group column>
              <v-chip variant="tonal">
                <v-icon class="mr-1">mdi-chip</v-icon>
                {{ vCpus }} vCPU
              </v-chip>

              <v-chip variant="tonal">
                <v-icon class="mr-1">mdi-memory</v-icon>
                {{ memSize }} GB
              </v-chip>

              <v-chip variant="tonal">
                <v-icon class="mr-1">mdi-disc</v-icon>
                {{ diskSize }} GB
              </v-chip>

              <v-tooltip v-if="cacheTimestamp" location="top">
                <template v-slot:activator="{ props }">
                  <v-chip variant="tonal" v-bind="props">
                    <v-icon class="mr-1">mdi-clock-outline</v-icon>
                    {{ runningTime }}
                  </v-chip>
                </template>
                <span>Calculated: {{ cacheTimestamp }}</span>
              </v-tooltip>
              <v-chip v-else variant="tonal">
                <v-icon class="mr-1">mdi-clock-outline</v-icon>
                {{ runningTime }}
              </v-chip>
            </v-chip-group>
          </v-col>
          <v-col cols="12" md="4" class="d-flex align-center justify-end">
            <div class="text-caption text-medium-emphasis">
              <v-icon size="small" class="mr-1">mdi-update</v-icon>
              Last updated: {{ lastUpdateFormatted }}
            </div>
          </v-col>
        </v-row>

        <!-- Charts Section -->
        <v-row>
          <v-col cols="12">
            <ServerCharts ref="serverChartsRef" />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.bg-primary {
  background-color: rgb(var(--v-theme-primary));
}

/* Mobile responsive adjustments */
@media (max-width: 599px) {
  :deep(.v-card-title) {
    padding: 16px !important;
    font-size: 1rem !important;
  }
  
  :deep(.v-card-text) {
    padding: 12px !important;
  }
  
  /* Stack chips vertically on mobile */
  :deep(.v-chip-group) {
    flex-direction: column !important;
    align-items: flex-start !important;
  }
  
  :deep(.v-chip) {
    width: 100%;
    justify-content: flex-start;
    margin-bottom: 8px !important;
  }
  
  /* Ensure touch-friendly buttons */
  :deep(.v-btn) {
    min-width: 44px !important;
    min-height: 44px !important;
  }
}

/* Tablet adjustments */
@media (min-width: 600px) and (max-width: 959px) {
  :deep(.v-card-title) {
    padding: 20px !important;
  }
  
  :deep(.v-chip-group) {
    flex-wrap: wrap;
  }
}
</style>
