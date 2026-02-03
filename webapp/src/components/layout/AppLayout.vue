<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <div class="content-wrapper">
        <AppHeader :title="title" />
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup>
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'

defineProps({ title: String })
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  background: #fafafa;
}
.main-content {
  flex: 1;
  overflow-y: auto;
}
.content-wrapper {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 48px 48px;
}
</style>
