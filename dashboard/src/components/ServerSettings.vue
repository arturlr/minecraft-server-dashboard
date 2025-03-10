<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { useServerStore } from "../stores/server";
import { useUserStore } from "../stores/user";

const serverStore = useServerStore()
const userStore = useUserStore();

const settingsForm = ref();
const addUserForm = ref();
const snackbar = ref(false)
const snackColor = ref(null)
const snackTimeout = ref(3500)

// Available shutdown methods
const shutdownMethodOptions = ref([
    { metric: 'CPUUtilization', abbr: '% CPU' },
    { metric: 'Connections', abbr: '# Users' },
    { metric: 'Schedule', abbr: 'Schedule' },
]);

const selectedShutdownMethod = ref(shutdownMethodOptions.value[0]) // Select first item by default

// ServerConfig Input - groupMembers will be processed 
const serverConfigInput = reactive({
    id: null,
    alarmThreshold: 0,
    alarmEvaluationPeriod: 0,
    runCommand: null,
    workDir: null,
    scheduleExpression: '',
    shutdownMethod: null 
});

const groupMembers = ref([])

// Variables for weekday scheduling
const selectedWeekdays = ref([]);
const selectedTime = ref(null);
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

const inviteeEmail = ref()

const settingsDialogLoading = ref(false);
const configDialogVisible = ref(false);
const usersDialogVisible = ref(false);

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
    if (serverConfigInput.shutdownMethod) {
        return `${serverConfigInput.shutdownMethod.abbr}, ${serverConfigInput.shutdownMethod.metric}`;
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

function generateUniqueId() {
  const timestamp = Date.now();
  const randomNumber = Math.random();
  const hexadecimalString = randomNumber.toString(16).substring(2, 8);

  return `${timestamp}-${hexadecimalString}`;
}

function openConfigDialog() {
  configDialogVisible.value = true;
}

function openUsersDialog() {
  usersDialogVisible.value = true;
}

onMounted(async () => {
    await getServerSettings();
});

function getEpochTime (days) {
    const currentTime = new Date().getTime(); // Get the current time in milliseconds
    const epochTime = currentTime + (days * 24 * 60 * 60 * 1000); // Calculate the future time by adding the number of milliseconds for the given days
    return epochTime;
}

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

async function getServerSettings() {
    try {
        settingsDialogLoading.value = true;
        const serverSettings = await serverStore.getServerConfig();
        
        if (!serverSettings) {
            return;
        }

        // Users are processed separately 
        const updates = {
            id: serverStore.selectedServer.id,
            alarmThreshold: Number(serverSettings.alarmThreshold) || 0,
            alarmEvaluationPeriod: Number(serverSettings.alarmEvaluationPeriod) || 0,
            runCommand: serverSettings.runCommand || null,
            workDir: serverSettings.workDir || null,            
            scheduleExpression: serverSettings.scheduleExpression || '',
            shutdownMethod: null
        };

        groupMembers.value = JSON.parse(serverSettings.groupMembers || '[]')

        // Find the shutdown method
        const methodFromServer = serverSettings.shutdownMethod || 'CPUUtilization';
        updates.shutdownMethod = shutdownMethodOptions.value.find(
            option => option.metric === methodFromServer
        ) || shutdownMethodOptions.value[0].metric;

        // Update all values at once
        Object.assign(serverConfigInput, updates);

        // Handle schedule expression after the state update
        if (serverSettings.scheduleExpression) {
            parseCronExpression(serverSettings.scheduleExpression);
        }
        
    } catch (error) {
        console.error('Error loading server settings:', error);
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
        serverConfigInput.scheduleExpression = "",
        serverConfigInput.shutdownMethod = shutdownMethodOptions.value[0].metric                
}

async function onSubmit() {
    settingsForm.value?.validate().then(async ({ valid: isValid }) => {
        if (isValid) {
            settingsDialogLoading.value = true;

            serverConfigInput.shutdownMethod = selectedShutdownMethod.value.metric
            serverConfigInput.id = serverStore.selectedServer.id
            serverConfigInput.scheduleExpression = generatedCronExpression.value
            
            const serverSettings = await serverStore.putServerConfig(serverConfigInput);
            if (serverSettings === serverStore.selectedServer.id) {
                snackText.value = "Setting Updated Successfully";
                snackbar.value = true;
                snackColor.value = "primary";
                configDialogVisible.value = false;
            }
            settingsDialogLoading.value = false;
        }
    })
}


async function writeLog(msg) {
    // Calculating expiration time
    const d = new Date();
    d.setDate(d.getDate() + 60);
    const expirationEpoch = Math.round(d.getTime() / 1000);

    await $store.dispatch("profile/saveAuditLogin", {
        email: email,
        action: msg,
        expirationEpoch: expirationEpoch,
    });
}

async function addUser() {
    addUserForm.value?.validate().then(async ({ valid: isValid }) => {
        if (isValid) {
            const input = {
                id: generateUniqueId(),
                actionUser: userStore.email,
                action: "add_user",
                instanceId: serverStore.selectedServer.id,
                inviteeEmail: inviteeEmail.value + "@gmail.com",
                expirationEpoch: getEpochTime(1)
            };

            const result = await serverStore.putLogAudit(input);
            console.log(result)
        }
    })
}
</script>

<template>
    <!-- Main buttons to open dialogs -->
    <div class="d-flex mb-4 pt-4 pl-4">
    <v-tooltip top>
      <template v-slot:activator="{ on, attrs }">
        <v-icon
          size="large"
          class="mr-2 custom-icon"
          v-bind="attrs"
          v-on="on"
          @click="openConfigDialog"
        >
        mdi-cog-outline
        </v-icon>
      </template>
      <span>Server Configuration</span>
    </v-tooltip>

    <v-tooltip top>
      <template v-slot:activator="{ on, attrs }">
        <v-icon
          size="large"
          class="custom-icon"
          v-bind="attrs"
          v-on="on"
          @click="openUsersDialog"
        >
          mdi-account-plus-outline
        </v-icon>
      </template>
      <span>Manage Users</span>
    </v-tooltip>
  </div>

    <!-- Configuration Dialog -->
    <v-dialog v-model="configDialogVisible" max-width="800px">
        <v-card>
            <v-progress-linear v-if="settingsDialogLoading" indeterminate height="5" value="5" color="teal">
            </v-progress-linear>
            <v-card-title class="text-h5">
                Server Configuration
                <v-spacer></v-spacer>
                <v-btn icon @click="configDialogVisible = false">
                    <v-icon>mdi-close</v-icon>
                </v-btn>
            </v-card-title>
            <v-card-text>
                <v-form ref="settingsForm">
                    <v-container>
                        <v-row>
                            <v-col cols="12">
                                <h3 class="text-h5 mb-4">Server Shutdown Configuration</h3>
                                <span class="font-weight-light">Configure when to automatically shutdown the Minecraft server</span>
                            </v-col>
                        </v-row>

                        <!-- Method Selection -->
                        <v-row>
                            <v-col cols="4">
                                <v-select 
                                    :items="shutdownMethodOptions" 
                                    item-title="abbr" 
                                    item-value="metric"
                                    :hint="selectedMethodHint" 
                                    dense 
                                    label="Shutdown Method" 
                                    single-line 
                                    persistent-hint 
                                    return-object                                     
                                    v-model="selectedShutdownMethod"
                                    :rules="isRequiredOnlyRules"
                                >
                                </v-select>
                            </v-col>
                        </v-row>

                        <!-- Schedule-based alarm configuration -->
                        <v-row v-if="selectedShutdownMethod?.metric === 'Schedule'">
                            <v-col cols="12">
                                <span class="font-weight-light">Set a schedule to automatically shutdown the server on specific days and time.</span>
                            </v-col>
                            <v-col cols="6">
                                <v-select
                                    v-model="selectedWeekdays"
                                    :items="weekdayOptions"
                                    item-title="text"
                                    item-value="value"
                                    label="Select Days"
                                    multiple
                                    chips
                                    hint="Select days when the server should shutdown"
                                    persistent-hint
                                    :rules="[v => v.length > 0 || 'At least one day must be selected']"
                                    @update:model-value="handleWeekdaySelection"
                                ></v-select>
                            </v-col>
                            <v-col cols="6">
                                <v-select
                                    v-model="selectedTime"
                                    :items="timeOptions"
                                    item-title="text"
                                    item-value="value"
                                    label="Shutdown Time"
                                    hint="Select time when the server should shutdown"
                                    persistent-hint
                                    :rules="[v => !!v || 'Please select a time']"
                                    :disabled="!selectedWeekdays.length"
                                ></v-select>
                            </v-col>
                            <v-col cols="12" v-if="generatedCronExpression">
                                <v-alert type="info" variant="tonal" density="compact">
                                    The server will shutdown at {{ selectedTime }} on 
                                    {{ selectedWeekdays.includes('ALL') ? 'all days' : 
                                    selectedWeekdays.filter(day => day !== 'ALL').join(', ') }}
                                    <br>
                                    <small>Cron expression: {{ generatedCronExpression }}</small>
                                </v-alert>
                            </v-col>
                        </v-row>

                        <!-- Metric-based alarm configuration -->
                        <v-row v-if="selectedShutdownMethod && selectedShutdownMethod.metric !== 'Schedule'">
                            <v-col cols="12">
                                <span class="font-weight-light">Set threshold and evaluation period for automatic server shutdown based on {{ selectedShutdownMethod.abbr }}.</span>
                            </v-col>
                            <v-col cols="6">
                                <v-text-field
                                    v-model="serverConfigInput.alarmThreshold"
                                    dense
                                    label="Threshold"
                                    :hint="selectedShutdownMethod.metric === 'CPUUtilization' ? 'Percentage of CPU utilization' : 'Number of connected users'"
                                    persistent-hint
                                    :suffix="selectedShutdownMethod.metric === 'CPUUtilization' ? '%' : ''"
                                    :rules="onlyNumbersRules"
                                ></v-text-field>
                            </v-col>
                            <v-col cols="6">
                                <v-text-field
                                    v-model="serverConfigInput.alarmEvaluationPeriod"
                                    dense
                                    label="Evaluation Period"
                                    hint="Number of minutes to evaluate the threshold"
                                    persistent-hint
                                    suffix="minutes"
                                    :rules="onlyNumbersRules"
                                ></v-text-field>
                            </v-col>
                            <v-col cols="12">
                                <v-alert type="info" variant="tonal" density="compact">
                                    The server will shutdown when {{ selectedShutdownMethod.abbr }} is below 
                                    {{ serverConfigInput.alarmThreshold }}{{ selectedShutdownMethod.metric === 'CPUUtilization' ? '%' : ' users' }} 
                                    for {{ serverConfigInput.alarmEvaluationPeriod }} minutes
                                </v-alert>
                            </v-col>
                        </v-row>

                        <!-- Divider -->
                        <v-divider class="my-6"></v-divider>

                        <!-- Minecraft Run Command Section -->
                        <v-row>
                            <v-col cols="12">
                                <h3 class="text-h5 mb-4">Minecraft Server Execution</h3>
                                <span class="font-weight-light">Configure the Minecraft server run command and working directory</span>
                            </v-col>
                        </v-row>
                        <v-row>
                            <v-col cols="6">
                                <v-text-field 
                                    dense 
                                    v-model="serverConfigInput.workDir" 
                                    label="Working directory"
                                    hint="Directory where the Minecraft server is located"
                                    persistent-hint
                                    prepend-icon="mdi-folder"
                                ></v-text-field>
                            </v-col>
                            <v-col cols="6">
                                <v-text-field 
                                    dense 
                                    v-model="serverConfigInput.runCommand" 
                                    label="Run command"
                                    hint="Command to start the Minecraft server"
                                    persistent-hint
                                    prepend-icon="mdi-console"
                                ></v-text-field>
                            </v-col>
                        </v-row>
                    </v-container>
                </v-form>

            </v-card-text>
            <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn text @click="resetForm">Clear</v-btn>
                <v-btn text @click="getServerSettings">Reload</v-btn>
                <v-btn color="primary" text @click="onSubmit" :disabled="settingsDialogLoading">
                    <v-icon left>mdi-content-save</v-icon>
                    Save
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <!-- Users Dialog -->
    <v-dialog v-model="usersDialogVisible" max-width="600px">
        <v-card>
            <v-card-title class="text-h5">
                Manage Users
                <v-spacer></v-spacer>
                <v-btn icon @click="usersDialogVisible = false">
                    <v-icon>mdi-close</v-icon>
                </v-btn>
            </v-card-title>
            <v-card-text>
                <v-container>
                    <v-row>
                        <v-col cols="12">
                            <v-list two-line>
                                <v-list-header>Current Members</v-list-header>
                                <v-list-item v-for="user in groupMembers" :key="user.id">
                                    <v-list-item-content>
                                        <v-list-item-title v-text="user.fullname"></v-list-item-title>
                                        <v-list-item-subtitle v-text="user.email"></v-list-item-subtitle>
                                    </v-list-item-content>
                                </v-list-item>
                            </v-list>
                        </v-col>
                    </v-row>
                    <v-row>
                        <v-col cols="12">
                            <v-form ref="addUserForm">
                                <v-text-field dense label="Email address" v-model="inviteeEmail" suffix="@gmail.com"
                                    :rules="alphaNumericRules"></v-text-field>
                            </v-form>
                        </v-col>
                    </v-row>
                </v-container>
            </v-card-text>
            <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn color="primary" text @click="addUser()">
                    <v-icon left>mdi-account-plus</v-icon>
                    Add User
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :timeout="snackTimeout" :color="snackColor" outlined left centered text>
        {{ snackText }}

        <template v-slot:actions>
            <v-btn color="white" variant="text" @click="snackbar = false">
                Close
            </v-btn>
        </template>
    </v-snackbar>
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
