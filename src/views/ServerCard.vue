<template>
  <div>
    <v-alert type="info" v-model="successAlert" dismissible>
      {{ infoMsg }}
    </v-alert>
    <v-alert type="error" v-model="errorAlert" dismissible>
      {{ errorMsg }}
    </v-alert>
    <v-card class="my-8 pa-2">
      <v-card-title class="text-h6">
        {{ serverName }}
      </v-card-title>
      <v-card-subtitle class="text-caption">{{ serverId }} </v-card-subtitle>
  
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
              <v-chip v-bind="attrs" v-on="on" color="gray" label outlined>
                <v-icon left> schedule </v-icon>
                {{ (serversDict[serverId].runningMinutes / 60).toFixed(1) }}
                hours
              </v-chip>
            </template>
            <span>Approximate number. Not for billing purpose</span>
          </v-tooltip>
        </v-chip-group>

        <v-divider class="mx-4" vertical></v-divider>

        <v-row>
          <v-col md="auto" class="d-flex flex-column">
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
          <v-col class="d-flex flex-column">
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

        <v-card-actions>
          <v-tooltip bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-btn text v-bind="attrs" v-on="on" @click="settingsDialog = true">
              <v-icon> settings </v-icon>
            </v-btn>
          </template>
          <span> Configure Minecraft Server initialization command</span>
        </v-tooltip>
          <v-tooltip bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-btn text v-bind="attrs" v-on="on" @click="addUserDialog = true;addUserEmail = null">
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
                <v-header>Current Members</v-header>
                 <v-list-item
                    v-for="user in groupMembers"
                    :key="user.id"
                  >
                <v-list-item-content>
                  <v-list-item-title v-text="user.fullname"></v-list-item-title>
                  <v-list-item-subtitle v-text="user.email"></v-list-item-subtitle>
                </v-list-item-content>
                 </v-list-item>
              </v-list>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-btn color="primary" text @click="triggerAction('adduser','email',addUserEmail)"> Add </v-btn>
          <v-btn color="warning" text @click="addUserDialog = false">
            Cancel
          </v-btn>          
        </v-card-actions>        
      </v-card>
    </v-dialog>

    <v-dialog v-model="settingsDialog" max-width="600px">
      <v-card>
        <v-card-title> Initialization Commands </v-card-title>
        <v-card-subtitle>
          <strong>{{ serverName }}</strong>
        </v-card-subtitle>
        <v-card-text>
          <v-container>
            <v-row>
              <v-text-field
                dense
                :prepend-icon="isRunCommandEdit ? 'save' : 'edit'"                
                v-model="runCommand"
                label="Minecraft run command"
                :readonly="isRunCommandEdit === false"
                @click:prepend="actionField('edit','runCommand')"
                @keyup.enter="actionField('save','runCommand')"
                @keyup.esc="actionField('cancel','runCommand')"
              ></v-text-field>
            </v-row>
            <v-row>
              <v-text-field
                dense
                :prepend-icon="isWorkingDirEdit ? 'save' : 'edit'" 
                v-model="workingDir"
                label="Minecraft working directory"
                :readonly="isWorkingDirEdit === false"
                @click:prepend="actionField('edit','workingDir')"
                @keyup.enter="actionField('save','workingDir')"
                @keyup.esc="actionField('cancel','workingDir')"
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
      max-width="300px"
    >
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
                @click="triggerAction('start')"
              >
                Start
              </v-btn>
            </div>
            <div v-else>
              <v-btn
                color="warning"
                outlined
                small
                @click="triggerAction('stop')"
              >
                Stop 
              </v-btn>

              <span> &nbsp; </span>

              <v-btn
                color="warning"
                outlined
                small
                @click="triggerAction('restart')"
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
      addUserEmail: null,
      addUserDialog: false,
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
      if (this.serversDict[this.serverId].groupMembers && 
          this.serversDict[this.serverId].groupMembers.length > 0) {
            return JSON.parse(this.serversDict[this.serverId].groupMembers)
          }
      else {
        return []
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
  },
  methods: {
    async actionField(action,param) {
      if (param == "runCommand") {
        if (action == 'edit' && this.isRunCommandEdit == true) {
          action = 'save'
        }
        this.isRunCommandEdit = !this.isRunCommandEdit;
        
        switch(action) {
          case 'cancel':
            this.runCommand = this.serversDict[this.serverId].runCommand;
            break;
          case 'save':
            if (this.runCommand != this.serversDict[this.serverId].runCommand) {
              await this.triggerAction('addparameter','/amplify/minecraftserverdashboard/' + this.serverId +'/runCommand',this.runCommand);
            }
            break;
        }
      }
      else if (param == "workingDir") {
        if (action == 'edit' && this.isWorkingDirEdit == true) {
          action = 'save'
        }
        this.isWorkingDirEdit = !this.isWorkingDirEdit;
        switch(action) {
          case 'cancel':
            this.workingDir = this.serversDict[this.serverId].workingDir;
            break;
          case 'save':
            if (this.workingDir != this.serversDict[this.serverId].workingDir) {
              await this.triggerAction('addparameter','/amplify/minecraftserverdashboard/' + this.serverId +'/workingDir',this.workingDir);
            }
            break;
        }
      }
    },
    async triggerAction(action, paramKey="", paramValue="") {
      this.serverStateConfirmation = false;
      this.addUserDialog = false;
      const input = {
        instanceId: this.serverId,
        action: action,
        paramKey: paramKey,
        paramValue: paramValue
      };
      const actionResult = await API.graphql({
        query: triggerServerAction,
        variables: { input: input },
      });

      const rsp = JSON.parse(actionResult.data.triggerServerAction);

      if (rsp.statusCode == 200) {
        this.infoMsg = "Server action: " + action + " done.";
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
            name: "NetworkOut",
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
            name: "Users",
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
