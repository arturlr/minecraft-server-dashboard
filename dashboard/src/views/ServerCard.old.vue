<template>
  <div>
    <v-card class="my-8 pa-2 rounded-lg elevation-3 border">
      <v-alert v-model="metricAlert" shaped prominent :type="metricAlertType" dismissible>
        {{ metricMsg }}
      </v-alert>
      <div class="server-header gradient-bg pa-4">
        <v-card-title class="text-h5 font-weight-medium">
          {{ serverName }} oi
          <v-chip class="ml-2" color="primary" small>
            <v-icon small left> mdi-clock-outline </v-icon>
            {{ (serversDict[serverId].runningMinutes / 60).toFixed(1) }} hours
          </v-chip>          
        </v-card-title>
        <!-- <v-card-actions class="pa-4">
            <v-btn color="primary" outlined rounded @click="processSettingsForm()">
              <v-icon left>settings</v-icon>
              Settings
            </v-btn>
            <v-btn color="secondary" outlined rounded @click="addUserDialog = true">
              <v-icon left>person_add</v-icon>
              Add User
            </v-btn>
          </v-card-actions> -->
      </div>
      <v-card-subtitle class="text-caption">{{ serverId }} </v-card-subtitle>
      <v-alert v-if="!iamServerCompliant" dense type="error">
        <v-row align="center">
          <v-col class="grow">
            This server does not have the correct IAM role and permissions to execute.
          </v-col>
          <v-progress-circular v-if="fixButtonProgess" :width="3" color="black" indeterminate></v-progress-circular>
          <v-col class="shrink">
            <v-btn :disabled="fixButtonProgess"
              @click="triggerAction('config_iam', serverId, true); fixButtonProgess = true">Fix it</v-btn>
          </v-col>
        </v-row>
      </v-alert>
      

          <v-text-field id="publicIp" dense label="Public IP" :value="serversDict[serverId].publicIp"
            append-icon="content_copy" @click:append="copyPublicIp" :hint="serversDict[serverId].state" persistent-hint
            outlined readonly>
            <v-icon large @click="serverStateConfirmation = true" slot="prepend" v-bind:color="serversDict[serverId].state === 'stopped'
                ? 'error'
                : serversDict[serverId].state === 'running'
                  ? 'success'
                  : 'warning'
              ">
              mdi-power
            </v-icon>
          </v-text-field>
          <v-row class="chart-container">
            <v-col cols="12" md="4">
              <v-card class="chart-card pa-3 rounded-lg">
                <div class="chart-title text-subtitle-1 mb-2">Users Activity</div>
                <apexchart ref="users" height="120" :options="getEnhancedAreaChartOptions" :series="chartInit" />
              </v-card>
            </v-col>
            <v-col cols="12" md="8">
              <v-card class="chart-card pa-3 rounded-lg">
                <div class="chart-title text-subtitle-1 mb-2">Performance Metrics</div>
                <apexchart ref="lineChart" height="180" :options="getEnhancedLineChartOptions" :series="chartInit" />
              </v-card>
            </v-col>
          </v-row>

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



    <v-snackbar v-model="successAlert" timeout="3500" absolute color="success" outlined left centered text>
      <strong>{{ infoMsg }}</strong>
    </v-snackbar>

    <v-snackbar v-model="errorAlert" timeout="3500" absolute color="red accent-2" outlined left centered text>
      <strong>{{ errorMsg }}</strong>
    </v-snackbar>

    <v-snackbar v-model="copyDialog" timeout="3500" absolute left centered color="primary" text>
      <strong>Copied!</strong>
    </v-snackbar>
  </div>
</template>

<style scoped>
.gradient-bg {
  background: linear-gradient(135deg, var(--v-primary-base) 0%, var(--v-secondary-base) 100%);
  color: white;
}

.metric-card {
  transition: all 0.3s ease;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 16px;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.chart-card {
  background: #ffffff;
  border: 1px solid #eee;
}

.status-chip {
  position: absolute;
  top: 16px;
  right: 16px;
}
</style>


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

    serverName() {
      return this.serversDict[this.serverId]?.name || 'Unknown Server';
    },

    iamServerCompliant() {
      return this.serversDict[this.serverId]?.iamCompliant || false;
    },

    chartInit() {
      return [];
    },

    getEnhancedAreaChartOptions() {
      return {
        chart: { type: 'area' },
        xaxis: { categories: [] }
      };
    },

    getEnhancedLineChartOptions() {
      return {
        chart: { type: 'line' },
        xaxis: { categories: [] }
      };
    },

    isMobile() {
      return this.$vuetify.breakpoint.xsOnly;
    },
  },
  methods: {
    async processSettingsForm(submit = false) {
      this.settingsDialog = true;
      this.settingsDialogLoading = true;

      if (submit) {
        let params = { am: this.alarmMetric, at: this.alarmThreshold }
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
          if ("runCommand" in infoResp) {
            this.runCommand = infoResp.runCommand;
          }
          if ("workingDir" in infoResp) {
            this.workingDir = infoResp.workingDir;
          }
          if ("alarmMetric" in infoResp) {
            this.alarmMetric = infoResp.alarmMetric;
          }
          if ("alarmThreshold" in infoResp) {
            this.alarmThreshold = infoResp.alarmThreshold;
          }
        }
      }

      this.settingsDialogLoading = false;
    },

    copyPublicIp() {
      const publicIp = this.serversDict[this.serverId]?.publicIp;
      if (publicIp) {
        navigator.clipboard.writeText(publicIp);
        this.copyDialog = true;
      }
    },

    async triggerAction(action, params, returnResponse = false) {
      try {
        const response = await API.graphql({
          query: triggerServerAction,
          variables: {
            serverId: this.serverId,
            action: action,
            params: JSON.stringify(params)
          }
        });

        if (returnResponse) {
          return JSON.parse(response.data.triggerServerAction);
        }

        this.successAlert = true;
        this.infoMsg = 'Action completed successfully';
      } catch (error) {
        this.errorAlert = true;
        this.errorMsg = error.message || 'An error occurred';
      }
    },

    subscribePutServerMetric() {
      // Subscription logic would go here
    },

    updateMetrics() {
      // Metrics update logic would go here
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
