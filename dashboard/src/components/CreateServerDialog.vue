<script setup>
import { ref, computed, watch, onUnmounted } from 'vue';
import { generateClient } from 'aws-amplify/api';
import { createServer } from '@/graphql/mutations';
import { onPutServerActionStatus } from '@/graphql/subscriptions';

const props = defineProps({
  visible: {
    type: Boolean,
    required: true
  }
});

const emit = defineEmits(['update:visible', 'server-created']);

// Create GraphQL client
const graphQlClient = generateClient();

// Form data
const serverName = ref('');
const instanceType = ref('t3.micro');
const shutdownMethod = ref('CPUUtilization');
const cpuThreshold = ref(5.0);
const evaluationPeriod = ref(30);
const connectionThreshold = ref(0);
const startSchedule = ref('');
const stopSchedule = ref('');
const loading = ref(false);
const errors = ref({});
const creationStatus = ref('');
const creationInstanceId = ref('');

// Subscription reference for real-time status updates
let statusSubscription = null;

// Instance type options with specifications and costs
const instanceTypes = [
  { value: 't3.micro', label: 'T3 Micro', cpu: '2 vCPU', memory: '1 GB', cost: '$0.0104/hr' },
  { value: 't3.small', label: 'T3 Small', cpu: '2 vCPU', memory: '2 GB', cost: '$0.0208/hr' },
  { value: 't3.medium', label: 'T3 Medium', cpu: '2 vCPU', memory: '4 GB', cost: '$0.0416/hr' },
  { value: 't3.large', label: 'T3 Large', cpu: '2 vCPU', memory: '8 GB', cost: '$0.0832/hr' },
  { value: 't3.xlarge', label: 'T3 XLarge', cpu: '4 vCPU', memory: '16 GB', cost: '$0.1664/hr' },
  { value: 't3.2xlarge', label: 'T3 2XLarge', cpu: '8 vCPU', memory: '32 GB', cost: '$0.3328/hr' }
];

// Shutdown method options
const shutdownMethods = [
  { value: 'CPUUtilization', label: 'CPU-based Shutdown', description: 'Stop when CPU usage is low' },
  { value: 'Connections', label: 'Connection-based Shutdown', description: 'Stop when no players connected' },
  { value: 'Schedule', label: 'Scheduled Shutdown', description: 'Start/stop on schedule' }
];

// Computed properties
const selectedInstanceType = computed(() => {
  return instanceTypes.find(type => type.value === instanceType.value);
});

const showCpuFields = computed(() => shutdownMethod.value === 'CPUUtilization');
const showConnectionFields = computed(() => shutdownMethod.value === 'Connections');
const showScheduleFields = computed(() => shutdownMethod.value === 'Schedule');

const isFormValid = computed(() => {
  return isServerNameValid.value && 
         isInstanceTypeValid.value && 
         isShutdownConfigValid.value &&
         Object.keys(errors.value).length === 0;
});

const isServerNameValid = computed(() => {
  const name = serverName.value.trim();
  return name.length >= 3 && name.length <= 50 && /^[a-zA-Z0-9_-]+$/.test(name);
});

const isInstanceTypeValid = computed(() => {
  return instanceTypes.some(type => type.value === instanceType.value);
});

const isShutdownConfigValid = computed(() => {
  if (shutdownMethod.value === 'CPUUtilization') {
    return cpuThreshold.value >= 0 && cpuThreshold.value <= 100 && 
           evaluationPeriod.value >= 1 && evaluationPeriod.value <= 60;
  }
  if (shutdownMethod.value === 'Connections') {
    return connectionThreshold.value >= 0 && connectionThreshold.value <= 100 && 
           evaluationPeriod.value >= 1 && evaluationPeriod.value <= 60;
  }
  if (shutdownMethod.value === 'Schedule') {
    return startSchedule.value.trim() !== '' && stopSchedule.value.trim() !== '';
  }
  return true;
});

// Validation functions
function validateServerName() {
  const name = serverName.value.trim();
  if (!name) {
    errors.value.serverName = 'Server name is required';
  } else if (name.length < 3) {
    errors.value.serverName = 'Server name must be at least 3 characters';
  } else if (name.length > 50) {
    errors.value.serverName = 'Server name must be no more than 50 characters';
  } else if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
    errors.value.serverName = 'Server name can only contain alphanumeric characters, hyphens, and underscores';
  } else {
    delete errors.value.serverName;
  }
}

function validateShutdownConfig() {
  if (shutdownMethod.value === 'CPUUtilization') {
    if (cpuThreshold.value < 0 || cpuThreshold.value > 100) {
      errors.value.cpuThreshold = 'CPU threshold must be between 0 and 100';
    } else {
      delete errors.value.cpuThreshold;
    }
    
    if (evaluationPeriod.value < 1 || evaluationPeriod.value > 60) {
      errors.value.evaluationPeriod = 'Evaluation period must be between 1 and 60 minutes';
    } else {
      delete errors.value.evaluationPeriod;
    }
  } else if (shutdownMethod.value === 'Connections') {
    if (connectionThreshold.value < 0 || connectionThreshold.value > 100) {
      errors.value.connectionThreshold = 'Connection threshold must be between 0 and 100';
    } else {
      delete errors.value.connectionThreshold;
    }
    
    if (evaluationPeriod.value < 1 || evaluationPeriod.value > 60) {
      errors.value.evaluationPeriod = 'Evaluation period must be between 1 and 60 minutes';
    } else {
      delete errors.value.evaluationPeriod;
    }
  } else if (shutdownMethod.value === 'Schedule') {
    if (!startSchedule.value.trim()) {
      errors.value.startSchedule = 'Start schedule is required';
    } else {
      delete errors.value.startSchedule;
    }
    
    if (!stopSchedule.value.trim()) {
      errors.value.stopSchedule = 'Stop schedule is required';
    } else {
      delete errors.value.stopSchedule;
    }
  }
}

// Watch for changes to validate in real-time
watch(serverName, validateServerName);
watch([shutdownMethod, cpuThreshold, evaluationPeriod, connectionThreshold, startSchedule, stopSchedule], validateShutdownConfig);

// Reset form when dialog closes
watch(() => props.visible, (newValue) => {
  if (!newValue) {
    resetForm();
  }
});

function resetForm() {
  serverName.value = '';
  instanceType.value = 't3.micro';
  shutdownMethod.value = 'CPUUtilization';
  cpuThreshold.value = 5.0;
  evaluationPeriod.value = 30;
  connectionThreshold.value = 0;
  startSchedule.value = '';
  stopSchedule.value = '';
  loading.value = false;
  errors.value = {};
  creationStatus.value = '';
  creationInstanceId.value = '';
  
  // Clean up subscription if exists
  if (statusSubscription) {
    statusSubscription.unsubscribe();
    statusSubscription = null;
  }
}

function closeDialog() {
  emit('update:visible', false);
}

async function submitForm() {
  if (!isFormValid.value) {
    return;
  }

  loading.value = true;
  creationStatus.value = 'Submitting request...';
  
  try {
    const input = {
      serverName: serverName.value.trim(),
      instanceType: instanceType.value,
      shutdownMethod: shutdownMethod.value
    };

    // Add shutdown-specific parameters
    if (shutdownMethod.value === 'CPUUtilization') {
      input.alarmThreshold = cpuThreshold.value;
      input.alarmEvaluationPeriod = evaluationPeriod.value;
    } else if (shutdownMethod.value === 'Connections') {
      input.alarmThreshold = connectionThreshold.value;
      input.alarmEvaluationPeriod = evaluationPeriod.value;
    } else if (shutdownMethod.value === 'Schedule') {
      input.startScheduleExpression = startSchedule.value.trim();
      input.stopScheduleExpression = stopSchedule.value.trim();
    }

    const result = await graphQlClient.graphql({
      query: createServer,
      variables: { input }
    });

    console.log('Server creation initiated:', result);
    
    // Parse the response to get instance ID if available
    if (result.data && result.data.createServer) {
      try {
        const response = JSON.parse(result.data.createServer);
        if (response.instanceId) {
          creationInstanceId.value = response.instanceId;
          // Subscribe to status updates for this instance
          subscribeToStatusUpdates(response.instanceId);
        }
      } catch {
        console.log('Could not parse createServer response for instance ID');
      }
    }
    
    creationStatus.value = 'Server creation queued. Please wait...';
    
    // Don't close dialog immediately - wait for completion status
    // emit('server-created') will be called when we receive COMPLETED status
    
  } catch (error) {
    console.error('Error creating server:', error);
    loading.value = false;
    creationStatus.value = '';
    
    // Enhanced error handling for creation failures
    if (error.errors && error.errors.length > 0) {
      const errorMessage = error.errors[0].message;
      
      // Handle specific validation errors
      if (errorMessage.includes('Server name')) {
        errors.value.serverName = errorMessage;
      } else if (errorMessage.includes('Instance type')) {
        errors.value.instanceType = errorMessage;
      } else if (errorMessage.includes('threshold') || errorMessage.includes('Threshold')) {
        if (shutdownMethod.value === 'CPUUtilization') {
          errors.value.cpuThreshold = errorMessage;
        } else if (shutdownMethod.value === 'Connections') {
          errors.value.connectionThreshold = errorMessage;
        } else {
          errors.value.general = errorMessage;
        }
      } else if (errorMessage.includes('Evaluation period') || errorMessage.includes('evaluation')) {
        errors.value.evaluationPeriod = errorMessage;
      } else if (errorMessage.includes('schedule') || errorMessage.includes('cron')) {
        if (errorMessage.toLowerCase().includes('start')) {
          errors.value.startSchedule = errorMessage;
        } else if (errorMessage.toLowerCase().includes('stop')) {
          errors.value.stopSchedule = errorMessage;
        } else {
          errors.value.general = errorMessage;
        }
      } else if (errorMessage.includes('Insufficient permissions') || errorMessage.includes('Unauthorized')) {
        errors.value.general = 'You do not have permission to create servers. Please contact an administrator.';
      } else if (errorMessage.includes('AWS') || errorMessage.includes('EC2')) {
        errors.value.general = 'AWS service error: ' + errorMessage + '. Please try again or contact support.';
      } else {
        errors.value.general = errorMessage;
      }
    } else if (error.networkError) {
      errors.value.general = 'Network error: Unable to connect to the server. Please check your connection and try again.';
    } else if (error.message) {
      errors.value.general = error.message;
    } else {
      errors.value.general = 'Failed to create server. Please try again.';
    }
  }
}

function subscribeToStatusUpdates(instanceId) {
  try {
    statusSubscription = graphQlClient.graphql({
      query: onPutServerActionStatus,
      variables: { id: instanceId }
    }).subscribe({
      next: ({ data }) => {
        if (data?.onPutServerActionStatus) {
          const status = data.onPutServerActionStatus;
          console.log('Server creation status update:', status);
          
          if (status.action === 'createServer') {
            if (status.status === 'PROCESSING') {
              creationStatus.value = status.message || 'Creating server...';
            } else if (status.status === 'COMPLETED') {
              creationStatus.value = status.message || 'Server created successfully!';
              loading.value = false;
              
              // Emit success event to trigger server list refresh
              emit('server-created');
              
              // Close dialog after a brief delay to show success message
              setTimeout(() => {
                closeDialog();
              }, 1500);
              
            } else if (status.status === 'FAILED') {
              creationStatus.value = '';
              loading.value = false;
              errors.value.general = status.message || 'Server creation failed. Please try again.';
            }
          }
        }
      },
      error: (error) => {
        console.error('Status subscription error:', error);
        // Don't show error to user as this is just for enhanced UX
      }
    });
  } catch (error) {
    console.error('Failed to subscribe to status updates:', error);
    // Continue without real-time updates
  }
}

// Cleanup subscription on component unmount
onUnmounted(() => {
  if (statusSubscription) {
    statusSubscription.unsubscribe();
  }
});
</script>

<template>
  <v-dialog 
    :model-value="visible" 
    @update:model-value="$emit('update:visible', $event)"
    max-width="600px" 
    :fullscreen="$vuetify.display.mobile"
    persistent 
    scrollable
    transition="dialog-bottom-transition"
  >
    <v-card>
      <v-overlay
        :model-value="loading"
        contained
        class="align-center justify-center"
      >
        <div class="text-center">
          <v-progress-circular
            indeterminate
            size="64"
            color="primary"
          ></v-progress-circular>
          <div v-if="creationStatus" class="mt-4 text-h6 text-white">
            {{ creationStatus }}
          </div>
        </div>
      </v-overlay>

      <v-card-title class="bg-primary text-white pa-6">
        <div class="d-flex align-center w-100">
          <v-icon class="me-3" size="28">mdi-server-plus</v-icon>
          <div>
            <div class="text-h5 font-weight-bold">Create New Server</div>
            <div class="text-body-2 opacity-90">Configure your new Minecraft server</div>
          </div>
          <v-spacer></v-spacer>
          <v-btn 
            icon 
            variant="text" 
            @click="closeDialog"
            class="text-white"
          >
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </div>
      </v-card-title>

      <v-card-text class="pa-6">
        <v-form @submit.prevent="submitForm">
          <!-- General Error Message -->
          <v-alert
            v-if="errors.general"
            type="error"
            class="mb-4"
            :text="errors.general"
          ></v-alert>

          <!-- Server Name -->
          <v-text-field
            v-model="serverName"
            label="Server Name"
            placeholder="my-minecraft-server"
            :error-messages="errors.serverName"
            :rules="[() => isServerNameValid || 'Invalid server name']"
            required
            class="mb-4"
            prepend-inner-icon="mdi-server"
          ></v-text-field>

          <!-- Instance Type -->
          <v-select
            v-model="instanceType"
            :items="instanceTypes"
            item-title="label"
            item-value="value"
            label="Instance Type"
            :error-messages="errors.instanceType"
            required
            class="mb-4"
            prepend-inner-icon="mdi-memory"
          >
            <template #item="{ props, item }">
              <v-list-item v-bind="props">
                <template #title>
                  <div class="d-flex justify-space-between align-center w-100">
                    <div>
                      <div class="font-weight-medium">{{ item.raw.label }}</div>
                      <div class="text-caption text-medium-emphasis">
                        {{ item.raw.cpu }} • {{ item.raw.memory }}
                      </div>
                    </div>
                    <div class="text-right">
                      <div class="font-weight-medium text-primary">{{ item.raw.cost }}</div>
                    </div>
                  </div>
                </template>
              </v-list-item>
            </template>
          </v-select>

          <!-- Instance Type Specifications Display -->
          <v-card v-if="selectedInstanceType" variant="outlined" class="mb-4">
            <v-card-text class="py-3">
              <div class="d-flex justify-space-between align-center">
                <div>
                  <div class="text-subtitle-2 font-weight-medium">{{ selectedInstanceType.label }}</div>
                  <div class="text-body-2 text-medium-emphasis">
                    {{ selectedInstanceType.cpu }} • {{ selectedInstanceType.memory }}
                  </div>
                </div>
                <div class="text-right">
                  <div class="text-h6 text-primary font-weight-bold">{{ selectedInstanceType.cost }}</div>
                  <div class="text-caption text-medium-emphasis">Estimated hourly cost</div>
                </div>
              </div>
            </v-card-text>
          </v-card>

          <!-- Shutdown Method -->
          <v-select
            v-model="shutdownMethod"
            :items="shutdownMethods"
            item-title="label"
            item-value="value"
            label="Shutdown Method"
            required
            class="mb-4"
            prepend-inner-icon="mdi-power"
          >
            <template #item="{ props, item }">
              <v-list-item v-bind="props">
                <template #title>
                  <div>
                    <div class="font-weight-medium">{{ item.raw.label }}</div>
                    <div class="text-caption text-medium-emphasis">{{ item.raw.description }}</div>
                  </div>
                </template>
              </v-list-item>
            </template>
          </v-select>

          <!-- CPU-based Shutdown Configuration -->
          <div v-if="showCpuFields" class="mb-4">
            <v-card variant="outlined">
              <v-card-title class="text-subtitle-1 py-3">
                <v-icon class="me-2">mdi-chip</v-icon>
                CPU-based Shutdown Configuration
              </v-card-title>
              <v-card-text>
                <v-row>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model.number="cpuThreshold"
                      label="CPU Threshold (%)"
                      type="number"
                      min="0"
                      max="100"
                      step="0.1"
                      :error-messages="errors.cpuThreshold"
                      suffix="%"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model.number="evaluationPeriod"
                      label="Evaluation Period (minutes)"
                      type="number"
                      min="1"
                      max="60"
                      :error-messages="errors.evaluationPeriod"
                      suffix="min"
                    ></v-text-field>
                  </v-col>
                </v-row>
                <div class="text-caption text-medium-emphasis">
                  Server will stop when CPU usage stays below {{ cpuThreshold }}% for {{ evaluationPeriod }} minutes
                </div>
              </v-card-text>
            </v-card>
          </div>

          <!-- Connection-based Shutdown Configuration -->
          <div v-if="showConnectionFields" class="mb-4">
            <v-card variant="outlined">
              <v-card-title class="text-subtitle-1 py-3">
                <v-icon class="me-2">mdi-account-multiple</v-icon>
                Connection-based Shutdown Configuration
              </v-card-title>
              <v-card-text>
                <v-row>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model.number="connectionThreshold"
                      label="Player Threshold"
                      type="number"
                      min="0"
                      max="100"
                      :error-messages="errors.connectionThreshold"
                      suffix="players"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model.number="evaluationPeriod"
                      label="Evaluation Period (minutes)"
                      type="number"
                      min="1"
                      max="60"
                      :error-messages="errors.evaluationPeriod"
                      suffix="min"
                    ></v-text-field>
                  </v-col>
                </v-row>
                <div class="text-caption text-medium-emphasis">
                  Server will stop when player count stays at or below {{ connectionThreshold }} for {{ evaluationPeriod }} minutes
                </div>
              </v-card-text>
            </v-card>
          </div>

          <!-- Scheduled Shutdown Configuration -->
          <div v-if="showScheduleFields" class="mb-4">
            <v-card variant="outlined">
              <v-card-title class="text-subtitle-1 py-3">
                <v-icon class="me-2">mdi-clock-outline</v-icon>
                Scheduled Shutdown Configuration
              </v-card-title>
              <v-card-text>
                <v-row>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="startSchedule"
                      label="Start Schedule (Cron)"
                      placeholder="0 18 * * 1-5"
                      :error-messages="errors.startSchedule"
                      prepend-inner-icon="mdi-play"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="stopSchedule"
                      label="Stop Schedule (Cron)"
                      placeholder="0 23 * * 1-5"
                      :error-messages="errors.stopSchedule"
                      prepend-inner-icon="mdi-stop"
                    ></v-text-field>
                  </v-col>
                </v-row>
                <div class="text-caption text-medium-emphasis">
                  Use cron expressions (minute hour day month day-of-week). Example: "0 18 * * 1-5" = 6 PM weekdays
                </div>
              </v-card-text>
            </v-card>
          </div>
        </v-form>
      </v-card-text>

      <v-card-actions class="pa-6 pt-0">
        <v-spacer></v-spacer>
        <v-btn
          variant="text"
          @click="closeDialog"
          :disabled="loading"
        >
          Cancel
        </v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          @click="submitForm"
          :disabled="!isFormValid || loading"
          :loading="loading"
        >
          Create Server
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
/* Mobile responsive adjustments */
@media (max-width: 599px) {
  :deep(.v-card-title) {
    padding: 16px !important;
  }
  
  :deep(.v-card-text) {
    padding: 12px !important;
  }
  
  :deep(.v-card-actions) {
    padding: 12px !important;
    padding-top: 0 !important;
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
}
</style>