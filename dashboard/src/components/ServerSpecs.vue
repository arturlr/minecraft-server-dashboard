<script setup>
import { reactive, ref, onMounted, computed } from "vue";
import { useUserStore } from "../stores/user";
import { useServerStore } from "../stores/server";

const userStore = useUserStore();
const serverStore = useServerStore()

const copyDialog = ref(false)
const fixButtonProgess = ref(false)

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

async function triggerAction(
      action,
      param,
      returnValue = false
    ) {

      if (action == 'add_user') {
        this.$refs.addUserEmail.validate();
        if (this.$refs.addUserEmail.hasError) {
          this.errorAlert = true
          this.errorMsg = "Only provide your google username"
          return false
        }

      }
      this.serverStateConfirmation = false;
      this.addUserDialog = false;

      let jsonParams = null;
      if (typeof SignUpParams == "string" && param.startsWith('i-')){
        jsonParams = JSON.parse('{ "instanceId":"' + param + '"}')
      }
      else {
        jsonParams = JSON.stringify(param);
      }

      const input = {
        instanceId: this.serverId,
        action: action,
        params: jsonParams
      };
      const actionResult = await API.graphql({
        query: triggerServerAction,
        variables: { input: input },
      });

      const rsp = JSON.parse(actionResult.data.triggerServerAction);

      // resetting flags
      if (action == 'config_iam') {
        this.fixButtonProgess = false;
        if (rsp.statusCode == 200) {
          this.serversDict[this.serverId].iamStatus = 'ok'
        }
        else {
          console.log(rsp)
        }
      }

      if (action == 'start') {
        this.fixButtonProgess = false;
        if (rsp.statusCode == 200) {
          this.serversDict[this.serverId].state = "starting"
        }
      }

      if (rsp.statusCode == 200) {
        if (returnValue) {
          return rsp.body;
        }
        //this.infoMsg = "Server action: " + action + " done.";
        //this.successAlert = true;
      } else {
        if (returnValue) {
          return null;
        }
        this.errorMsg = rsp.body.err;
        this.errorAlert = true;
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