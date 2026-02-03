<template>
  <div class="app-header">
    <h1 class="header-title">{{ title }}</h1>
  </div>
</template>

<script setup>
defineProps({ title: { type: String, default: 'Dashboard' } })
</script>

<style scoped>
.app-header {
  padding: 32px 0 24px;
  border-bottom: 1px solid #e5e5e5;
  margin-bottom: 32px;
}
.header-title {
  font-size: 24px;
  font-weight: 500;
  color: #171717;
}
</style>
