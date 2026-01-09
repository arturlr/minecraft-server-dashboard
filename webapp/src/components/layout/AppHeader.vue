<template>
  <v-app-bar flat color="#102216" class="border-b border-green px-2">
    <v-app-bar-title class="text-white font-weight-bold">{{ title }}</v-app-bar-title>
    <template #append>
      <v-btn icon variant="flat" color="surface" class="mr-2">
        <span class="material-symbols-outlined">notifications</span>
      </v-btn>
      <v-btn color="primary" class="glow-primary font-weight-bold">
        <span class="material-symbols-outlined mr-2">add</span>
        New Instance
      </v-btn>
    </template>
  </v-app-bar>
</template>

<script setup>
defineProps({ title: { type: String, default: 'Command Center' } })
</script>
