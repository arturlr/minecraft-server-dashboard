<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import AppToolbar from "../components/AppToolbar.vue";
import IamAlert from "../components/IamAlert.vue";
import ServerTable from "../components/ServerTable.vue";
import ServerConfigDialog from "../components/ServerConfigDialog.vue";
import ServerStatsDialog from "../components/ServerStatsDialog.vue";
import PowerControlDialog from "../components/PowerControlDialog.vue";
import ErrorBoundary from "../components/ErrorBoundary.vue";
import { generateClient } from 'aws-amplify/api';
import { useUserStore } from "../stores/user";
import { useServerStore } from "../stores/server";
import * as subscriptions from "../graphql/subscriptions";
import * as mutations from "../graphql/mutations";
import { parseGraphQLError, retryOperation } from "../utils/errorHandler";

const userStore = useUserStore();
const serverStore = useServerStore();
const graphQlClient = generateClient();

// Dialog visibility states
const configDialogVisible = ref(false);
const statsDialogVisible = ref(false);
const powerDialogVisible = ref(false);

// Selected server for dialog operations
const selectedServerId = ref(null);

// Snackbar state
const snackbar = ref({
  visible: false,
  text: '',
  color: 'primary',
  timeout: 3500
});

// Subscription references
let stateChangeSubscription = null;

// Computed properties for selected server details with proper memoization
const selectedServer = computed(() => {
  if (!selectedServerId.value) return null;
  return serverStore.getServerById(selectedServerId.value);
});

const selectedServerName = computed(() => {
  const server = selectedServer.value;
  if (!server) return '';
  return server.name && server.name.length > 2 ? server.name : server.id;
});

const selectedServerState = computed(() => {
  const server = selectedServer.value;
  return server?.state || '';
});

const selectedServerIamStatus = computed(() => {
  const server = selectedServer.value;
  return server?.iamStatus || '';
});

// Computed property for servers with IAM issues - memoized to avoid filtering on every render
const serversWithIamIssues = computed(() => {
  return serverStore.serversList.filter(server => server.iamStatus !== 'ok');
});

// Dialog handler methods
function openConfigDialog(serverId) {
  selectedServerId.value = serverId;
  serverStore.setSelectedServerId(serverId);
  configDialogVisible.value = true;
}

function openStatsDialog(serverId) {
  selectedServerId.value = serverId;
  serverStore.setSelectedServerId(serverId);
  statsDialogVisible.value = true;
}

function openPowerDialog(serverId) {
  selectedServerId.value = serverId;
  serverStore.setSelectedServerId(serverId);
  powerDialogVisible.value = true;
}

async function copyToClipboard(serverId) {
  const server = serverStore.getServerById(serverId);
  if (!server || !server.publicIp) {
    handleActionComplete('No IP address available to copy', false);
    return;
  }

  try {
    const ipAddress = `${server.publicIp}:25565`;
    await navigator.clipboard.writeText(ipAddress);
    handleActionComplete('Server IP address copied to clipboard!', true);
  } catch (err) {
    console.error('Failed to copy to clipboard:', err);
    const errorMessage = err.message?.includes('permission') 
      ? 'Clipboard access denied. Please allow clipboard permissions.'
      : 'Failed to copy to clipboard. Please try again.';
    handleActionComplete(errorMessage, false);
  }
}

async function fixIamRole(serverId) {
  try {
    // Execute with retry logic for network errors
    const result = await retryOperation(async () => {
      return await graphQlClient.graphql({
        query: mutations.fixServerRole,
        variables: { instanceId: serverId }
      });
    });

    if (result.data.fixServerRole) {
      handleActionComplete('IAM role fixed successfully', true);
      // Refresh server list to update IAM status
      try {
        await serverStore.listServers();
      } catch (refreshError) {
        console.error('Error refreshing server list:', refreshError);
        // Don't show error to user since the main operation succeeded
      }
    } else {
      handleActionComplete('Failed to fix IAM role. Please try again.', false);
    }
  } catch (error) {
    console.error('Error fixing IAM role:', error);
    const errorMessage = parseGraphQLError(error);
    handleActionComplete(errorMessage, false);
  }
}

function handleActionComplete(message, success) {
  snackbar.value = {
    visible: true,
    text: message,
    color: success ? 'success' : 'error',
    timeout: success ? 3500 : 5000 // Show errors longer
  };
}

/**
 * Handle server name update event from ServerTable
 * @param {string} serverId - The EC2 instance ID
 * @param {string} newName - The new server name
 */
function handleServerNameUpdated(serverId, newName) {
  // Update the server name in the store
  serverStore.updateServerName(serverId, newName);
  
  // Show success message
  handleActionComplete(`Server name updated to "${newName}"`, true);
  
  // Optionally refresh the server list to ensure consistency
  // serverStore.loadServers();
}

function handleServerCreated() {
  // Show immediate feedback
  handleActionComplete('Server creation completed! Refreshing server list...', true);
  
  // Refresh server list when a new server is created
  serverStore.listServers().then(() => {
    // Additional success feedback after refresh
    console.log('Server list refreshed after creation');
  }).catch((error) => {
    console.error('Error refreshing server list after creation:', error);
    const errorMessage = parseGraphQLError(error);
    handleActionComplete(`Server created, but failed to refresh list: ${errorMessage}. Please refresh manually.`, false);
  });
}

// Handle component errors from ErrorBoundary
function handleComponentError({ error, instance, info }) {
  console.error('Component error caught by boundary:', error);
  handleActionComplete(`Component error: ${error.message}`, false);
}

// Lifecycle hooks
onMounted(async () => {
  // Load server list with error handling
  try {
    await serverStore.listServers();
  } catch (error) {
    console.error('Error loading server list:', error);
    const errorMessage = parseGraphQLError(error);
    handleActionComplete(`Failed to load servers: ${errorMessage}`, false);
  }

  // Subscribe to state changes with error handling
  try {
    stateChangeSubscription = graphQlClient.graphql({
      query: subscriptions.onChangeState
    }).subscribe({
      next: ({ data }) => {
        if (data?.onChangeState) {
          serverStore.updateServer(data.onChangeState);
        }
      },
      error: (error) => {
        console.error('State change subscription error:', error);
        const errorMessage = parseGraphQLError(error);
        handleActionComplete(`Real-time updates disconnected: ${errorMessage}`, false);
        
        // Attempt to reconnect after a delay
        setTimeout(() => {
          console.log('Attempting to reconnect to state change subscription...');
          try {
            stateChangeSubscription = graphQlClient.graphql({
              query: subscriptions.onChangeState
            }).subscribe({
              next: ({ data }) => {
                if (data?.onChangeState) {
                  serverStore.updateServer(data.onChangeState);
                }
              },
              error: (error) => {
                console.error('Reconnection failed:', error);
              }
            });
          } catch (reconnectError) {
            console.error('Failed to reconnect:', reconnectError);
          }
        }, 5000);
      }
    });
  } catch (error) {
    console.error('Failed to subscribe to state changes:', error);
    handleActionComplete('Failed to enable real-time updates', false);
  }
});

onUnmounted(() => {
  // Clean up subscription
  if (stateChangeSubscription) {
    stateChangeSubscription.unsubscribe();
  }
});
</script>

<template>
  <v-layout class="rounded rounded-md">
    <AppToolbar @server-created="handleServerCreated" />
    <v-main>
      <ErrorBoundary @error="handleComponentError">
        <v-container fluid class="pa-4">
          <!-- Snackbar for notifications -->
          <v-snackbar 
            v-model="snackbar.visible" 
            :timeout="snackbar.timeout" 
            :color="snackbar.color" 
            outlined 
            left 
            centered 
            text
          >
            {{ snackbar.text }}

            <template #actions>
              <v-btn color="white" variant="text" @click="snackbar.visible = false">
                Close
              </v-btn>
            </template>
          </v-snackbar>

          <!-- IAM Alert -->
          <IamAlert 
            :servers="serversWithIamIssues"
            @fix-iam="fixIamRole"
          />

          <!-- Server Table -->
          <ServerTable
            :servers="serverStore.serversList"
            :loading="serverStore.loading"
            @open-config="openConfigDialog"
            @open-stats="openStatsDialog"
            @open-power="openPowerDialog"
            @copy-ip="copyToClipboard"
            @server-name-updated="handleServerNameUpdated"
          />
        </v-container>
      </ErrorBoundary>
    </v-main>
  </v-layout>

  <!-- Configuration Dialog - Only render when visible -->
  <ErrorBoundary v-if="configDialogVisible" @error="handleComponentError">
    <ServerConfigDialog
      v-model:visible="configDialogVisible"
      :server-id="selectedServerId"
      @config-saved="handleActionComplete('Configuration saved successfully!', true)"
    />
  </ErrorBoundary>

  <!-- Statistics Dialog - Only render when visible -->
  <ErrorBoundary v-if="statsDialogVisible" @error="handleComponentError">
    <ServerStatsDialog
      v-model:visible="statsDialogVisible"
      :server-id="selectedServerId"
    />
  </ErrorBoundary>

  <!-- Power Control Dialog - Only render when visible -->
  <ErrorBoundary v-if="powerDialogVisible" @error="handleComponentError">
    <PowerControlDialog
      v-model:visible="powerDialogVisible"
      :server-id="selectedServerId"
      :server-name="selectedServerName"
      :server-state="selectedServerState"
      :iam-status="selectedServerIamStatus"
      @action-complete="handleActionComplete"
    />
  </ErrorBoundary>
</template>
