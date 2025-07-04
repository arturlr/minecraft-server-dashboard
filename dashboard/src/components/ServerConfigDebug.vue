<template>
  <v-card class="ma-4">
    <v-card-title>Server Config Debug</v-card-title>
    <v-card-text>
      <v-btn @click="testGetServerConfig" color="primary" class="mr-2">Test Get Config</v-btn>
      <v-btn @click="testGetServerUsers" color="secondary">Test Get Users</v-btn>
      
      <v-divider class="my-4"></v-divider>
      
      <div v-if="configData">
        <h3>Server Config Data:</h3>
        <pre>{{ JSON.stringify(configData, null, 2) }}</pre>
      </div>
      
      <div v-if="usersData">
        <h3>Server Users Data:</h3>
        <pre>{{ JSON.stringify(usersData, null, 2) }}</pre>
      </div>
      
      <div v-if="error" class="error--text">
        <h3>Error:</h3>
        <pre>{{ error }}</pre>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref } from 'vue'
import { useServerStore } from '../stores/server'

const serverStore = useServerStore()
const configData = ref(null)
const usersData = ref(null)
const error = ref(null)

async function testGetServerConfig() {
  try {
    error.value = null
    console.log('Testing getServerConfig for server:', serverStore.selectedServerId)
    configData.value = await serverStore.getServerConfig()
    console.log('Config data received:', configData.value)
  } catch (err) {
    error.value = err.message
    console.error('Error getting server config:', err)
  }
}

async function testGetServerUsers() {
  try {
    error.value = null
    console.log('Testing getServerUsers for server:', serverStore.selectedServerId)
    usersData.value = await serverStore.getServerUsers()
    console.log('Users data received:', usersData.value)
  } catch (err) {
    error.value = err.message
    console.error('Error getting server users:', err)
  }
}
</script>