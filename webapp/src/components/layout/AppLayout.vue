<template>
  <div class="d-flex h-100">
    <AppSidebar />
    <v-main class="bg-background">
      <AppHeader :title="title" />
      <div class="pa-6 pa-lg-10" style="max-width: 1600px; margin: 0 auto">
        <slot />
      </div>
    </v-main>
  </div>
</template>

<script setup>
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'

defineProps({ title: String })
</script>
