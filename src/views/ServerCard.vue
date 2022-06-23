<template>
  <div>
    <v-card class="my-8 pa-2">
      <v-card-title class="text-h6">
        {{ serverName }}
      </v-card-title>
      <v-card-subtitle class="text-caption">{{ serverId }} </v-card-subtitle>
      <v-card-text>
        <v-row>
          <v-chip-group column>
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
          <div v-if="isMobile">
            <v-card>
              <apexchart
                ref="lineChart"
                height="150"
                :options="lineChartOptions"
                :series="chartInit"
              ></apexchart>
            </v-card>
          </div>
          <v-col v-else class="d-flex flex-column">
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
            @click="triggerAction('adduser', {'email': addUserEmail} )"
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
                  :items="['Connections','CPUUtilization','NetworkOut']"
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
                  hint="Connections, %CPU or NetworkOut bytes"
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
                  :rules="[rules.required]"
                ></v-text-field>
              </v-col>
              <v-col cols="12">
                <v-text-field
                  dense
                  v-model="workingDir"
                  ref="workingDir"
                  label="Minecraft working directory"
                  :rules="[rules.required]"
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
        <v-card-actions>
          <div v-if="serversDict[serverId].state == 'stopped'">
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
//import awsconfig from "../aws-exports";
//import { Signer } from "@aws-amplify/core";
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
        onlyNumbers: (value) => {
          const pattern = /^[0-9]*$/;
          return pattern.test(value) || "Threshold must be only 2 numbers.";
        },
      },
      serverId: null,
      copyDialog: false,
      serverStateConfirmation: false,
      cpu: [],
      network: [],
      errorAlert: false,
      errorMsg: "",
      settingsDialog: false,
      settingsDialogLoading: false,
      runCommand: null,
      workingDir: null,
      successAlert: false,
      infoMsg: null,
      addUserEmail: null,
      addUserDialog: false,
      alarmMetric: null,
      alarmThreshold: 25,
      settingsFormHasErrors: false,
      chartInit: [
        {
          data: [],
        },
      ],
      lineChartOptions: {
        chart: {
          type: "line",
          toolbar: {
            show: false,
          },
        },
        colors: ["#154360", "#5DADE2", "#D35400"],
        dataLabels: {
          enabled: false,
        },
        stroke: {
          curve: "smooth",
        },
        grid: {
          borderColor: "#e7e7e7",
          row: {
            colors: ["#f3f3f3", "transparent"], // takes an array which will be repeated on columns
            opacity: 0.5,
          },
        },
        markers: {
          size: 0,
        },
        xaxis: {
          type: "datetime",
          labels: {
            formatter: function (val, timestamp) {
              return moment(new Date(timestamp)).format("HH:mm");
            },
          },
        },
      },
      areaChartOptions: {
        chart: {
          type: "area",
          sparkline: {
            enabled: true,
          },
        },
        title: {
          text: "Users connected",
          align: "left",
        },
        stroke: {
          curve: "straight",
        },
        fill: {
          opacity: 0.3,
        },
        yaxis: {
          min: 0,
        },
        colors: ["#DCE6EC"],
      },
    };
  },
  created() {
    if (this.$route.params) {
      this.serverId = this.$route.params.id;
      this.runCommand = this.serversDict[this.serverId].runCommand;
      this.workingDir = this.serversDict[this.serverId].workingDir;
      this.subscribePutServerMetric();
    }
  },
  watch: {
    $route(to) {
      this.serverId = to.params.id;
      this.updateCharts();
    },
  },
  computed: {
    ...mapState({
      serversDict: (state) => state.general.serversDict,
    }),
    groupMembers() {
      if (
        this.serversDict[this.serverId].groupMembers &&
        this.serversDict[this.serverId].groupMembers.length > 0
      ) {
        return JSON.parse(this.serversDict[this.serverId].groupMembers);
      } else {
        return [];
      }
    },
    serverName() {
      if (
        this.serversDict[this.serverId].name &&
        this.serversDict[this.serverId].name.length > 2
      ) {
        return this.serversDict[this.serverId].name;
      } else {
        return this.serverId;
      }
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
        await this.triggerAction("setintanceinfo", {rc:this.runCommand,wd:this.workingDir,am:this.alarmMetric,at:this.alarmThreshold,instanceId:this.serverId})        
        this.settingsDialog = false;
      } else {
        // Default values
        this.runCommand = "";
        this.workingDir = "";
        this.alarmMetric = "";
        this.alarmThreshold = "";

        const resp = await this.triggerAction("getintanceinfo", this.serverId);
        console.log(resp)
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
        return false;
      }

      this.processSettingsForm(true);
    },
    async triggerAction(
      action,
      param,
      returnValue = false
    ) {
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
      console.log(rsp)

      if (rsp.statusCode == 200) {
        if (returnValue) {
          return rsp.body;
        }
        this.infoMsg = "Server action: " + action + " done.";
        this.successAlert = true;
      } else {
        if (returnValue) {
          return null;
        }
        this.errorMsg = rsp.body.err;
        this.errorAlert = true;
      }
    },
    updateCharts() {
      this.$nextTick(() => {
        this.$refs.lineChart.updateSeries([
          {
            name: "CPU",
            data: this.serversDict[this.serverId].cpuStats
              ? this.serversDict[this.serverId].cpuStats
              : [],
          },
          {
            name: "NetworkOut 100K",
            data: this.serversDict[this.serverId].networkStats
              ? this.serversDict[this.serverId].networkStats
              : [],
          },
          {
            name: "Memory",
            data: this.serversDict[this.serverId].memStats
              ? this.serversDict[this.serverId].memStats
              : [],
          },
        ]);

        this.$refs.users.updateSeries([
          {
            name: "Connections",
            data: this.serversDict[this.serverId].activeUsers
              ? this.serversDict[this.serverId].activeUsers
              : [],
          },
        ]);
      });
    },
    subscribePutServerMetric() {
      API.graphql({
        query: onPutServerMetric,
        variables: {},
      }).subscribe({
        next: (eventData) => {
          this.$store.dispatch("general/addServerStats", {
            metric: eventData.value.data.onPutServerMetric,
          });
          this.updateCharts();
        },
      });
    },
    classColor(sState) {
      if (sState === "running" || sState === "ok") {
        return "green";
      } else if (sState === "stopped" || sState === "fail") {
        return "red";
      } else {
        return "orange";
      }
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
    copyPublicIp() {
      let serverIp = document.querySelector("#publicIp");
      serverIp.setAttribute("type", "text");
      serverIp.value = serverIp.value + ":25565";
      serverIp.select();
      try {
        document.execCommand("copy");
      } catch (err) {
        console.error("Oops, unable to copy");
      }
      serverIp.setAttribute("type", "hidden");
      this.copyDialog = true;
      setTimeout(() => {
        this.copyDialog = false;
      }, 2000);
    },
  },
};
</script>
