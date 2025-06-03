<script setup>
import { reactive, ref, onMounted, computed } from "vue";
import { useUserStore } from "../stores/user";
import { useServerStore } from "../stores/server";

const userStore = useUserStore();
const serverStore = useServerStore()

const copyDialog = ref(false)
const fixButtonProgess = ref(false)
const fixErrorAlert = ref(false)
const fixErrorMsg = ref("")
const fixSuccessAlert = ref(false)
const fixSuccessMsg = ref("")

const iamServerCompliant = computed(() => {
    return serverStore.selectedServer.iamStatus === 'ok' ? true : false
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

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (err) {
    console.error('Failed to copy', err);
  }
}

function showCopyDialog() {
    copyDialog.value = true;
}

function hideCopyDialog() {
  setTimeout(() => {
    copyDialog.value = false; 
  }, 2000);
}

function copyPublicIp() {
  const ip = document.querySelector('#publicIp').value + ':25565';

  showCopyDialog();
  
  copyToClipboard(ip)
    .then(() => {
      hideCopyDialog();
    })
    .catch(() => {
      hideCopyDialog();
    });
}

async function triggerAction(action, param, returnValue = false) {
  try {
    // Reset error state when starting a new action
    if (action === 'config_iam') {
      fixErrorAlert.value = false;
      fixErrorMsg.value = "";
    }

    let jsonParams = null;
    if (typeof param === "string" && param.startsWith('i-')) {
      jsonParams = JSON.parse('{ "instanceId":"' + param + '"}');
    } else {
      jsonParams = JSON.stringify(param);
    }

    const input = {
      instanceId: serverStore.selectedServer.id,
      action: action,
      params: jsonParams
    };

    const actionResult = await API.graphql({
      query: triggerServerAction,
      variables: { input: input },
    });

    const rsp = JSON.parse(actionResult.data.triggerServerAction);

    // Handle response for IAM configuration
    if (action === 'config_iam') {
      fixButtonProgess.value = false;
      if (rsp.statusCode === 200) {
        serverStore.selectedServer.iamStatus = 'ok';
        // Clear any previous error messages if fix was successful
        fixErrorAlert.value = false;
        fixErrorMsg.value = "";
        // Show success message
        fixSuccessAlert.value = true;
        fixSuccessMsg.value = rsp.body.msg || "Successfully fixed IAM role";
        // Auto-hide success message after 5 seconds
        setTimeout(() => {
          fixSuccessAlert.value = false;
        }, 5000);
      } else {
        // Display error message from backend
        fixErrorAlert.value = true;
        fixErrorMsg.value = rsp.body.details || rsp.body.err || "Failed to fix IAM role";
        console.error("IAM fix error:", rsp);
      }
    }

    // Handle response for start action
    if (action === 'start') {
      if (rsp.statusCode === 200) {
        serverStore.selectedServer.state = "starting";
      }
    }

    if (returnValue) {
      return rsp.statusCode === 200 ? rsp.body : null;
    }

    return rsp.statusCode === 200;
  } catch (error) {
    console.error("Error executing action:", error);
    if (action === 'config_iam') {
      fixButtonProgess.value = false;
      fixErrorAlert.value = true;
      fixErrorMsg.value = "An error occurred while processing your request";
    }
    return returnValue ? null : false;
  }
}
</script>

<template>
    <v-alert v-if="!iamServerCompliant" closable dense type="error">
        <v-row align="center">
            <v-col class="grow">
                This server does not have the correct IAM role and permissions to execute.
            </v-col>
            <v-progress-circular v-if="fixButtonProgess" :width="3" color="black" indeterminate></v-progress-circular>
            <v-col class="shrink">
                <v-btn :disabled="fixButtonProgess"
                    @click="triggerAction('config_iam', serverStore.selectedServer.id, true); fixButtonProgess = true">Fix it</v-btn>
            </v-col>
        </v-row>
    </v-alert>
    
    <!-- Success alert for IAM fix -->
    <v-alert v-if="fixSuccessAlert" closable dense type="success" class="mt-2">
        <v-row align="center">
            <v-col>
                {{ fixSuccessMsg }}
            </v-col>
        </v-row>
    </v-alert>
    
    <!-- Error alert for IAM fix -->
    <v-alert v-if="fixErrorAlert" closable dense type="warning" class="mt-2">
        <v-row align="center">
            <v-col>
                {{ fixErrorMsg }}
            </v-col>
        </v-row>
    </v-alert>
    
    <v-card class="my-8 pa-2">
        <v-card-text>
            <v-row>
                <v-chip-group column>
                    <v-chip variant="label">
                        <v-icon> mdi-chip </v-icon>
                        {{ serverStore.selectedServer.vCpus }} vCPU
                    </v-chip>

                    <v-chip variant="label">
                        <v-icon left> mdi-memory </v-icon>
                        {{ serverStore.selectedServer.memSize / 1024 }} GB
                    </v-chip>

                    <v-chip variant="label">
                        <v-icon left> mdi-disc </v-icon>
                        {{ serverStore.selectedServer.diskSize }} GB
                    </v-chip>

                    <v-chip variant="label">
                        <v-icon> mdi-clock-outline </v-icon>
                        {{ (serverStore.selectedServer.runningMinutes / 60).toFixed(1) }}
                        hours
                    </v-chip>

                </v-chip-group>
            </v-row>
            <v-row>
                <v-text-field
            label="Public IP"
            id="publicIp"
            :hint="serverStore.selectedServer.state "
            v-model="serverStore.selectedServer.publicIp"
            readonly=true
          >
          
          <template v-slot:prepend-inner>
            <v-icon icon="mdi-power-standby" @click="serverStateConfirmation = true" size="large" :color="serverStore.selectedServer.state === 'stopped'
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
            </v-row>

        </v-card-text>

    </v-card>

    <v-snackbar
      v-model="copyDialog"
      timeout="3500"
      absolute
      left
      centered
      color="orange"
      text
    >
      <strong>Copied!</strong>
    </v-snackbar>

</template>
