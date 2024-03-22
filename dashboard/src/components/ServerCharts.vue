<script setup>
import { reactive, ref, onMounted } from "vue";
import { generateClient, CONNECTION_STATE_CHANGE } from 'aws-amplify/api';
import * as subscriptions from '../graphql/subscriptions';
import { Hub } from 'aws-amplify/utils';
import { useUserStore } from "../stores/user";
import { useServerStore } from "../stores/server";
import VueApexCharts from "vue3-apexcharts";
import moment from "moment";

const userStore = useUserStore();
const serverStore = useServerStore()

const graphQlClient = generateClient();

const cpuSeries = ref([{ data: [] }]);
const memSeries = ref([{ data: [] }]);
const netSeries = ref([{ data: [] }]);
const usersSeries = ref([{ data: [] }]);

const metricAlert = ref(false);
const metricMsg = ref(null)


const lineChartOptions = ref({
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
})

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

    // if (name == "users" && data.length > 0) {
    //     this.$refs.users.updateOptions({
    //         title: {
    //             text: String(serverStore.selectedServer.activeUsers[serverStore.selectedServer.activeUsers.length - 1].y) + " Connection(s)"
    //         }
    //     })
    // }

    if (data.alertMsg && data.alertMsg.length > 0) {
        metricAlert.value = true;
        metricMsg.value = serverStore.selectedServer.alertMsg
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

    const createSub = await graphQlClient
        .graphql({ query: subscriptions.onPutServerMetric })
        .subscribe({
            next: ({ data }) => {
                console.log("updating metrics for: " + data.onPutServerMetric.id)
                if (data.onPutServerMetric.id === serverStore.selectedServer.id) {
                    const cpuData = JSON.parse(data.onPutServerMetric.cpuStats)
                    const memData = JSON.parse(data.onPutServerMetric.memStats)
                    const netData = JSON.parse(data.onPutServerMetric.networkStats)
                    const usersData = JSON.parse(data.onPutServerMetric.activeUsers)
                    if (cpuData.length > 0)
                        updateMetrics('cpu', cpuData);
                    
                    if (netData.length > 0)
                        updateMetrics('net', netData);

                    if (memData.length > 0)
                        updateMetrics('mem', memData);

                    if (usersData.length > 0)
                        updateMetrics('users', usersData);
                }
            },
            error: (error) => console.warn(error)
        });
}

onMounted(async () => {
    subscribePutServerMetric()
})

</script>

<template>

    <v-card>
        <VueApexCharts height="70" :options="usersOptions" :series="usersSeries" />
    </v-card>

    <v-card>
        <VueApexCharts height="70" :options="cpuOptions" :series="cpuSeries" />
    </v-card>

    <v-card>
        <VueApexCharts height="70" :options="memOptions" :series="memSeries" />
    </v-card>

    <v-card>
        <VueApexCharts height="70" :options="netOptions" :series="netSeries" />
    </v-card>
</template>