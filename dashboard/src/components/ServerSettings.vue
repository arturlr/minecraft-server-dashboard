<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { useServerStore } from "../stores/server";
import { useUserStore } from "../stores/user";
import { parseGraphQLError, retryOperation } from "../utils/errorHandler";

const emit = defineEmits(['config-saved', 'close']);

const serverStore = useServerStore()
const userStore = useUserStore();

const settingsForm = ref();
const snackbar = ref(false)
const snackColor = ref(null)
const snackTimeout = ref(3500)
const snackText = ref('')

// Available shutdown methods
const shutdownMethodOptions = ref([
    { metric: 'CPUUtilization', abbr: '% CPU' },
    { metric: 'Connections', abbr: '# Users' },
    { metric: 'Schedule', abbr: 'Schedule' },
]);

// Function to update options with active label
function updateShutdownMethodOptions() {
    shutdownMethodOptions.value = [
        { 
            metric: 'CPUUtilization', 
            abbr: selectedShutdownMethod.value?.metric === 'CPUUtilization' ? '% CPU (Active)' : '% CPU'
        },
        { 
            metric: 'Connections', 
            abbr: selectedShutdownMethod.value?.metric === 'Connections' ? '# Users (Active)' : '# Users'
        },
        { 
            metric: 'Schedule', 
            abbr: selectedShutdownMethod.value?.metric === 'Schedule' ? 'Schedule (Active)' : 'Schedule'
        },
    ];
}

const selectedShutdownMethod = ref(shutdownMethodOptions.value[0]) // Select first item by default

// Watch for changes in selected shutdown method to update options
watch(selectedShutdownMethod, () => {
    updateShutdownMethodOptions();
}, { deep: true });

// ServerConfig Input - groupMembers will be processed 
const serverConfigInput = reactive({
    id: null,
    alarmThreshold: 0,
    alarmEvaluationPeriod: 0,
    runCommand: null,
    workDir: null,
    stopScheduleExpression: '',
    startScheduleExpression: '',
    shutdownMethod: null
});

// Variables for weekday scheduling
const selectedWeekdays = ref([]);
const selectedTime = ref(null);
const selectedStartTime = ref(null);
const enableStartSchedule = ref(false);
// Weekdays options for selection
const weekdayOptions = ref([
  { text: 'Select All', value: 'ALL' },
  { text: 'Monday', value: 'MON' },
  { text: 'Tuesday', value: 'TUE' },
  { text: 'Wednesday', value: 'WED' },
  { text: 'Thursday', value: 'THU' },
  { text: 'Friday', value: 'FRI' },
  { text: 'Saturday', value: 'SAT' },
  { text: 'Sunday', value: 'SUN' },
]);
// Time options for dropdown
const timeOptions = ref([]);

const settingsDialogLoading = ref(false);

// Generate time options in 30-minute intervals
for (let hour = 0; hour < 24; hour++) {
  for (let minute of [0, 30]) {
    const formattedHour = hour.toString().padStart(2, '0');
    const formattedMinute = minute.toString().padStart(2, '0');
    const timeValue = `${formattedHour}:${formattedMinute}`;
    const displayText = `${formattedHour}:${formattedMinute}`;
    timeOptions.value.push({ text: displayText, value: timeValue });
  }
}

// All weekday values for "Select All" option
const allWeekdayValues = computed(() => {
  return weekdayOptions.value
    .filter(option => option.value !== 'ALL')
    .map(option => option.value);
});

const isRequiredOnlyRules = [
    value => {
        if (value) return true
        return 'Field is required.'
    },
]

const onlyNumbersRules = [
    value => {
        if (value) return true
        return 'Field is required.'
    },
    value => {
        const pattern = /^[0-9]*$/;
        if (value && pattern.test(value)) return true
        return 'It must be numbers only.'
    },
]

const alphaNumericRules = [
    value => {
        const pattern = /^[a-zA-Z0-9_.-]*$/;
        if (value && pattern.test(value)) return true
        return '"Only alphanumeric or dot, underscore and dash are allowed.'
    },
]

// Watch for "Select All" option
function handleWeekdaySelection(newValue) {
  if (newValue.includes('ALL')) {
    // If "Select All" is selected, select all weekdays
    selectedWeekdays.value = [...allWeekdayValues.value];
  } else if (selectedWeekdays.value.length === allWeekdayValues.value.length) {
    // If all weekdays were previously selected and one is deselected, remove "Select All"
    selectedWeekdays.value = newValue.filter(day => day !== 'ALL');
  }
}

// Computed property for the hint
const selectedMethodHint = computed(() => {
    if (selectedShutdownMethod.value) {
        return `${selectedShutdownMethod.value.abbr} - ${selectedShutdownMethod.value.metric}`;
    }
    return '';
});

// Computed property to generate the cron expression from weekdays and time
const generatedCronExpression = computed(() => {
    if (!selectedTime.value || selectedWeekdays.value.length === 0 || 
        (selectedWeekdays.value.length === 1 && selectedWeekdays.value[0] === 'ALL')) {
        return null;
    }
    
    const [hours, minutes] = selectedTime.value.split(':');
    
    // Filter out the "ALL" option if present
    const weekdaysToUse = selectedWeekdays.value.filter(day => day !== 'ALL');
    
    // Cron format: minutes hours * * days_of_week (0-6, where 0 is Sunday)
    // Convert our weekday codes to cron numbers
    const weekdayMap = { 'SUN': 0, 'MON': 1, 'TUE': 2, 'WED': 3, 'THU': 4, 'FRI': 5, 'SAT': 6 };
    const cronWeekdays = weekdaysToUse.map(day => weekdayMap[day]).join(',');
    
    return `${minutes} ${hours} * * ${cronWeekdays}`;
});

// Computed property to generate start schedule cron expression
const generatedStartCronExpression = computed(() => {
    if (!enableStartSchedule.value || !selectedStartTime.value || selectedWeekdays.value.length === 0 || 
        (selectedWeekdays.value.length === 1 && selectedWeekdays.value[0] === 'ALL')) {
        return null;
    }
    
    const [hours, minutes] = selectedStartTime.value.split(':');
    
    // Filter out the "ALL" option if present
    const weekdaysToUse = selectedWeekdays.value.filter(day => day !== 'ALL');
    
    // Cron format: minutes hours * * days_of_week (0-6, where 0 is Sunday)
    // Convert our weekday codes to cron numbers
    const weekdayMap = { 'SUN': 0, 'MON': 1, 'TUE': 2, 'WED': 3, 'THU': 4, 'FRI': 5, 'SAT': 6 };
    const cronWeekdays = weekdaysToUse.map(day => weekdayMap[day]).join(',');
    
    return `${minutes} ${hours} * * ${cronWeekdays}`;
});

onMounted(async () => {
    await getServerSettings();
});

// Parse cron expression to extract weekdays and time
function parseCronExpression(cronExpression) {
    if (!cronExpression) return;
    
    const parts = cronExpression.split(' ');
    if (parts.length !== 5) return;
    
    const minutes = parts[0];
    const hours = parts[1];
    const weekdaysPart = parts[4];
    
    // Set time
    selectedTime.value = `${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}`;
    
    // Set weekdays
    const weekdayMap = { '0': 'SUN', '1': 'MON', '2': 'TUE', '3': 'WED', '4': 'THU', '5': 'FRI', '6': 'SAT' };
    const selectedDays = [];
    
    if (weekdaysPart.includes(',')) {
        const days = weekdaysPart.split(',');
        days.forEach(day => {
            if (weekdayMap[day]) {
                selectedDays.push(weekdayMap[day]);
            }
        });
    } else if (weekdayMap[weekdaysPart]) {
        selectedDays.push(weekdayMap[weekdaysPart]);
    }
    
    selectedWeekdays.value = selectedDays;
    
    // Check if all weekdays are selected
    if (selectedDays.length === 7) {
        selectedWeekdays.value.push('ALL');
    }
}

// Parse start schedule cron expression
function parseStartCronExpression(cronExpression) {
    if (!cronExpression) return;
    
    const parts = cronExpression.split(' ');
    if (parts.length !== 5) return;
    
    const minutes = parts[0];
    const hours = parts[1];
    
    // Set start time
    selectedStartTime.value = `${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}`;
    enableStartSchedule.value = true;
}

async function getServerSettings() {
    try {
        settingsDialogLoading.value = true;
        
        // Execute with retry logic for network errors
        const serverSettings = await retryOperation(async () => {
            return await serverStore.getServerConfig();
        });
        
        if (!serverSettings) {
            snackText.value = "No configuration found for this server";
            snackbar.value = true;
            snackColor.value = "warning";
            return;
        }

        // Find the shutdown method first
        const methodFromServer = serverSettings.shutdownMethod || 'CPUUtilization';
        const foundMethod = [
            { metric: 'CPUUtilization', abbr: '% CPU' },
            { metric: 'Connections', abbr: '# Users' },
            { metric: 'Schedule', abbr: 'Schedule' }
        ].find(option => option.metric === methodFromServer) || 
        { metric: 'CPUUtilization', abbr: '% CPU' };
        
        // Set the selected shutdown method for the UI first
        selectedShutdownMethod.value = foundMethod;
        updateShutdownMethodOptions();

        // Process server configuration data
        const updates = {
            id: serverStore.selectedServerId,
            alarmThreshold: Number(serverSettings.alarmThreshold) || 0,
            alarmEvaluationPeriod: Number(serverSettings.alarmEvaluationPeriod) || 0,
            runCommand: serverSettings.runCommand || '',
            workDir: serverSettings.workDir || '',            
            stopScheduleExpression: serverSettings.stopScheduleExpression || '',
            startScheduleExpression: serverSettings.startScheduleExpression || '',
            shutdownMethod: foundMethod
        };

        // Update all values at once
        Object.assign(serverConfigInput, updates);

        // Handle schedule expressions after the state update
        if (foundMethod.metric === 'Schedule') {
            if (serverSettings.stopScheduleExpression) {
                parseCronExpression(serverSettings.stopScheduleExpression);
            }
            if (serverSettings.startScheduleExpression) {
                parseStartCronExpression(serverSettings.startScheduleExpression);
            }
        }
        
    } catch (error) {
        console.error('Error loading server settings:', error);
        const errorMessage = parseGraphQLError(error);
        snackText.value = `Failed to load settings: ${errorMessage}`;
        snackbar.value = true;
        snackColor.value = "error";
    } finally {
        settingsDialogLoading.value = false;
    }
}


function resetForm() {
        serverConfigInput.alarmThreshold = 0,
        serverConfigInput.alarmEvaluationPeriod = 0,
        serverConfigInput.runCommand = "",
        serverConfigInput.workDir = "",
        //serverConfigInput.groupMember = '[]',
        serverConfigInput.stopScheduleExpression = "",
        serverConfigInput.startScheduleExpression = "",
        serverConfigInput.shutdownMethod = { metric: 'CPUUtilization', abbr: '% CPU' }
        selectedShutdownMethod.value = { metric: 'CPUUtilization', abbr: '% CPU' };
        selectedStartTime.value = null;
        enableStartSchedule.value = false;               
}

async function onSubmit() {
    settingsForm.value?.validate().then(async ({ valid: isValid }) => {
        if (isValid) {
            settingsDialogLoading.value = true;

            // Prepare the configuration data
            const configData = {
                id: serverStore.selectedServerId,
                shutdownMethod: selectedShutdownMethod.value.metric,
                alarmThreshold: serverConfigInput.alarmThreshold,
                alarmEvaluationPeriod: serverConfigInput.alarmEvaluationPeriod,
                runCommand: serverConfigInput.runCommand || '',
                workDir: serverConfigInput.workDir || '',
                stopScheduleExpression: generatedCronExpression.value || '',
                startScheduleExpression: generatedStartCronExpression.value || ''
            };
            
            try {
                // Execute with retry logic for network errors
                const serverSettings = await retryOperation(async () => {
                    return await serverStore.putServerConfig(configData);
                });
                
                if (serverSettings && serverSettings.id) {
                    snackText.value = "Configuration saved successfully!";
                    snackbar.value = true;
                    snackColor.value = "success";
                    
                    // Emit success event after a short delay to show the snackbar
                    setTimeout(() => {
                        emit('config-saved', 'Configuration saved successfully!');
                    }, 500);
                } else {
                    snackText.value = "Failed to save configuration. Please try again.";
                    snackbar.value = true;
                    snackColor.value = "error";
                }
            } catch (error) {
                console.error('Error updating server config:', error);
                const errorMessage = parseGraphQLError(error);
                snackText.value = `Failed to save: ${errorMessage}`;
                snackbar.value = true;
                snackColor.value = "error";
            }
            
            settingsDialogLoading.value = false;
        } else {
            snackText.value = "Please fix validation errors before saving";
            snackbar.value = true;
            snackColor.value = "warning";
        }
    })
}



</script>

<template>
    <div>
        <v-progress-linear 
            v-if="settingsDialogLoading" 
            indeterminate 
            height="3" 
            color="primary"
            class="position-absolute"
            style="top: 0; z-index: 1;"
        ></v-progress-linear>
        
        <v-form ref="settingsForm">
                    <!-- Shutdown Configuration Section -->
                    <div class="pa-6 border-b">
                        <div class="mb-6">
                            <div class="d-flex align-center mb-2">
                                <v-icon class="me-2 text-orange" size="24">mdi-power</v-icon>
                                <h3 class="text-h6 font-weight-bold">Auto-Shutdown Configuration</h3>
                            </div>
                            <p class="text-body-2 text-medium-emphasis ma-0">
                                Configure when to automatically shutdown the Minecraft server to save costs
                            </p>
                        </div>

                        <!-- Method Selection -->
                        <v-row class="mb-4">
                            <v-col cols="12" md="6">
                                <v-select 
                                    :items="shutdownMethodOptions" 
                                    item-title="abbr" 
                                    item-value="metric"
                                    :hint="selectedMethodHint" 
                                    label="Shutdown Method" 
                                    persistent-hint 
                                    return-object                                     
                                    v-model="selectedShutdownMethod"
                                    :rules="isRequiredOnlyRules"
                                    variant="outlined"
                                    prepend-inner-icon="mdi-timer"
                                    color="primary"
                                >
                                </v-select>
                            </v-col>
                        </v-row>

                        <!-- Schedule-based Configuration -->
                        <v-expand-transition>
                            <div v-if="selectedShutdownMethod?.metric === 'Schedule'">
                                <v-card variant="tonal" color="blue" class="mb-4">
                                    <v-card-text class="pa-4">
                                        <div class="d-flex align-center mb-3">
                                            <v-icon class="me-2" color="blue">mdi-calendar-clock</v-icon>
                                            <span class="font-weight-medium">Schedule Configuration</span>
                                        </div>
                                        <p class="text-body-2 ma-0">
                                            Set a schedule to automatically shutdown the server on specific days and times.
                                        </p>
                                    </v-card-text>
                                </v-card>

                                <v-row>
                                    <v-col cols="12" md="6">
                                        <v-select
                                            v-model="selectedWeekdays"
                                            :items="weekdayOptions"
                                            item-title="text"
                                            item-value="value"
                                            label="Select Days"
                                            multiple
                                            chips
                                            hint="Choose which days to apply the shutdown schedule"
                                            persistent-hint
                                            :rules="[v => v.length > 0 || 'At least one day must be selected']"
                                            @update:model-value="handleWeekdaySelection"
                                            variant="outlined"
                                            prepend-inner-icon="mdi-calendar"
                                        ></v-select>
                                    </v-col>
                                    <v-col cols="12" md="6">
                                        <v-select
                                            v-model="selectedTime"
                                            :items="timeOptions"
                                            item-title="text"
                                            item-value="value"
                                            label="Shutdown Time"
                                            hint="Time when the server should shutdown"
                                            persistent-hint
                                            :rules="[v => !!v || 'Please select a time']"
                                            :disabled="!selectedWeekdays.length"
                                            variant="outlined"
                                            prepend-inner-icon="mdi-clock"
                                        ></v-select>
                                    </v-col>
                                </v-row>

                                <v-row>
                                    <v-col cols="12">
                                        <v-checkbox
                                            v-model="enableStartSchedule"
                                            label="Also schedule server start time"
                                            hint="Enable automatic server startup at a specified time"
                                            persistent-hint
                                            density="comfortable"
                                            color="primary"
                                        ></v-checkbox>
                                    </v-col>
                                </v-row>

                                <v-expand-transition>
                                    <v-row v-if="enableStartSchedule">
                                        <v-col cols="12" md="6">
                                            <v-select
                                                v-model="selectedStartTime"
                                                :items="timeOptions"
                                                item-title="text"
                                                item-value="value"
                                                label="Start Time"
                                                hint="Time when the server should start"
                                                persistent-hint
                                                :rules="enableStartSchedule ? [v => !!v || 'Please select a start time'] : []"
                                                :disabled="!selectedWeekdays.length"
                                                variant="outlined"
                                                prepend-inner-icon="mdi-play"
                                            ></v-select>
                                        </v-col>
                                    </v-row>
                                </v-expand-transition>

                                <v-expand-transition>
                                    <div v-if="generatedCronExpression">
                                        <v-alert 
                                            type="info" 
                                            variant="tonal" 
                                            class="mt-4"
                                            border="start"
                                            border-color="info"
                                        >
                                            <template v-slot:prepend>
                                                <v-icon>mdi-information</v-icon>
                                            </template>
                                            <div class="font-weight-medium mb-2">Schedule Summary</div>
                                            <div v-if="enableStartSchedule && selectedStartTime" class="mb-2">
                                                Server will <strong>start at {{ selectedStartTime }}</strong> and <strong>shutdown at {{ selectedTime }}</strong> on 
                                                {{ selectedWeekdays.includes('ALL') ? 'all days' : 
                                                selectedWeekdays.filter(day => day !== 'ALL').join(', ') }}
                                            </div>
                                            <div v-else class="mb-2">
                                                Server will <strong>shutdown at {{ selectedTime }}</strong> on 
                                                {{ selectedWeekdays.includes('ALL') ? 'all days' : 
                                                selectedWeekdays.filter(day => day !== 'ALL').join(', ') }}
                                            </div>
                                            <div class="text-caption">
                                                <div v-if="enableStartSchedule && selectedStartTime">
                                                    Start cron: <code>{{ generatedStartCronExpression }}</code>
                                                </div>
                                                <div>Shutdown cron: <code>{{ generatedCronExpression }}</code></div>
                                            </div>
                                        </v-alert>
                                    </div>
                                </v-expand-transition>
                            </div>
                        </v-expand-transition>

                        <!-- Metric-based Configuration -->
                        <v-expand-transition>
                            <div v-if="selectedShutdownMethod && selectedShutdownMethod.metric !== 'Schedule'">
                                <v-card variant="tonal" color="orange" class="mb-4">
                                    <v-card-text class="pa-4">
                                        <div class="d-flex align-center mb-3">
                                            <v-icon class="me-2" color="orange">mdi-chart-line</v-icon>
                                            <span class="font-weight-medium">Metric-Based Configuration</span>
                                        </div>
                                        <p class="text-body-2 ma-0">
                                            Set threshold and evaluation period for automatic server shutdown based on {{ selectedShutdownMethod.abbr }}.
                                        </p>
                                    </v-card-text>
                                </v-card>

                                <v-row>
                                    <v-col cols="12" md="6">
                                        <v-text-field
                                            v-model="serverConfigInput.alarmThreshold"
                                            label="Threshold"
                                            :hint="selectedShutdownMethod.metric === 'CPUUtilization' ? 'Percentage of CPU utilization' : 'Number of connected users'"
                                            persistent-hint
                                            :suffix="selectedShutdownMethod.metric === 'CPUUtilization' ? '%' : ''"
                                            :rules="onlyNumbersRules"
                                            variant="outlined"
                                            prepend-inner-icon="mdi-speedometer"
                                        ></v-text-field>
                                    </v-col>
                                    <v-col cols="12" md="6">
                                        <v-text-field
                                            v-model="serverConfigInput.alarmEvaluationPeriod"
                                            label="Evaluation Period"
                                            hint="Number of minutes to evaluate the threshold"
                                            persistent-hint
                                            suffix="minutes"
                                            :rules="onlyNumbersRules"
                                            variant="outlined"
                                            prepend-inner-icon="mdi-timer-sand"
                                        ></v-text-field>
                                    </v-col>
                                </v-row>

                                <v-alert 
                                    type="info" 
                                    variant="tonal" 
                                    class="mt-4"
                                    border="start"
                                    border-color="info"
                                >
                                    <template v-slot:prepend>
                                        <v-icon>mdi-information</v-icon>
                                    </template>
                                    <div class="font-weight-medium">Shutdown Condition</div>
                                    <div>
                                        The server will shutdown when {{ selectedShutdownMethod.abbr }} is below 
                                        <strong>{{ serverConfigInput.alarmThreshold }}{{ selectedShutdownMethod.metric === 'CPUUtilization' ? '%' : ' users' }}</strong> 
                                        for <strong>{{ serverConfigInput.alarmEvaluationPeriod }} minutes</strong>
                                    </div>
                                </v-alert>
                            </div>
                        </v-expand-transition>
                    </div>

                    <!-- Server Execution Section -->
                    <div class="pa-6">
                        <div class="mb-6">
                            <div class="d-flex align-center mb-2">
                                <v-icon class="me-2 text-green" size="24">mdi-console</v-icon>
                                <h3 class="text-h6 font-weight-bold">Minecraft Server Execution</h3>
                            </div>
                            <p class="text-body-2 text-medium-emphasis ma-0">
                                Configure the Minecraft server run command and working directory
                            </p>
                        </div>

                        <v-row>
                            <v-col cols="12" md="6">
                                <v-text-field 
                                    v-model="serverConfigInput.workDir" 
                                    label="Working Directory"
                                    hint="Directory where the Minecraft server is located"
                                    persistent-hint
                                    prepend-inner-icon="mdi-folder"
                                    variant="outlined"
                                    placeholder="/home/minecraft/server"
                                ></v-text-field>
                            </v-col>
                            <v-col cols="12" md="6">
                                <v-text-field 
                                    v-model="serverConfigInput.runCommand" 
                                    label="Run Command"
                                    hint="Command to start the Minecraft server"
                                    persistent-hint
                                    prepend-inner-icon="mdi-play"
                                    variant="outlined"
                                    placeholder="java -jar server.jar"
                                ></v-text-field>
                            </v-col>
                        </v-row>
                    </div>
                </v-form>

                <!-- Actions -->
                <div class="pa-6 bg-grey-lighten-5">
                    <v-spacer></v-spacer>
                    <v-btn 
                        variant="text" 
                        @click="resetForm"
                        prepend-icon="mdi-refresh"
                        :disabled="settingsDialogLoading"
                    >
                        Clear
                    </v-btn>
                    <v-btn 
                        variant="text" 
                        @click="getServerSettings"
                        prepend-icon="mdi-reload"
                        :disabled="settingsDialogLoading"
                    >
                        Reload
                    </v-btn>
                    <v-btn 
                        variant="text" 
                        @click="emit('close')"
                        prepend-icon="mdi-close"
                        :disabled="settingsDialogLoading"
                    >
                        Cancel
                    </v-btn>
                    <v-btn 
                        color="primary" 
                        variant="elevated"
                        @click="onSubmit" 
                        :disabled="settingsDialogLoading"
                        :loading="settingsDialogLoading"
                        prepend-icon="mdi-content-save"
                        class="px-6"
                    >
                        Save Configuration
                    </v-btn>
                </div>

        <v-snackbar v-model="snackbar" :timeout="snackTimeout" :color="snackColor" outlined left centered text>
            {{ snackText }}

            <template v-slot:actions>
                <v-btn color="white" variant="text" @click="snackbar = false">
                    Close
                </v-btn>
            </template>
        </v-snackbar>
    </div>
</template>

<style scoped>
.custom-icon {
  color: #9e9e9e; /* Gray color by default */
  transition: color 0.3s ease;
}

.custom-icon:hover {
  color: #1976d2; /* Primary blue color on hover */
}
</style>
