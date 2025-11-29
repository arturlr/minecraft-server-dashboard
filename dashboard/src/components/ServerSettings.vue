<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { useServerStore } from "../stores/server";
import { useUserStore } from "../stores/user";
import { parseGraphQLError, retryOperation } from "../utils/errorHandler";
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

dayjs.extend(utc);
dayjs.extend(timezone);

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

// Auto-detect browser timezone
const detectedTimezone = ref(dayjs.tz.guess());

// Get friendly timezone name with offset
const timezoneDisplay = computed(() => {
    const tz = detectedTimezone.value;
    const offset = dayjs().tz(tz).format('Z');
    return `${tz} (UTC${offset})`;
});

// ServerConfig Input - groupMembers will be processed 
const serverConfigInput = reactive({
    id: null,
    alarmThreshold: 0,
    alarmEvaluationPeriod: 0,
    runCommand: null,
    workDir: null,
    stopScheduleExpression: '',
    startScheduleExpression: '',
    shutdownMethod: null,
    timezone: detectedTimezone.value
});

// Variables for weekday scheduling
const selectedWeekdays = ref([]);
const selectedTime = ref(null);
const selectedStartTime = ref(null);
const enableStartSchedule = ref(false);

// Weekdays options for selection
const weekdayOptions = ref([
  { text: 'Select All', value: 'ALL' },
  { text: 'Monday', value: 'MON', icon: 'mdi-alpha-m-circle' },
  { text: 'Tuesday', value: 'TUE', icon: 'mdi-alpha-t-circle' },
  { text: 'Wednesday', value: 'WED', icon: 'mdi-alpha-w-circle' },
  { text: 'Thursday', value: 'THU', icon: 'mdi-alpha-t-circle' },
  { text: 'Friday', value: 'FRI', icon: 'mdi-alpha-f-circle' },
  { text: 'Saturday', value: 'SAT', icon: 'mdi-alpha-s-circle' },
  { text: 'Sunday', value: 'SUN', icon: 'mdi-alpha-s-circle' },
]);

// Quick schedule presets
const schedulePresets = ref([
  { name: 'Weekday Evenings', days: ['MON', 'TUE', 'WED', 'THU', 'FRI'], start: '17:00', stop: '23:00' },
  { name: 'Weekend All Day', days: ['SAT', 'SUN'], start: '08:00', stop: '23:00' },
  { name: 'Every Evening', days: ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'], start: '18:00', stop: '23:00' },
  { name: 'Business Hours', days: ['MON', 'TUE', 'WED', 'THU', 'FRI'], start: '09:00', stop: '17:00' },
]);

// Common timezone options
const timezoneOptions = ref([
  { text: 'UTC', value: 'UTC' },
  { text: 'US/Eastern (EST/EDT)', value: 'America/New_York' },
  { text: 'US/Central (CST/CDT)', value: 'America/Chicago' },
  { text: 'US/Mountain (MST/MDT)', value: 'America/Denver' },
  { text: 'US/Pacific (PST/PDT)', value: 'America/Los_Angeles' },
  { text: 'Europe/London (GMT/BST)', value: 'Europe/London' },
  { text: 'Europe/Paris (CET/CEST)', value: 'Europe/Paris' },
  { text: 'Asia/Tokyo (JST)', value: 'Asia/Tokyo' },
  { text: 'Asia/Shanghai (CST)', value: 'Asia/Shanghai' },
  { text: 'Australia/Sydney (AEDT/AEST)', value: 'Australia/Sydney' },
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

// Computed property to check for schedule conflicts
const scheduleWarning = computed(() => {
    if (!enableStartSchedule.value || !selectedStartTime.value || !selectedTime.value) {
        return null;
    }
    
    const [startHour, startMin] = selectedStartTime.value.split(':').map(Number);
    const [stopHour, stopMin] = selectedTime.value.split(':').map(Number);
    
    const startMinutes = startHour * 60 + startMin;
    const stopMinutes = stopHour * 60 + stopMin;
    
    if (startMinutes >= stopMinutes) {
        return {
            type: 'warning',
            message: 'Start time is after or equal to stop time. Server will run for less than expected or across midnight.'
        };
    }
    
    const runningMinutes = stopMinutes - startMinutes;
    const runningHours = Math.floor(runningMinutes / 60);
    const remainingMinutes = runningMinutes % 60;
    
    if (runningMinutes < 60) {
        return {
            type: 'warning',
            message: `Server will only run for ${runningMinutes} minutes per day. Consider extending the schedule.`
        };
    }
    
    return {
        type: 'info',
        message: `Server will run for ${runningHours}h ${remainingMinutes}m per scheduled day.`
    };
});

// Computed property for metric-based shutdown warnings
const metricWarning = computed(() => {
    if (selectedShutdownMethod.value?.metric === 'Schedule') {
        return null;
    }
    
    const threshold = Number(serverConfigInput.alarmThreshold);
    const period = Number(serverConfigInput.alarmEvaluationPeriod);
    
    if (!threshold || !period) {
        return null;
    }
    
    if (selectedShutdownMethod.value?.metric === 'CPUUtilization') {
        if (threshold > 20) {
            return {
                type: 'warning',
                message: 'CPU threshold above 20% may cause premature shutdowns during normal gameplay.'
            };
        }
        if (period < 10) {
            return {
                type: 'warning',
                message: 'Evaluation period under 10 minutes may cause false shutdowns during temporary CPU spikes.'
            };
        }
    }
    
    if (selectedShutdownMethod.value?.metric === 'Connections') {
        if (threshold > 0 && period < 5) {
            return {
                type: 'warning',
                message: 'Short evaluation period may shutdown server when players briefly disconnect.'
            };
        }
    }
    
    return null;
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

// Apply a schedule preset
function applyPreset(preset) {
    selectedWeekdays.value = [...preset.days];
    selectedStartTime.value = preset.start;
    selectedTime.value = preset.stop;
    enableStartSchedule.value = true;
    
    snackText.value = `Applied preset: ${preset.name}`;
    snackbar.value = true;
    snackColor.value = "info";
}

// Computed property for the hint
const selectedMethodHint = computed(() => {
    if (selectedShutdownMethod.value) {
        return `${selectedShutdownMethod.value.abbr} - ${selectedShutdownMethod.value.metric}`;
    }
    return '';
});

// Helper to convert local time to UTC based on timezone
function convertToUTC(localTime, sourceTimezone) {
    if (!localTime || !sourceTimezone) return localTime;
    
    const [hours, minutes] = localTime.split(':').map(Number);
    
    // Create a date in the source timezone and convert to UTC
    const utcTime = dayjs.tz(`2000-01-01 ${localTime}`, sourceTimezone)
        .utc()
        .format('HH:mm');
    
    return utcTime;
}

// Helper to convert UTC time to local timezone
function convertFromUTC(utcTime, targetTimezone) {
    if (!utcTime || !targetTimezone) return utcTime;
    
    const [hours, minutes] = utcTime.split(':').map(Number);
    
    // Create a UTC date and convert to target timezone
    const localTime = dayjs.utc()
        .hour(hours)
        .minute(minutes)
        .tz(targetTimezone)
        .format('HH:mm');
    
    return localTime;
}

// Helper to generate cron expression from time and weekdays (keeps local time, backend will convert to UTC)
function generateCronExpression(time, weekdays) {
    if (!time || !weekdays?.length || (weekdays.length === 1 && weekdays[0] === 'ALL')) {
        return null;
    }
    
    // Keep time in local timezone - backend will convert to UTC
    const [hours, minutes] = time.split(':');
    
    const weekdayToCron = { 'SUN': 0, 'MON': 1, 'TUE': 2, 'WED': 3, 'THU': 4, 'FRI': 5, 'SAT': 6 };
    const cronWeekdays = weekdays
        .filter(day => day !== 'ALL')
        .map(day => weekdayToCron[day])
        .join(',');
    
    // Return standard 5-field cron expression in local time (backend will convert to UTC)
    return `${minutes} ${hours} * * ${cronWeekdays}`;
}

// Computed property to generate the cron expression from weekdays and time
const generatedCronExpression = computed(() => 
    generateCronExpression(selectedTime.value, selectedWeekdays.value)
);

// Computed property to generate start schedule cron expression
const generatedStartCronExpression = computed(() => 
    enableStartSchedule.value ? generateCronExpression(selectedStartTime.value, selectedWeekdays.value) : null
);

onMounted(async () => {
    await getServerSettings();
});

// Weekday mapping for standard cron (0-6, Sunday=0)
const WEEKDAY_MAP = { 
    '0': 'SUN', '1': 'MON', '2': 'TUE', '3': 'WED', 
    '4': 'THU', '5': 'FRI', '6': 'SAT'
};

// Parse standard cron expression to extract time and weekdays (already in local timezone from backend)
function parseCronExpression(cronExpression, isStartSchedule = false) {
    if (!cronExpression) return;
    
    const parts = cronExpression.trim().split(' ');
    
    // Expect standard 5-field cron: minute hour day month day-of-week
    if (parts.length !== 5) {
        console.warn('Invalid cron expression format (expected 5 fields):', cronExpression);
        return;
    }
    
    const [minutes, hours, , , weekdaysPart] = parts;
    // Backend stores cron in local time, so no conversion needed
    const localTime = `${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}`;
    
    // Set time based on schedule type
    if (isStartSchedule) {
        selectedStartTime.value = localTime;
        enableStartSchedule.value = true;
        return; // Start schedule doesn't need weekday parsing
    }
    
    selectedTime.value = localTime;
    
    // Parse weekdays if not wildcard
    if (weekdaysPart === '*') {
        console.warn('Cron expression uses wildcard for weekdays, cannot parse specific days');
        return;
    }
    
    const selectedDays = weekdaysPart.split(',')
        .map(day => WEEKDAY_MAP[day.trim()])
        .filter((day, index, self) => day && self.indexOf(day) === index); // Remove duplicates
    
    selectedWeekdays.value = selectedDays.length === 7 ? [...selectedDays, 'ALL'] : selectedDays;
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
            shutdownMethod: foundMethod,
            timezone: detectedTimezone.value  // Always use browser's detected timezone
        };

        // Update all values at once
        Object.assign(serverConfigInput, updates);

        // Handle schedule expressions after the state update
        if (foundMethod.metric === 'Schedule') {
            if (serverSettings.stopScheduleExpression) {
                parseCronExpression(serverSettings.stopScheduleExpression, false);
            }
            if (serverSettings.startScheduleExpression) {
                parseCronExpression(serverSettings.startScheduleExpression, true);
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
        serverConfigInput.timezone = detectedTimezone.value
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
                startScheduleExpression: generatedStartCronExpression.value || '',
                timezone: serverConfigInput.timezone || 'UTC'
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
    <div class="position-relative">
        <v-progress-linear 
            v-if="settingsDialogLoading" 
            indeterminate 
            height="3" 
            color="primary"
            class="position-absolute"
            style="top: 0; z-index: 1;"
        ></v-progress-linear>
        
        <!-- Loading Overlay -->
        <v-overlay
            :model-value="settingsDialogLoading"
            contained
            class="align-center justify-center"
            persistent
        >
            <div class="text-center">
                <v-progress-circular
                    indeterminate
                    size="64"
                    width="6"
                    color="primary"
                ></v-progress-circular>
                <div class="mt-4 text-h6">Loading server settings...</div>
                <div class="text-body-2 text-medium-emphasis mt-2">Please wait</div>
            </div>
        </v-overlay>
        
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
                            <v-col cols="12" md="6" v-if="selectedShutdownMethod?.metric === 'Schedule'">
                                <v-alert
                                    type="info"
                                    variant="tonal"
                                    density="compact"
                                    class="mb-0"
                                >
                                    <div class="d-flex align-center">
                                        <v-icon class="me-2" size="20">mdi-earth</v-icon>
                                        <div>
                                            <div class="text-subtitle-2 font-weight-medium">Detected Timezone</div>
                                            <div class="text-body-2">{{ timezoneDisplay }}</div>
                                            <div class="text-caption text-medium-emphasis">Schedule times will use your local timezone</div>
                                        </div>
                                    </div>
                                </v-alert>
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

                                <!-- Quick Presets -->
                                <v-card variant="outlined" class="mb-4">
                                    <v-card-text class="pa-4">
                                        <div class="d-flex align-center mb-3">
                                            <v-icon class="me-2" size="20">mdi-lightning-bolt</v-icon>
                                            <span class="text-subtitle-2 font-weight-medium">Quick Presets</span>
                                        </div>
                                        <div class="d-flex flex-wrap gap-2">
                                            <v-chip
                                                v-for="preset in schedulePresets"
                                                :key="preset.name"
                                                @click="applyPreset(preset)"
                                                variant="outlined"
                                                color="primary"
                                                class="cursor-pointer"
                                                prepend-icon="mdi-clock-fast"
                                            >
                                                {{ preset.name }}
                                            </v-chip>
                                        </div>
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
                                            :hint="`Time when the server should shutdown (${serverConfigInput.timezone})`"
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
                                                :hint="`Time when the server should start (${serverConfigInput.timezone})`"
                                                persistent-hint
                                                :rules="enableStartSchedule ? [v => !!v || 'Please select a start time'] : []"
                                                :disabled="!selectedWeekdays.length"
                                                variant="outlined"
                                                prepend-inner-icon="mdi-play"
                                            ></v-select>
                                        </v-col>
                                    </v-row>
                                </v-expand-transition>

                                <!-- Schedule Warnings -->
                                <v-expand-transition>
                                    <v-alert 
                                        v-if="scheduleWarning"
                                        :type="scheduleWarning.type" 
                                        variant="tonal" 
                                        class="mt-4"
                                        border="start"
                                    >
                                        <template v-slot:prepend>
                                            <v-icon>{{ scheduleWarning.type === 'warning' ? 'mdi-alert' : 'mdi-information' }}</v-icon>
                                        </template>
                                        {{ scheduleWarning.message }}
                                    </v-alert>
                                </v-expand-transition>

                                <!-- Schedule Summary -->
                                <v-expand-transition>
                                    <div v-if="generatedCronExpression">
                                        <v-card variant="outlined" class="mt-4" color="primary">
                                            <v-card-text class="pa-4">
                                                <div class="d-flex align-center mb-3">
                                                    <v-icon class="me-2" color="primary">mdi-calendar-check</v-icon>
                                                    <span class="font-weight-bold">Schedule Summary</span>
                                                </div>
                                                
                                                <!-- Visual Day Indicators -->
                                                <div class="d-flex gap-2 mb-4 flex-wrap">
                                                    <v-chip
                                                        v-for="day in weekdayOptions.filter(d => d.value !== 'ALL')"
                                                        :key="day.value"
                                                        :color="selectedWeekdays.includes(day.value) ? 'primary' : 'default'"
                                                        :variant="selectedWeekdays.includes(day.value) ? 'flat' : 'outlined'"
                                                        size="small"
                                                        class="font-weight-medium"
                                                    >
                                                        {{ day.text.substring(0, 3) }}
                                                    </v-chip>
                                                </div>

                                                <div v-if="enableStartSchedule && selectedStartTime" class="mb-3">
                                                    <div class="d-flex align-center mb-2">
                                                        <v-icon size="20" class="me-2" color="success">mdi-play-circle</v-icon>
                                                        <span class="text-body-2">
                                                            Server <strong class="text-success">starts</strong> at 
                                                            <strong>{{ selectedStartTime }}</strong>
                                                        </span>
                                                    </div>
                                                    <div class="d-flex align-center">
                                                        <v-icon size="20" class="me-2" color="error">mdi-stop-circle</v-icon>
                                                        <span class="text-body-2">
                                                            Server <strong class="text-error">stops</strong> at 
                                                            <strong>{{ selectedTime }}</strong>
                                                        </span>
                                                    </div>
                                                </div>
                                                <div v-else class="mb-3">
                                                    <div class="d-flex align-center">
                                                        <v-icon size="20" class="me-2" color="error">mdi-stop-circle</v-icon>
                                                        <span class="text-body-2">
                                                            Server <strong class="text-error">stops</strong> at 
                                                            <strong>{{ selectedTime }}</strong>
                                                        </span>
                                                    </div>
                                                </div>

                                                <v-divider class="my-3"></v-divider>

                                                <div class="text-caption text-medium-emphasis">
                                                    <div v-if="enableStartSchedule && selectedStartTime" class="mb-1">
                                                        <v-icon size="16" class="me-1">mdi-code-braces</v-icon>
                                                        Start: <code class="text-caption">{{ generatedStartCronExpression }}</code>
                                                    </div>
                                                    <div>
                                                        <v-icon size="16" class="me-1">mdi-code-braces</v-icon>
                                                        Stop: <code class="text-caption">{{ generatedCronExpression }}</code>
                                                    </div>
                                                </div>
                                            </v-card-text>
                                        </v-card>
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

                                <!-- Metric Warning -->
                                <v-expand-transition>
                                    <v-alert 
                                        v-if="metricWarning"
                                        :type="metricWarning.type" 
                                        variant="tonal" 
                                        class="mt-4"
                                        border="start"
                                    >
                                        <template v-slot:prepend>
                                            <v-icon>mdi-alert</v-icon>
                                        </template>
                                        {{ metricWarning.message }}
                                    </v-alert>
                                </v-expand-transition>

                                <!-- Shutdown Condition Summary -->
                                <v-card variant="outlined" class="mt-4" color="orange">
                                    <v-card-text class="pa-4">
                                        <div class="d-flex align-center mb-3">
                                            <v-icon class="me-2" color="orange">mdi-information</v-icon>
                                            <span class="font-weight-bold">Shutdown Condition</span>
                                        </div>
                                        <div class="text-body-2">
                                            The server will <strong class="text-error">automatically shutdown</strong> when 
                                            {{ selectedShutdownMethod.abbr }} is 
                                            <strong class="text-orange">≤ {{ serverConfigInput.alarmThreshold }}{{ selectedShutdownMethod.metric === 'CPUUtilization' ? '%' : ' users' }}</strong> 
                                            for <strong class="text-orange">{{ serverConfigInput.alarmEvaluationPeriod }} consecutive minutes</strong>
                                        </div>
                                        
                                        <v-divider class="my-3"></v-divider>
                                        
                                        <div class="d-flex align-center text-caption text-medium-emphasis">
                                            <v-icon size="16" class="me-1">mdi-lightbulb-on-outline</v-icon>
                                            <span>
                                                <strong>Tip:</strong> 
                                                {{ selectedShutdownMethod.metric === 'CPUUtilization' 
                                                    ? 'Lower CPU thresholds (3-5%) work well for idle detection' 
                                                    : 'Set to 0 users to shutdown when server is empty' }}
                                            </span>
                                        </div>
                                    </v-card-text>
                                </v-card>
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
  color: #9e9e9e;
  transition: color 0.3s ease;
}

.custom-icon:hover {
  color: #1976d2;
}

.cursor-pointer {
  cursor: pointer;
  transition: transform 0.2s ease;
}

.cursor-pointer:hover {
  transform: translateY(-2px);
}

.gap-2 {
  gap: 8px;
}

code {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.875em;
}

.border-b {
  border-bottom: 1px solid rgba(0, 0, 0, 0.12);
}
</style>
