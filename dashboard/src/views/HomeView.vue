<script setup>
import { reactive, ref, onMounted, computed } from "vue";
import Header from "../components/Header.vue";
import ServerSpecs from "../components/ServerSpecs.vue";
import ServerCharts from "../components/ServerCharts.vue";
import { useUserStore } from "../stores/user";
import { useServerStore } from "../stores/server";

const userStore = useUserStore();
const serverStore = useServerStore()

const serverName = computed(() => {
      if (
        serverStore.selectedServer.name &&
        serverStore.selectedServer.name.length > 2
      ) {
        return serverStore.selectedServer.name;
      } else {
        return serverStore.selectedServer.id;
      }
    });

</script>

<template>
  <v-layout class="rounded rounded-md">
    <Header />
    <v-main class="d-flex justify-center">
      <div v-if="serverStore.selectedServer.id != null">
        <v-card 
          class="pa-6 mx-auto"
          :title="serverName"
          :subtitle="serverStore.selectedServer.id"
        >
          <ServerSpecs />
          <ServerCharts />
        </v-card>
      </div>
    </v-main>
  </v-layout>
</template>