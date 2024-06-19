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

function copyPublicIp() {
  const ip = document.querySelector('#publicIp').value + ':25565';

  copyToClipboard(ip)
    .then(() => {
      snackbar.value = true
      snackText.value = "Server IP Address copied!"
      snackColor.value = "primary"
    })
    .catch(() => {
      snackbar.value = true
      snackText.value = "copy failed!"
      snackColor.value = "error"
    });
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
    snackText.value = rsp.body.msg;
    snackbar.value = true;
    snackColor.value = "primary"
  }
  else {
    snackText.value = rsp.body.err;
    snackbar.value = true;
    snackColor.value = "error"
  }
}

</script>

<template>
  <v-layout class="rounded rounded-md">
    <Header />
    <v-main class="d-flex justify-center">
      <v-snackbar v-model="snackbar" :timeout="snackTimeout" :color="snackColor" outlined left centered text>
        {{ snackText }}

        <template v-slot:actions>
          <v-btn color="white" variant="text" @click="snackbar = false">
            Close
          </v-btn>
        </template>
      </v-snackbar>

      <div v-if="serverStore.selectedServer.id != null">
        <v-card class="pa-6" max-width="600"  :title="serverName" :subtitle="serverStore.selectedServer.id">
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
            class="pb-5" 
            label="Public IP" 
            id="publicIp" 
            :hint="serverStore.selectedServer.state"
            persistent-hint
            v-model="serverStore.selectedServer.publicIp" readonly=true>

            <template v-slot:prepend-inner>
              <v-icon icon="mdi-power-standby" @click="powerButtonDialog = true" size="large" :color="serverStore.selectedServer.state === 'stopped'
        ? 'error'
        : serverStore.selectedServer.state === 'running'
          ? 'success'
          : 'warning'
        "></v-icon>
            </template>

            <template v-slot:append-inner>
              <v-icon size="large" icon="mdi-content-copy" @click="copyPublicIp"></v-icon>
            </template>

          </v-text-field>

          <ServerCharts />
          
          <ServerSettings />

          <span class="text-caption">Hours running: {{ (serverStore.selectedServer.runningMinutes / 60).toFixed(1)
            }}</span>


        </v-card>
        
      </div>
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