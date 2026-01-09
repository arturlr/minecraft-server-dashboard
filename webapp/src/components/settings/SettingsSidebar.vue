<template>
  <v-navigation-drawer permanent width="280" color="#102216" class="border-green" border="e">
    <div class="d-flex flex-column h-100">
      <div class="pa-6">
        <!-- Logo -->
        <div class="d-flex align-center ga-4 mb-8">
          <v-avatar size="48" color="primary" variant="tonal" rounded="lg">
            <span class="material-symbols-outlined text-primary">dns</span>
          </v-avatar>
          <div>
            <h1 class="text-white text-body-1 font-weight-bold">Minecraft Server</h1>
            <p class="text-muted text-caption text-uppercase" style="letter-spacing: 1px">Dashboard</p>
          </div>
        </div>

        <!-- Navigation -->
        <nav class="d-flex flex-column ga-2">
          <div v-for="item in navItems" :key="item.label" :class="['settings-nav-item', { active: item.active }]">
            <span class="material-symbols-outlined">{{ item.icon }}</span>
            <span>{{ item.label }}</span>
          </div>
        </nav>
      </div>

      <v-spacer />

      <div class="pa-6 border-t border-green">
        <div class="settings-nav-item" @click="$router.push('/')">
          <span class="material-symbols-outlined">logout</span>
          <span>Back to Dashboard</span>
        </div>
      </div>
    </div>
  </v-navigation-drawer>
</template>

<script setup>
const navItems = [
  { icon: 'settings', label: 'General Settings', active: true },
  { icon: 'schedule', label: 'Automation', active: false },
  { icon: 'group', label: 'Members', active: false },
  { icon: 'backup', label: 'Backups', active: false },
  { icon: 'terminal', label: 'Console', active: false },
]
</script>

<style scoped lang="scss">
.settings-nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  color: #9db9a6;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;

  &:hover {
    background: #1c2e24;
    color: white;
  }

  &.active {
    background: rgba(19,236,91,0.2);
    border: 1px solid rgba(19,236,91,0.2);
    color: #13ec5b;
    font-weight: 700;
  }
}
</style>
