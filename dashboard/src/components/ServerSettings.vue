<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { useServerStore } from "../stores/server";
import { useUserStore } from "../stores/user";

const serverStore = useServerStore()
const userStore = useUserStore();

const settingsForm = ref();
const addUserForm = ref();
const snackbar = ref(false)
const snackText = ref(null)
const snackColor = ref(null)
const snackTimeout = ref(3500)
const workDir = ref(null);
const runCommand = ref(null);
const workingDir = ref(null);
const alarmMetric = ref({ metric: 'CPUUtilization', abbr: '% CPU' });
const alarmEvaluationPeriod = ref();
const alarmMetricItems = ref([
    { metric: 'CPUUtilization', abbr: '% CPU' },
    { metric: 'Connections', abbr: '# Users' },
]);
const alarmThreshold = ref(null);

const inviteeEmail = ref()

const settingsDialogLoading = ref(false);

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

function generateUniqueId() {
  const timestamp = Date.now();
  const randomNumber = Math.random();
  const hexadecimalString = randomNumber.toString(16).substring(2, 8);

  return `${timestamp}-${hexadecimalString}`;
}

onMounted(async () => {
    const serverSettings = await serverStore.getServerConfig(serverStore.selectedServer.id);
    // console.log(serverSettings)
    alarmThreshold.value = serverSettings.alarmThreshold;
    alarmEvaluationPeriod.value = serverSettings.alarmEvaluationPeriod
});

const groupMembers = computed(() => {
    if (
        serverStore.selectedServer.groupMembers &&
        serverStore.selectedServer.groupMembers.length > 0
    ) {
        return JSON.parse(serverStore.selectedServer.groupMembers);
    } else {
        return [];
    }
});

function getEpochTime (days) {
    const currentTime = new Date().getTime(); // Get the current time in milliseconds
    const epochTime = currentTime + (days * 24 * 60 * 60 * 1000); // Calculate the future time by adding the number of milliseconds for the given days
    return epochTime;
}

function resetForm() {
    alarmThreshold.value = null
    alarmEvaluationPeriod.value = null
}

async function onSubmit() {
    settingsForm.value?.validate().then(async ({ valid: isValid }) => {
        if (isValid) {
            const input = {
                id: serverStore.selectedServer.id,
                alarmType: alarmMetric.value.metric,
                alarmThreshold: parseFloat(alarmThreshold.value),
                alarmEvaluationPeriod: parseInt(alarmEvaluationPeriod.value, 10),
                runCommand: runCommand.value ?? '',
                workDir: workDir.value ?? ''
            }
            const serverSettings = await serverStore.putServerConfig(input);
            if (serverSettings === serverStore.selectedServer.id) {
                snackText.value = "Setting Updated Successfuly";
                snackbar.value = true;
                snackColor.value = "primary"
            }
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

            //powerButtonDialog.value = false;
            //addUserDialog.value = false;

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

    <v-progress-linear v-if="settingsDialogLoading" indeterminate height="5" value="5" color="teal">
    </v-progress-linear>
    <v-expansion-panels variant="accordion">
        <v-expansion-panel>
            <v-expansion-panel-title>Configuration</v-expansion-panel-title>
            <v-expansion-panel-text>
                <v-form ref="settingsForm">
                    <v-container>
                        <v-row>
                            <v-col cols="12">
                                <span class="font-weight-light">The alarm configuration evaluates if the CPU%
                                    utilization is under the threshold for the specified number of evaluation periods to
                                    shutdown the instance.</span>
                            </v-col>
                        </v-row>

                        <v-row>
                            <v-col cols="4">
                                <v-select :items="alarmMetricItems" item-title="abbr" item-value="metric"
                                    :hint="`${alarmMetric.abbr}, ${alarmMetric.metric}`" dense label="Alarm Metric"
                                    single-line persistent-hint return-object v-model="alarmMetric"
                                    :rules="isRequiredOnlyRules">
                                </v-select>
                            </v-col>
                            <v-col cols="4">
                                <v-text-field dense label="Threshold"
                                    hint="Number of %CPU the instance has to be below to alarm" v-model="alarmThreshold"
                                    :rules="onlyNumbersRules"></v-text-field>
                            </v-col>
                            <v-col cols="4">
                                <v-text-field dense label="Evaluation Period"
                                    hint="Number of data points per minute to evaluate." v-model="alarmEvaluationPeriod"
                                    :rules="onlyNumbersRules"></v-text-field>
                            </v-col>
                        </v-row>


                        <v-row>
                            <v-col cols="12">
                                <span class="font-weight-light">The minecraft run command and the directorty it
                                    executes. Leave it blank if you want to do it manually</span>
                            </v-col>
                            <v-col cols="6">
                                <v-text-field dense v-model="workingDir" label="Working directory"></v-text-field>
                            </v-col>
                            <v-col cols="6">
                                <v-text-field dense v-model="runCommand" label="Run command"></v-text-field>
                            </v-col>

                        </v-row>
                        <v-btn v-if="!settingsDialogLoading" color="primary" text @click="onSubmit">
                            Save
                        </v-btn>

                        <v-btn text @click="resetForm"> Close </v-btn>
                    </v-container>
                </v-form>
            </v-expansion-panel-text>
        </v-expansion-panel>
        <v-expansion-panel>
            <v-expansion-panel-title>Users</v-expansion-panel-title>
            <v-expansion-panel-text>
                <v-container>
                    <v-row>
                        <v-col cols="8">
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
                        <v-col cols="8">
                            <v-form ref="addUserForm">
                                <v-text-field dense label="Email address" v-model="inviteeEmail" suffix="@gmail.com"
                                    :rules="alphaNumericRules"></v-text-field>
                            </v-form>
                        </v-col>
                    </v-row>
                    <v-btn color="primary" text @click="addUser()">
                        Add
                    </v-btn>
                </v-container>
            </v-expansion-panel-text>
        </v-expansion-panel>
    </v-expansion-panels>

    <v-snackbar v-model="snackbar" :timeout="snackTimeout" :color="snackColor" outlined left centered text>
        {{ snackText }}

        <template v-slot:actions>
            <v-btn color="white" variant="text" @click="snackbar = false">
                Close
            </v-btn>
        </template>
    </v-snackbar>


</template>