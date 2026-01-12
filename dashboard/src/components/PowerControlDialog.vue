<script setup>
import { ref, computed } from 'vue';
import { generateClient } from 'aws-amplify/api';
import * as mutations from '../graphql/mutations';
import { useServerStore } from '../stores/server';
import { parseGraphQLError, retryOperation } from '../utils/errorHandler';

const client = generateClient();
const serverStore = useServerStore();

const props = defineProps({
  visible: {
    type: Boolean,
    required: true
  },
  serverId: {
    type: String,
    default: null
  },
  serverName: {
    type: String,
    default: ''
  },
  serverState: {
    type: String,
    default: 'stopped'
  },
  iamStatus: {
    type: String,
    default: 'ok'
  }
});

const emit = defineEmits(['update:visible', 'action-complete']);

const loading = ref(false);
const fixingIam = ref(false);

const isIamCompliant = computed(() => props.iamStatus === 'ok');
const isServerRunning = computed(() => props.serverState === 'running');
const isServerStopped = computed(() => props.serverState === 'stopped');

async function executeAction(action) {
  if (!props.serverId) {
    emit('action-complete', 'No server selected', false);
    return;
  }

  loading.value = true;
  
  try {
    let mutation;
    let actionName;
    
    switch (action) {
      case 'startServer':
        mutation = mutations.startServer;
        actionName = 'Start';
        break;
      case 'stopServer':
        mutation = mutations.stopServer;
        actionName = 'Stop';
        break;
      case 'restartServer':
        mutation = mutations.restartServer;
        actionName = 'Restart';
        break;
      default:
        throw new Error('Invalid action');
    }

    // Execute with retry logic for network errors
    const result = await retryOperation(async () => {
      return await client.graphql({
        query: mutation,
        variables: { instanceId: props.serverId }
      });
    });

    if (result.data[action]) {
      emit('action-complete', `${actionName} command sent successfully`, true);
      emit('update:visible', false);
    } else {
      const errorMsg = `Failed to ${actionName.toLowerCase()} server. Please try again.`;
      emit('action-complete', errorMsg, false);
    }
  } catch (error) {
    console.error(`Error executing ${action}:`, error);
    const errorMessage = parseGraphQLError(error);
    emit('action-complete', errorMessage, false);
  } finally {
    loading.value = false;
  }
}

async function fixIamRole() {
  if (!props.serverId) {
    emit('action-complete', 'No server selected', false);
    return;
  }

  fixingIam.value = true;
  
  try {
    // Execute with retry logic for network errors
    const result = await retryOperation(async () => {
      return await client.graphql({
        query: mutations.fixServerRole,
        variables: { instanceId: props.serverId }
      });
    });

    if (result.data.fixServerRole) {
      emit('action-complete', 'IAM role fixed successfully', true);
      emit('update:visible', false);
    } else {
      emit('action-complete', 'Failed to fix IAM role. Please try again.', false);
    }
  } catch (error) {
    console.error('Error fixing IAM role:', error);
    const errorMessage = parseGraphQLError(error);
    emit('action-complete', errorMessage, false);
  } finally {
    fixingIam.value = false;
  }
}

function closeDialog() {
  emit('update:visible', false);
}
</script>

<template>
  <v-dialog 
    :model-value="visible" 
    @update:model-value="$emit('update:visible', $event)"
    max-width="500px"
    :fullscreen="$vuetify.display.mobile"
    persistent
    transition="dialog-bottom-transition"
  >
    <v-card class="elevation-8">
      <!-- Header -->
      <v-card-title class="bg-primary text-white pa-6">
        <div class="d-flex align-center w-100">
          <v-icon class="me-3" size="28">mdi-power</v-icon>
          <div>
            <div class="text-h5 font-weight-bold">Power Control</div>
            <div class="text-body-2 opacity-90">{{ serverName || serverId }}</div>
          </div>
          <v-spacer></v-spacer>
          <v-btn 
            icon 
            variant="text" 
            @click="closeDialog"
            class="text-white"
            :disabled="loading || fixingIam"
          >
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </div>
      </v-card-title>

      <v-card-text class="pa-6">
        <!-- IAM Error Alert -->
        <v-alert 
          v-if="!isIamCompliant" 
          type="error" 
          variant="tonal"
          border="start"
          border-color="error"
          class="mb-4"
        >
          <template #prepend>
            <v-icon>mdi-alert-circle</v-icon>
          </template>
          <div class="font-weight-medium mb-2">IAM Role Issue Detected</div>
          <div class="mb-3">
            You need to fix the IAM role to perform any power actions on this server.
          </div>
          <v-btn 
            color="error" 
            variant="elevated"
            @click="fixIamRole"
            :loading="fixingIam"
            :disabled="fixingIam"
            prepend-icon="mdi-wrench"
            size="small"
          >
            Fix IAM Role Now
          </v-btn>
        </v-alert>

        <!-- Power Actions -->
        <div v-else>
          <!-- Server State Info -->
          <v-card variant="tonal" :color="isServerRunning ? 'success' : 'grey'" class="mb-4">
            <v-card-text class="pa-4">
              <div class="d-flex align-center">
                <v-icon 
                  class="me-2" 
                  :color="isServerRunning ? 'success' : 'grey'"
                  size="24"
                >
                  {{ isServerRunning ? 'mdi-server' : 'mdi-server-off' }}
                </v-icon>
                <div>
                  <div class="font-weight-medium">Current State</div>
                  <div class="text-body-2">
                    Server is currently <strong>{{ serverState }}</strong>
                  </div>
                </div>
              </div>
            </v-card-text>
          </v-card>

          <!-- Action Buttons for Stopped Server -->
          <div v-if="isServerStopped" class="d-flex flex-column gap-3">
            <v-btn 
              color="success" 
              variant="elevated"
              size="large"
              @click="executeAction('startServer')"
              :loading="loading"
              :disabled="loading"
              prepend-icon="mdi-play"
              block
            >
              Start Server
            </v-btn>
          </div>

          <!-- Action Buttons for Running Server -->
          <div v-else-if="isServerRunning" class="d-flex flex-column gap-3">
            <v-btn 
              color="warning" 
              variant="elevated"
              size="large"
              @click="executeAction('stopServer')"
              :loading="loading"
              :disabled="loading"
              prepend-icon="mdi-stop"
              block
            >
              Stop Server
            </v-btn>
            
            <v-btn 
              color="info" 
              variant="elevated"
              size="large"
              @click="executeAction('restartServer')"
              :loading="loading"
              :disabled="loading"
              prepend-icon="mdi-restart"
              block
            >
              Restart Server
            </v-btn>
          </div>

          <!-- Transitional State -->
          <div v-else>
            <v-alert 
              type="info" 
              variant="tonal"
              border="start"
              border-color="info"
            >
              <template #prepend>
                <v-icon>mdi-information</v-icon>
              </template>
              <div class="font-weight-medium">Server in Transition</div>
              <div>
                The server is currently in a transitional state ({{ serverState }}). 
                Please wait for the operation to complete.
              </div>
            </v-alert>
          </div>
        </div>
      </v-card-text>

      <!-- Actions -->
      <v-card-actions class="pa-6 bg-grey-lighten-5">
        <v-spacer></v-spacer>
        <v-btn 
          variant="text" 
          @click="closeDialog"
          prepend-icon="mdi-close"
          :disabled="loading || fixingIam"
        >
          Cancel
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.gap-3 {
  gap: 12px;
}

/* Mobile responsive adjustments */
@media (max-width: 599px) {
  :deep(.v-card-title) {
    padding: 16px !important;
  }
  
  :deep(.v-card-text) {
    padding: 16px !important;
  }
  
  :deep(.v-card-actions) {
    padding: 16px !important;
  }
  
  /* Make buttons more touch-friendly */
  :deep(.v-btn) {
    min-width: 44px !important;
    min-height: 44px !important;
  }
  
  /* Ensure action buttons are full width on mobile */
  :deep(.v-btn[block]) {
    width: 100%;
  }
}

/* Tablet adjustments */
@media (min-width: 600px) and (max-width: 959px) {
  :deep(.v-card-title) {
    padding: 20px !important;
  }
  
  :deep(.v-card-text) {
    padding: 20px !important;
  }
}
</style>
