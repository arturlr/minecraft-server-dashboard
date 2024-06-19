<script setup>
import { reactive, ref, onMounted } from "vue";
import { generateClient } from 'aws-amplify/api';
import * as subscriptions from '../graphql/subscriptions';
import { Hub } from 'aws-amplify/utils';
import { useServerStore } from "../stores/server";
import VueApexCharts from "vue3-apexcharts";
import moment from "moment";

const serverStore = useServerStore()

const graphQlClient = generateClient();

const cpuSeries = ref([{ data: [] }]);
const memSeries = ref([{ data: [] }]);
const netSeries = ref([{ data: [] }]);
const usersSeries = ref([{ data: [] }]);

const currentCPU = ref(0);
const currentMemory = ref(0);
const currentNet = ref(0);
const currentUsers = ref(0);

const metricAlert = ref(false);
const metricMsg = ref(null)

const cpuOptions = ref({
    chart: {
        type: "area",
        sparkline: {
            enabled: true,
        },
    },
    title: {
        text: "CPU",
        offsetX: 30,
        style: {
            fontSize: '14px',
            cssClass: 'apexcharts-yaxis-title'
        }
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
    xaxis: {
        type: "datetime",
        labels: {
            formatter: function (val, timestamp) {
                return moment(new Date(timestamp)).format("HH:mm");
            },
        },
    },
    colors: ["#154360"],
})

const memOptions = ref({
    chart: {
        type: "area",
        sparkline: {
            enabled: true,
        },
    },
    title: {
        text: "Memory",
        offsetX: 30,
        style: {
            fontSize: '14px',
            cssClass: 'apexcharts-yaxis-title'
        }
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
    xaxis: {
        type: "datetime",
        labels: {
            formatter: function (val, timestamp) {
                return moment(new Date(timestamp)).format("HH:mm");
            },
        },
    },
    colors: ["#5DADE2"],
})

const netOptions = ref({
    chart: {
        type: "area",
        sparkline: {
            enabled: true,
        },
    },
    title: {
        text: "Networking",
        offsetX: 30,
        style: {
            fontSize: '14px',
            cssClass: 'apexcharts-yaxis-title'
        }
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
    xaxis: {
        type: "datetime",
        labels: {
            formatter: function (val, timestamp) {
                return moment(new Date(timestamp)).format("HH:mm");
            },
        },
    },
    colors: ["#D35400"],
})

const usersOptions = ref({
    chart: {
        type: "area",
        sparkline: {
            enabled: true,
        },
    },
    title: {
        text: "Users",
        offsetX: 30,
        style: {
            fontSize: '14px',
            cssClass: 'apexcharts-yaxis-title'
        }
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
    xaxis: {
        type: "datetime",
        labels: {
            formatter: function (val, timestamp) {
                return moment(new Date(timestamp)).format("HH:mm");
            },
        },
    },
    colors: ["#52B12C"],
})

function updateMetrics(name, data) {

    if (data.alertMsg && data.alertMsg.length > 0) {
        metricAlert.value = true;
        metricMsg.value = serverStore.serversDict[serverStore.selectedServerId].alertMsg
    }
    else {
        metricAlert.value = false;
        metricMsg.value = null
    }

    switch (name) {
        case "users":
            usersSeries.value = [{
                name: "users",
                data: data
            }];
            break;

        case "cpu":
            cpuSeries.value = [{
                name: "cpu",
                data: data
            }];
            break;

        case "mem":
            memSeries.value = [{
                name: "mem",
                data: data
            }];
            break

        case "net":
            netSeries.value = [{
                name: "net",
                data: data
            }]
            break;
    }
}

function classColor(sState) {
    if (sState === "running" || sState === "ok") {
        return "green";
    } else if (sState === "stopped" || sState === "fail") {
        return "red";
    } else {
        return "orange";
    }
}

async function subscribePutServerMetric() {

    await graphQlClient
        .graphql({
            query: subscriptions.onPutServerMetric,
            variables: { id: serverStore.selectedServer.id },
        }).subscribe({
            next: (response) => {
                console.log("updating: " + response.data.onPutServerMetric.id)
                const cpuData = JSON.parse(response.data.onPutServerMetric.cpuStats);
                const memData = JSON.parse(response.data.onPutServerMetric.memStats);
                const netData = JSON.parse(response.data.onPutServerMetric.networkStats);
                const usersData = JSON.parse(response.data.onPutServerMetric.activeUsers);

                if (cpuData.length > 0)
                    currentCPU.value = cpuData[cpuData.length - 1].y;
                cpuOptions.value = {
                    title: {
                        text: "CPU - " + currentCPU.value.toString() + " %"
                    }
                }
                updateMetrics('cpu', cpuData);

                if (netData.length > 0)
                    currentNet.value = netData[netData.length - 1].y;
                netOptions.value = {
                    title: {
                        text: "Network - " + currentNet.value.toString() + " packages"
                    }
                }
                updateMetrics('net', netData);

                if (memData.length > 0)
                    currentMemory.value = memData[memData.length - 1].y;
                memOptions.value = {
                    title: {
                        text: "Memory - " + currentMemory.value.toString() + " %"
                    }
                }
                updateMetrics('mem', memData);

                if (usersData.length > 0)
                    currentUsers.value = usersData[usersData.length - 1].y;
                usersOptions.value = {
                    title: {
                        text: "Users - " + currentUsers.value.toString()
                    }
                }
                updateMetrics('users', usersData);

            },
            error: (error) => console.warn(error)
        });
}

onMounted(async () => {
    await subscribePutServerMetric()
})

</script>

<template>
    <v-card variant="plain">
        <VueApexCharts ref="usersChart" height="70" :options="usersOptions" :series="usersSeries" />
    </v-card>

    <v-card variant="plain">
        <VueApexCharts ref="cpuChart" height="70" :options="cpuOptions" :series="cpuSeries" />
    </v-card>

    <v-card variant="plain">
        <VueApexCharts ref="memChart" height="70" :options="memOptions" :series="memSeries" />
    </v-card>

    <v-card variant="plain">
        <VueApexCharts ref="netChart" height="70" :options="netOptions" :series="netSeries" />
    </v-card>
</template>