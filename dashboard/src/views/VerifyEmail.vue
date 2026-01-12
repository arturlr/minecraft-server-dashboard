<script setup>
import { reactive, ref, onMounted, computed } from "vue";
import { useRoute } from 'vue-router';
import { useServerStore } from "../stores/server";
import { useUserStore } from "../stores/user";

const serverStore = useServerStore()
const userStore = useUserStore();
const route = useRoute();

onMounted(async () => {
  const code = route.query.code;
  const email = userStore.email
  console.log(code)
  console.log(email)
  const serverSettings = await serverStore.verifyEmail(code,email);
  console.log(serverSettings)
});

</script>

<template>
  <div>
    <v-toolbar density="compact">
      <v-app-bar-nav-icon></v-app-bar-nav-icon>

      <v-toolbar-title>Minecraft Dashboard</v-toolbar-title>
</v-toolbar>
  </div>  
</template>




