<script setup>
import { reactive, ref, onMounted } from "vue";
import { useUserStore } from "../stores/user";
import { useServerStore } from "../stores/server";
import { signOut } from 'aws-amplify/auth';

const userStore = useUserStore();
const serverStore = useServerStore()

const serversList = ref([])
const serversDict = ref({})

onMounted(async () => {
    serversList.value = await serverStore.listServers()
    serversDict.value = serverStore.serversDict
})

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
    serverStore.selectedServer = serverStore.serversDict[id]
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

            <v-list v-if="serversList && serversList.length > 0" nav>
                <v-list-subheader>Servers</v-list-subheader>
                <div v-for="(item, i) in serversList" :key="i">
                    <v-list-item :title="serversDict[item.id].name.length > 2
                    ? serversDict[item.id].name
                    : item.id" @click="showServer(item.id)">
                        <template v-slot:prepend>
                            <v-icon :color="serversDict[item.id].state === 'stopped'
                        ? 'error'
                        : serversDict[item.id].state === 'running'
                            ? 'success'
                            : 'warning'
                    "> mdi-power</v-icon>
                        </template>
                    </v-list-item>
                </div>
            </v-list>
        </v-navigation-drawer>
</template>