<script setup>
import { reactive, ref, watch, computed } from "vue";
import Header from "../components/Header.vue";
import ServerCharts from "../components/ServerCharts.vue";
import ServerSettings from "../components/ServerSettings.vue";
import { generateClient } from 'aws-amplify/api';
import { useUserStore } from "../stores/user";
import { useServerStore } from "../stores/server";
import * as mutations from "../graphql/mutations";
import * as queries from "../graphql/queries";

const loading = ref(false)
const copying = ref(false)

const userStore = useUserStore();
const serverStore = useServerStore()

const settingsDialog = ref(false)
const addUserDialog = ref(false)

const graphQlClient = generateClient();

const copyDialog = ref(false)
const fixButtonProgess = ref(false)
const powerButtonDialog = ref(false)
const snackbar = ref(false)
const snackText = ref(null)
const snackColor = ref(null)
const snackTimeout = ref(3500)

const selectedServer = computed(() => serverStore.getServerById(serverStore.selectedServerId))

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (err) {
    console.error('Failed to copy', err);
  }
}

function formatRunningTime(minutes) {
    const hours = minutes / 60;
    if (hours < 1) {
      return `${Math.round(minutes)} minutes`;
    } else if (hours < 24) {
      return `${hours.toFixed(1)} hours`;
    } else {
      const days = Math.floor(hours / 24);
      const remainingHours = (hours % 24).toFixed(1);
      return `${days}d ${remainingHours}h`;
    }
  }

async function copyPublicIp() {
  copying.value = true
  try {
    await copyToClipboard(document.querySelector('#publicIp').value + ':25565')
    snackbar.value = true
    snackText.value = "Server IP Address copied!"
    snackColor.value = "success"
  } catch (err) {
    snackbar.value = true
    snackText.value = "Copy failed!"
    snackColor.value = "error"
  } finally {
    copying.value = false
  }
}

async function triggerAction(action) {

  const actionResult = await graphQlClient.graphql({
    query: mutations[action],
    variables: { instanceId: serverStore.selectedServerId },
  });

  const rsp = JSON.parse(actionResult.data[action]);

  if (action == "fixServerRole") {
    fixButtonProgess.value = false;
  }
  else {
    powerButtonDialog.value = false;
  }

  if (rsp.statusCode == 200) {
    snackText.value = rsp.body;
    snackbar.value = true;
    snackColor.value = "primary"
  }
  else {
    snackText.value = rsp.body;
    snackbar.value = true;
    snackColor.value = "error"
  }
}





</script>

<template>
  <v-layout class="rounded rounded-md">
    <Header />
    <v-main>
      <v-container fluid class="pa-4">
      <v-snackbar v-model="snackbar" :timeout="snackTimeout" :color="snackColor" outlined left centered text>
        {{ snackText }}

        <template v-slot:actions>
          <v-btn color="white" variant="text" @click="snackbar = false">
            Close
          </v-btn>
        </template>
      </v-snackbar>

      <div v-if="selectedServer">
         <!-- Server Card -->
         <v-row justify="center">
          <v-col cols="12" sm="10" md="8" lg="6">
            <v-card elevation="2" class="rounded-lg">

              <v-card-item>
                <v-row align="center">
                  <v-col>
                    <v-card-title class="text-h5 font-weight-bold">
                      {{ serverStore.getServerName }}
                      <v-chip
                        :color="selectedServer.state === 'running' ? 'success' : 'error'"
                        size="small"
                        class="ml-2"
                        variant="elevated"
                      >
                        {{ selectedServer.state }}
                      </v-chip>

                      <!-- <span v-if="selectedServer.runningMinutes">
                        <v-chip
                          size="small"
                          class="ml-2"
                          color='black'
                          variant="outlined"
                          :prepend-icon="selectedServer.runningMinutes ? 'mdi-clock-outline' : 'mdi-clock-off-outline'"
                        >
                          {{ formatRunningTime(selectedServer.runningMinutes) }}
                        </v-chip>
                      </span> -->

                    </v-card-title>
                    <v-card-subtitle class="pt-2">
                      <v-icon icon="mdi-server" class="mr-1"></v-icon>
                      {{ selectedServer.id }}
                    </v-card-subtitle>
                  </v-col>
                </v-row>
              </v-card-item>


          <v-alert v-if="!serverStore.isServerIamCompliant" closable dense type="error"> 
            <v-row align="center">
              <v-col class="grow">
                This server does not have the correct IAM role and permissions to execute.
              </v-col>
              <v-progress-circular v-if="fixButtonProgess" :width="3" color="black" indeterminate></v-progress-circular>
              <v-col class="shrink">
                <v-btn :disabled="fixButtonProgess" @click="triggerAction('fixServerRole'); fixButtonProgess = true">Fix
                  it</v-btn>
              </v-col>
            </v-row>
          </v-alert>
          
          <v-text-field 
            readonly
            label="Server Address"
            class="mt-4"
            variant="outlined"
            hide-details
            v-model="selectedServer.publicIp">

            <template v-slot:prepend-inner>
              <v-icon icon="mdi-power-standby" @click="powerButtonDialog = true" size="large" :color="serverStore.getServerStateColor" />          
            </template>

            <template v-slot:append-inner>
              <v-icon size="large" icon="mdi-content-copy" @click="copyPublicIp"></v-icon>
            </template>

          </v-text-field>

          <ServerSettings /> 

          <ServerCharts /> 

        </v-card>
        

      </v-col>
      </v-row>
    </div>
    </v-container>
    </v-main>
  </v-layout>

  <v-dialog v-model="powerButtonDialog" max-width="400px" transition="dialog-bottom-transition">
  <v-card class="rounded-lg">
    <v-card-item class="bg-primary pa-4">
      <template v-slot:prepend>
        <v-icon size="large" color="white" class="mr-2">mdi-server</v-icon>
      </template>
      <v-card-title class="text-h5 text-white font-weight-medium pa-0">
        {{ serverStore.getServerName }}
      </v-card-title>
    </v-card-item>

    <v-card-text class="pt-4">
      <v-alert
        v-if="selectedServer.iamStatus !== 'ok'"
        type="error"
        variant="tonal"
        density="comfortable"
      >
        <template v-slot:prepend>
          <v-icon icon="mdi-alert-circle"></v-icon>
        </template>
        You need to fix the IAM role to perform any actions!
      </v-alert>

      <div v-else>
        <div v-if="selectedServer.state === 'stopped'" class="d-flex gap-2">
          <v-btn
     
          density="compact"
            color="success"
            text-transform="none"
            @click="triggerAction('startServer')"
            prepend-icon="mdi-power"
          >
            Start
          </v-btn>
        </div>
        <div v-else class="d-flex gap-2">
          <v-btn
   
          density="compact"
            color="warning"
            text-transform="none"
            @click="triggerAction('stopServer')"
            prepend-icon="mdi-power-off"
          >
            Stop
          </v-btn>
          <v-btn
          density="compact"
            color="info"
            text-transform="none"
            @click="triggerAction('restartServer')"
            prepend-icon="mdi-restart"
          >
            Restart
          </v-btn>
        </div>
      </div>
    </v-card-text>

    <v-divider></v-divider>

    <v-card-actions class="pa-4">
      <v-spacer></v-spacer>
      <v-btn
        color="grey-darken-1"
        variant="text"
        @click="powerButtonDialog = false"
        prepend-icon="mdi-close"
      >
        Cancel
      </v-btn>
    </v-card-actions>
  </v-card>
</v-dialog>


</template>

<style scoped>
.time-chip {
  background-color: #f5f5f5 !important;
  color: #757575 !important;
  font-size: 0.875rem;
}

.custom-icon {
  color: #9e9e9e;
}
</style>