<template>
  <div>
    <v-card class="my-8 pa-2">
      <v-alert
      v-model="metricAlert"
      shaped
      prominent
      :type="metricAlertType"
      dismissible
    >
     {{ metricMsg }}
    </v-alert>
      <v-card-title class="text-h6">
        {{ serverName }}
      </v-card-title>
      <v-card-subtitle class="text-caption">{{ serverId }} </v-card-subtitle>
        <v-alert
        v-if="!iamServerCompliant"
        dense
        type="error"
      >
        <v-row align="center">
          <v-col class="grow">
            This server does not have the correct IAM role and permissions to execute.
          </v-col>
          <v-progress-circular            
            v-if="fixButtonProgess"
            :width="3"
            color="black"
            indeterminate            
          ></v-progress-circular>
          <v-col class="shrink">
            <v-btn
            :disabled="fixButtonProgess"
            @click="triggerAction('config_iam',serverId, true);fixButtonProgess=true"
            >Fix it</v-btn>
          </v-col>
        </v-row>
      </v-alert>
      <v-card-text>
        <v-row>
          <v-chip-group column>
            <!-- <v-chip 
            v-if="serversDict[serverId].initStatus === 'fail' && serversDict[serverId].state === 'running'"
            color="orange" label outlined>
            <v-icon left> hourglass_empty </v-icon>
              initializing...
            </v-chip> -->

            <v-chip color="gray" label outlined>
              <v-icon left> developer_board </v-icon>
              {{ serversDict[serverId].vCpus }} vCPU
            </v-chip>

            <v-chip color="gray" label outlined>
              <v-icon left> sd_card </v-icon>
              {{ serversDict[serverId].memSize / 1024 }} GB
            </v-chip>

            <v-chip color="gray" label outlined>
              <v-icon left> album </v-icon>
              {{ serversDict[serverId].diskSize }} GB
            </v-chip>

            <v-tooltip bottom>
              <template v-slot:activator="{ on, attrs }">
                <v-chip
                  v-if="!isMobile"
                  v-bind="attrs"
                  v-on="on"
                  color="gray"
                  label
                  outlined
                >
                  <v-icon left> schedule </v-icon>
                  {{ (serversDict[serverId].runningMinutes / 60).toFixed(1) }}
                  hours
                </v-chip>
              </template>
              <span>Approximate number. Not for billing purpose</span>
            </v-tooltip>
          </v-chip-group>
        </v-row>

        <v-row>
          <v-col md="auto" class="d-flex flex-column">
            <v-text-field
              id="publicIp"
              dense
              label="Public IP"
              :value="serversDict[serverId].publicIp"
              append-icon="content_copy"
              @click:append="copyPublicIp"
              :hint="serversDict[serverId].state"
              persistent-hint
              outlined
              readonly
            >
              <v-icon
                large
                @click="serverStateConfirmation = true"
                slot="prepend"
                v-bind:color="
                  serversDict[serverId].state === 'stopped'
                    ? 'error'
                    : serversDict[serverId].state === 'running'
                    ? 'success'
                    : 'warning'
                "
              >
                mdi-power
              </v-icon>
            </v-text-field>
            <v-card>
              <apexchart
                ref="users"
                height="90"
                :options="areaChartOptions"
                :series="chartInit"
              ></apexchart>
            </v-card>
          </v-col>
          <!-- <div v-if="isMobile">
            <v-card>
              <apexchart
                ref="lineChart"
                height="150"
                :options="lineChartOptions"
                :series="chartInit"
              ></apexchart>
            </v-card>
          </div> 
          <v-col v-else class="d-flex flex-column"> -->
          <v-col>
            <v-card>
              <apexchart
                ref="lineChart"
                height="150"
                :options="lineChartOptions"
                :series="chartInit"
              ></apexchart>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>

      <v-card-actions>
        <v-tooltip bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-btn text v-bind="attrs" v-on="on" @click="processSettingsForm()">
              <v-icon> settings </v-icon>
            </v-btn>
          </template>
          <span> Configure Minecraft Server initialization command</span>
        </v-tooltip>
        <v-tooltip bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-btn
              text
              v-bind="attrs"
              v-on="on"
              @click="
                addUserDialog = true;
                addUserEmail = null;
              "
            >
              <v-icon> person_add </v-icon>
            </v-btn>
          </template>
          <span> Add user to Start/Stop Server</span>
        </v-tooltip>
      </v-card-actions>

      <v-list>
        <v-list-item two-line>
          <v-list-item-content>
            <v-list-item-title class="font-weight-light">
              Last event date:
            </v-list-item-title>
            <v-list-item-subtitle class="font-weight-light">
              {{ serversDict[serverId].launchTime }}
            </v-list-item-subtitle>
          </v-list-item-content>
        </v-list-item>
      </v-list>
    </v-card>

    <v-dialog v-model="addUserDialog" max-width="300px">
      <v-card>
        <v-card-title> Add user to start/stop </v-card-title>
        <v-card-subtitle>
          <strong>{{ serverName }}</strong>
        </v-card-subtitle>
        <v-card-text>
          <v-row>
            <v-text-field
              dense
              label="Email address"
              v-model="addUserEmail"
              suffix="@gmail.com"
              ref="addUserEmail"
              :rules="[rules.alphanumeric]"
            ></v-text-field>
          </v-row>
          <v-row>
            <v-list two-line>
              <v-list-header>Current Members</v-list-header>
              <v-list-item v-for="user in groupMembers" :key="user.id">
                <v-list-item-content>
                  <v-list-item-title v-text="user.fullname"></v-list-item-title>
                  <v-list-item-subtitle
                    v-text="user.email"
                  ></v-list-item-subtitle>
                </v-list-item-content>
              </v-list-item>
            </v-list>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-btn
            color="primary"
            text
            @click="triggerAction('add_user', {'email': addUserEmail} )"
          >
            Add
          </v-btn>
          <v-btn color="warning" text @click="addUserDialog = false">
            Cancel
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="settingsDialog" max-width="600px">
      <v-card ref="settingsForm">
        <v-progress-linear
          v-if="settingsDialogLoading"
          indeterminate
          height="5"
          value="5"
          color="teal"
        ></v-progress-linear>
        <v-card-title> Settings </v-card-title>
        <v-card-subtitle>
          <strong>{{ serverName }}</strong>
        </v-card-subtitle>
        <v-card-text>
          <v-container>
            <v-row>
              <v-col cols="12" sm="6">
                <v-select
                  :items="['Connections','CPUUtilization','MbpsOut']"
                  label="Metric"
                  :rules="[rules.required]"
                  dense
                  v-model="alarmMetric"
                  ref="alarmMetric"
                ></v-select>
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field
                  dense
                  label="Instance idle threshold."
                  hint="Connections, %CPU or Mbps"
                  :rules="[rules.required, rules.onlyNumbers]"
                  maxlength="6"
                  v-model="alarmThreshold"
                  ref="alarmThreshold"
                ></v-text-field>
              </v-col>

              <v-col cols="12">
                <v-text-field
                  dense
                  v-model="runCommand"
                  ref="runCommand"
                  label="Minecraft run command"
                ></v-text-field>
              </v-col>
              <v-col cols="12">
                <v-text-field
                  dense
                  v-model="workingDir"
                  ref="workingDir"
                  label="Minecraft working directory"
                ></v-text-field>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions>
          <v-btn
            v-if="!settingsDialogLoading"
            color="primary"
            text
            @click="submit"
          >
            Save
          </v-btn>
          <v-slide-x-reverse-transition>
            <v-tooltip v-if="settingsFormHasErrors" right>
              <template v-slot:activator="{ on, attrs }">
                <v-btn
                  icon
                  class="my-0"
                  v-bind="attrs"
                  @click="resetForm"
                  v-on="on"
                >
                  <v-icon>mdi-refresh</v-icon>
                </v-btn>
              </template>
              <span>Refresh form</span>
            </v-tooltip>
          </v-slide-x-reverse-transition>
          <v-spacer></v-spacer>
          <v-btn text @click="settingsDialog = false"> Close </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="serverStateConfirmation" max-width="300px">
      <v-card>
        <v-list-item two-line>
          <v-list-item-content>
            <v-list-item-title class="text-h6">
              {{ serverName }}
            </v-list-item-title>
            <v-list-item-subtitle>Confirm actions: </v-list-item-subtitle>
          </v-list-item-content>
        </v-list-item>
        <v-card-actions
        v-if="serversDict[serverId].iamStatus === 'ok'"
        >
          <div v-if="serversDict[serverId].state === 'stopped'">
            <v-btn
              color="success"
              outlined
              small
              class="pa-2"
              @click="triggerAction('start',serverId, true)"
            >
              Start
            </v-btn>
          </div>
          <div v-else>
            <v-btn
              color="warning"
              outlined
              small
              @click="triggerAction('stop',serverId, true)"
            >
              Stop
            </v-btn>

            <span> &nbsp; </span>

            <v-btn
              color="warning"
              outlined
              small
              @click="triggerAction('restart',serverId, true)"
            >
              ReStart
            </v-btn>
          </div>

          <v-spacer></v-spacer>

          <v-btn
            color="gray darken-1"
            outlined
            small
            @click="serverStateConfirmation = false"
          >
            Cancel
          </v-btn>
        </v-card-actions>
        <v-card-text
        v-else
        >
        You need to Fix the role to be able to perform any action!
        </v-card-text>
      </v-card>
    </v-dialog>

    <v-snackbar
      v-model="successAlert"
      timeout="3500"
      absolute
      color="success"
      outlined
      left
      centered
      text
    >
      <strong>{{ infoMsg }}</strong>
    </v-snackbar>

    <v-snackbar
      v-model="errorAlert"
      timeout="3500"
      absolute
      color="red accent-2"
      outlined
      left
      centered
      text
    >
      <strong>{{ errorMsg }}</strong>
    </v-snackbar>

    <v-snackbar
      v-model="copyDialog"
      timeout="3500"
      absolute
      left
      centered
      color="primary"
      text
    >
      <strong>Copied!</strong>
    </v-snackbar>
  </div>
</template>

<script>
import VueApexCharts from "vue-apexcharts";
import { API } from "aws-amplify";
import { mapState } from "vuex";
import moment from "moment";
import { onPutServerMetric } from "../graphql/subscriptions";
import { triggerServerAction } from "../graphql/mutations";

export default {
  name: "ServerCard",
  components: {
    apexchart: VueApexCharts,
  },
  data() {
    return {
      rules: {
        required: (value) => !!value || "Required.",
        minLen: value => (value && value.length >= 3) || 'Must be greater than 3 characters',
        maxLen: value => (value && value.length <= 250) || 'Must be less than 250 characters',
        alphanumeric: (value) => {
          const alphaPattern = /^[a-zA-Z0-9_.-]*$/;
          return alphaPattern.test(value) || "Only alphanumeric or dot, underscore and dash are allowed.";
        },
        onlyNumbers: (value) => {
          const pattern = /^[0-9]*$/;
          return pattern.test(value) || "Threshold must be only numbers.";
        },
      },
      serverId: null,
      copyDialog: false,
      serverStateConfirmation: false,
      cpu: [],
      network: [],
      errorAlert: false,
      errorMsg: "",
      metricAlert: false,
      metricAlertType: 'info',
      metricMsg: null,
      settingsDialog: false,
      settingsDialogLoading: false,
      runCommand: null,
      workingDir: null,
      successAlert: false,
      infoMsg: null,
      addUserEmail: null,
      addUserDialog: false,
      fixButtonProgess: false,
      alarmMetric: null,
      alarmThreshold: 25,
      settingsFormHasErrors: false,
    }
  },
  created() {
    if (this.$route.params) {
      this.serverId = this.$route.params.id;
      this.runCommand = this.serversDict[this.serverId].runCommand;
      this.workingDir = this.serversDict[this.serverId].workingDir;      
    }
  },
  mounted() {
    this.subscribePutServerMetric();
  },
  watch: {
    $route(to) {
      this.serverId = to.params.id;
      this.updateMetrics();
    },
  },
  computed: {
    ...mapState({
      serversDict: (state) => state.general.serversDict,
    }),
    
    isMobile() {
      return this.$vuetify.breakpoint.xsOnly;
    },
  },
  methods: {
    async processSettingsForm(submit = false) {
      this.settingsDialog = true;
      this.settingsDialogLoading = true;
      
      if (submit) {
        let params = { am:this.alarmMetric,at:this.alarmThreshold }
        if (this.runCommand.length > 3) {
          params.rc = this.runCommand
        }
        if (this.workingDir.length > 3) {
          params.wd = this.workingDir
        }

        await this.triggerAction("set_instance_attr", params)        
        this.settingsDialog = false;
      } else {
        // Default values
        this.runCommand = "";
        this.workingDir = "";
        this.alarmMetric = "CPUUtilization";
        this.alarmThreshold = "10";

        const infoResp = await this.triggerAction("get_instance_attr", this.serverId, true);

        if (infoResp) {
          if ("runCommand" in infoResp){
            this.runCommand = infoResp.runCommand;
          }
          if ("workingDir" in infoResp){
            this.workingDir = infoResp.workingDir;
          }
          if ("alarmMetric" in infoResp){
            this.alarmMetric = infoResp.alarmMetric;
          }
          if ("alarmThreshold" in infoResp){
            this.alarmThreshold = infoResp.alarmThreshold;
          }
        }        
      }

      this.settingsDialogLoading = false;
    },
    resetForm() {
      this.settingsFormHasErrors = false;

      this.$refs.alarmMetric.reset();
      this.$refs.alarmThreshold.reset();
      this.$refs.runCommand.reset();
      this.$refs.workingDir.reset();
    },
    async submit() {
      this.settingsFormHasErrors = false;

      this.$refs.alarmMetric.validate();
      this.$refs.alarmThreshold.validate();
      this.$refs.runCommand.validate();
      this.$refs.workingDir.validate();
      if (
        this.$refs.alarmMetric.hasError ||
        this.$refs.alarmThreshold.hasError ||
        this.$refs.runCommand.hasError ||
        this.$refs.workingDir.hasError
      ) {
        this.settingsFormHasErrors = true;
        console.error(this.$refs.workingDir.hasError)
        return false;
      }

      this.processSettingsForm(true);
    },
    
    
    async writeLog(msg) {
      // Calculating expiration time
      const d = new Date();
      d.setDate(d.getDate() + 60);
      const expirationEpoch = Math.round(d.getTime() / 1000);

      await this.$store.dispatch("profile/saveAuditLogin", {
        email: this.email,
        action: msg,
        expirationEpoch: expirationEpoch,
      });
    },
    
  },
};
</script>
