<template>
  <div class="app-layout">
    <div class="main-content">
      <div class="content-wrapper">
        <div class="app-header">
          <h1 class="header-title">{{ title }}</h1>
          <div class="header-toolbar">
            <slot name="toolbar" />
          </div>
        </div>
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({ title: String })
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
  background: #fafafa;
}
.main-content {
  width: 100%;
}
.content-wrapper {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 48px 48px;
}
.app-header {
  padding: 32px 0 24px;
  border-bottom: 1px solid #e5e5e5;
  margin-bottom: 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-title {
  font-size: 24px;
  font-weight: 500;
  color: #171717;
}
.header-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
}
</style>
