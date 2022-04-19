<template>
  <div>
    <v-alert type="info" v-model="successAlert" dismissible>
      {{ infoMsg }}
    </v-alert>
    <v-alert type="error" v-model="errorAlert" dismissible>
      {{ errorMsg }}
    </v-alert>
    <v-card class="my-8 pa-2">
      <v-list-item>
        <v-list-item-content>
          <v-list-item-title
            class="text-h4"
            v-if="
              serversDict[serverId].name &&
              serversDict[serverId].name.length > 2
            "
          >
            {{ serversDict[serverId].name }}
          </v-list-item-title>
          <v-list-item-title class="text-h4" v-else>
            {{ serverId }}
          </v-list-item-title>
          <v-list-item-subtitle
            class="text-caption"
            v-if="
              serversDict[serverId].name &&
              serversDict[serverId].name.length > 2
            "
            >{{ serverId }}
          </v-list-item-subtitle>
        </v-list-item-content>
      </v-list-item>

      <v-chip-group>
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
          v-bind="attrs"
          v-on="on"
          color="gray" 
          label 
          outlined>
          <v-icon left> schedule </v-icon>
          {{ (serversDict[serverId].runningMinutes/60).toFixed(1) }} hours
        </v-chip>
        </template>
        <span>Approximate number. Not for billing purpose</span>
        </v-tooltip>
      </v-chip-group>

      <v-divider class="mx-4" vertical></v-divider>

      <v-row>
        <v-col cols="4">
          <v-text-field
            id="publicIp"
            dense
            label="Public IP"
            :value="serversDict[serverId].publicIp"
            append-icon="content_copy"
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
        <v-col cols="8">
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

      <v-list>
        <v-list-item>
          <v-btn depressed x-small @click="settingsDialog = true">
            settings
          </v-btn>
        </v-list-item>
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

    <v-dialog v-model="settingsDialog" persistent max-width="600px">
      <v-card>
        <v-card-title>
          <span class="text-h6">Initialization Commands</span>
        </v-card-title>
        <v-card-text>
          <v-container>
            <v-row>
              <v-text-field
                dense
                :prepend-icon="isRunCommandEdit ? 'save' : 'edit'"
                @click:prepend="toggleEdit('runCommand')"
                v-model="runCommand"
                label="Minecraft run command"
                :readonly="isRunCommandEdit === false"
                @keyup.enter="doneEdit($event)"
                @keyup.esc="cancelEdit('runCommand')"
              ></v-text-field>
            </v-row>
            <v-row>
              <v-text-field
                dense
                :prepend-inner-icon="isWorkingDirEdit ? 'save' : 'edit'"
                v-model="serversDict[serverId].workingDir"
                label="Minecraft working directory"
                :readonly="isWorkingDirEdit === false"
              ></v-text-field>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions>
          <v-btn color="primary" text @click="settingsDialog = false">
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog
      v-model="serverStateConfirmation"
      hide-overlay
      persistent
      width="300"
    >
      <v-card color="gray" dark>
        <v-card-title>
          Please confirm action:
          <v-progress-linear color="white" class="mb-0"></v-progress-linear>
        </v-card-title>
        <v-card-actions>
          <v-spacer></v-spacer>
          <div v-if="serversDict[serverId].state == 'stopped'">
            <v-btn
              color="green darken-1"
              text
              @click="triggerServerState('start')"
            >
              Start
            </v-btn>
          </div>
          <div v-else>
            <v-btn
              color="orange darken-1"
              text
              @click="triggerServerState('stop')"
            >
              Stop
            </v-btn>
            <v-btn
              color="orange darken-1"
              text
              @click="triggerServerState('restart')"
            >
              ReStart
            </v-btn>
          </div>

          <v-btn
            color="gray darken-1"
            text
            @click="serverStateConfirmation = false"
          >
            Cancel
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="copyDialog" hide-overlay persistent width="300">
      <v-card color="primary" dark>
        <v-card-text>
          Copied IP Address to Clipboard
          <v-progress-linear color="white" class="mb-0"></v-progress-linear>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="green darken-1" text @click="copyDialog = false">
            Ok
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
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
      serverId: null,
      copyDialog: false,
      serverStateConfirmation: false,
      cpu: [],
      network: [],
      errorAlert: false,
      errorMsg: "",
      settingsDialog: false,
      runCommand: null,
      isRunCommandEdit: false,
      workingDir: null,
      isWorkingDirEdit: false,
      successAlert: false,
      infoMsg: null,
      cpuChart: [
        {
          data: [],
        },
      ],
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
        colors: ["#77B6EA", "#545454"],
        dataLabels: {
          enabled: false,
        },
        stroke: {
          curve: "smooth",
        },
        title: {
          text: "% CPU Utilization & Network Packages Out (10k)",
          align: "left",
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
  },
  methods: {
    toggleEdit(param) {
      if (param == "runCommand") {
        this.isRunCommandEdit = !this.isRunCommandEdit;
      }
    },
    doneEdit(param) {
      if (param == "runCommand") {
        this.isRunCommandEdit = !this.isRunCommandEdit;
      }
    },
    cancelEdit(param) {
      if (param == "runCommand") {
        this.isRunCommandEdit = !this.isRunCommandEdit;
        this.runCommand = this.serversDict[this.serverId].runCommand;
      }
    },
    async triggerServerState(state) {
      this.serverStateConfirmation = false;
      const input = {
        id: this.serverId,
        action: state,
      };
      const actionResult = await API.graphql({
        query: triggerServerAction,
        variables: { input: input },
      });

      const rsp = JSON.parse(actionResult.data.triggerServerAction);

      if (rsp.statusCode == 200) {
        this.infoMsg = "Server action: " + state + " successfully initiated.";
        this.successAlert = true;
      } else {
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
            name: "Network",
            data: this.serversDict[this.serverId].networkStats
              ? this.serversDict[this.serverId].networkStats
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
      serverIp.select();
      try {
        document.execCommand("copy");
      } catch (err) {
        console.error("Oops, unable to copy");
      }
      serverIp.setAttribute("type", "hidden");
      this.copyDialog = true;
    },
  },
};
</script>
