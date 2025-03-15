<script setup>
import { reactive, ref, onMounted } from "vue";
import { useUserStore } from "../stores/user";
import { useServerStore } from "../stores/server";
import { signOut } from 'aws-amplify/auth';
import { generateClient } from 'aws-amplify/api';
import * as subscriptions from "../graphql/subscriptions";

const userStore = useUserStore();
const serverStore = useServerStore()
const graphQlClient = generateClient();

const serversList = ref([])
const serversDict = ref({})

onMounted(async () => {
    // load servers and serverDict (both are done at listServer)
    serversList.value = await serverStore.listServers()
    serversDict.value = serverStore.serversDict  
    await subscribeChangeServerInfo() 
})

async function subscribeChangeServerInfo() {
     await graphQlClient.graphql({
        query: subscriptions.onChangeState,
        variables: {},
    }).subscribe({
        next: (response) => {
            let server = response.data.onChangeState
            serverStore.updateServer(server)
            //serverStore.updateServerStateDict(server)
        },
        error: (error) => {
            console.error('Error subscribing to server info changes:', error);
        },
    });
};

const alert = reactive({
    title: null,
    type: "warning",
    text: null,
    active: false,
    icon: null
});

async function userSignOut() {
    try {
        await signOut();
        $router.push("/auth");
    } catch (error) {
        console.log("error signing out: ", error);
    }
}

function showServer(id) {
    // check if id is not null
    if (!id) return
    // check if id is not the same as the selected server
    if (id === serverStore.selectedServerId) return
    serverStore.setSelectedServerId(id)
}

</script>

<template>
    <v-navigation-drawer permanent>
        <v-list>
            <v-list-item prepend-icon=mdi-account-circle-outline :subtitle="userStore.email"
                :title="userStore.fullname"></v-list-item>
            <v-list-item prepend-icon=mdi-exit-to-app subtitle="SignOut" @click="userSignOut"></v-list-item>
        </v-list>

        <v-divider></v-divider>

        <v-progress-linear v-if="serverStore.loading" indeterminate height="5" value="5"
            color="teal"></v-progress-linear>

        <v-list v-if="serversList && serversList.length > 0" nav>
            <v-list-subheader>Servers</v-list-subheader>
            <div v-for="(item, i) in serversList" :key="i">
                <v-list-item @click="showServer(item.id)">

                    <v-list-item-title class="font-weight-black">

                        {{ serversDict[item.id].name.length > 2
                ? serversDict[item.id].name.toUpperCase()
                : item.id.toUpperCase() }}

                        <v-icon :color="serversDict[item.id].state === 'stopped'
                ? 'error'
                : serversDict[item.id].state === 'running'
                    ? 'success'
                    : 'warning'
                "> mdi-power-standby</v-icon>

                        <v-icon v-if="serversDict[item.id].iamStatus != 'ok'" color="warning">
                            mdi-alert-outline
                            <v-tooltip activator="parent" location="bottom">
                                IAM Role is not compliant</v-tooltip>
                        </v-icon>

                    </v-list-item-title>
                    <v-list-item-subtitle>
                        {{ serversDict[item.id].vCpus }} vCPU /
                        {{ serversDict[item.id].memSize / 1024 }} GB RAM /
                        {{ serversDict[item.id].diskSize }} GB Disk
                    </v-list-item-subtitle>
                </v-list-item>
            </div>
        </v-list>
    </v-navigation-drawer>
</template>