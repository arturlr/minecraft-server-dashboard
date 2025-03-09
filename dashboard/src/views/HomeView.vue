<script setup>
import { reactive, ref, onMounted, computed } from "vue";
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

const serverName = computed(() => {
  if (
    serverStore.selectedServer.name &&
    serverStore.selectedServer.name.length > 2
  ) {
    return serverStore.selectedServer.name;
  } else {
    return serverStore.selectedServer.id;
  }
});

const formatRunningTime = computed((minutes) => {
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
  })


const iamServerCompliant = computed(() => {
  return serverStore.selectedServer.iamStatus === 'ok' ? true : false
});

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (err) {
    console.error('Failed to copy', err);
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
    variables: { instanceId: serverStore.selectedServer.id },
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

const getServerStateColor = computed(() => {
  switch(serverStore.selectedServer.state) {
    case 'running': return 'success'
    case 'stopped': return 'error'
    default: return 'warning'
  }
})

const getServerStateIcon = computed(() => {
  switch(serverStore.selectedServer.state) {
    case 'running': return 'mdi-server-network'
    case 'stopped': return 'mdi-server-off'
    default: return 'mdi-server-network-off'
  }
})


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

      <div v-if="serverStore.selectedServer.id != null">
         <!-- Server Card -->
         <v-row justify="center">
          <v-col cols="12" sm="10" md="8" lg="6">
            <v-card elevation="2" class="rounded-lg">

              <v-card-item>
                <v-row align="center">
                  <v-col>
                    <v-card-title class="text-h5 font-weight-bold">
                      {{ serverName }}
                      <v-chip
                        :color="serverStore.selectedServer.state === 'running' ? 'success' : 'error'"
                        size="small"
                        class="ml-2"
                        variant="elevated"
                      >
                        {{ serverStore.selectedServer.state }}
                      </v-chip>
                    </v-card-title>
                    <v-card-subtitle class="pt-2">
                      <v-icon icon="mdi-server" class="mr-1"></v-icon>
                      {{ serverStore.selectedServer.id }}
                    </v-card-subtitle>
                  </v-col>
                </v-row>
              </v-card-item>


          <v-alert v-if="!iamServerCompliant" closable dense type="error"> 
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
            v-model="serverStore.selectedServer.publicIp">

            <template v-slot:prepend-inner>
              <v-icon icon="mdi-power-standby" @click="powerButtonDialog = true" size="large" :color="getServerStateColor" />          
            </template>

            <template v-slot:append-inner>
              <v-icon size="large" icon="mdi-content-copy" @click="copyPublicIp"></v-icon>
            </template>

          </v-text-field>

          <ServerSettings /> 

          <ServerCharts /> 

          <span {{ formatRunningTime(serverStore.selectedServer.runningMinutes) }} />


        </v-card>
        

      </v-col>
      </v-row>
    </div>
    </v-container>
    </v-main>
  </v-layout>

  <v-dialog v-model="powerButtonDialog" max-width="300px">
    <v-card>
      <v-list-item two-line>
        <v-list-item-content>
          <v-list-item-title class="text-h6">
            {{ serverName }}
          </v-list-item-title>
          <v-list-item-subtitle>Confirm actions: </v-list-item-subtitle>
        </v-list-item-content>
      </v-list-item>
      <v-card-actions v-if="serverStore.selectedServer.iamStatus === 'ok'">
        <div v-if="serverStore.selectedServer.state === 'stopped'">
          <v-btn color="success" outlined small class="pa-2" @click="triggerAction('startServer')">
            Start
          </v-btn>
        </div>
        <div v-else>
          <v-btn color="warning" outlined small @click="triggerAction('stopServer')">
            Stop
          </v-btn>

          <span> &nbsp; </span>

          <v-btn color="warning" outlined small @click="triggerAction('restartServer')">
            ReStart
          </v-btn>
        </div>

        <v-spacer></v-spacer>

        <v-btn color="gray darken-1" outlined small @click="powerButtonDialog = false">
          Cancel
        </v-btn>
      </v-card-actions>
      <v-card-text v-else>
        You need to Fix the role to be able to perform any action!
      </v-card-text>
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