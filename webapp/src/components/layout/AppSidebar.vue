<template>
  <v-navigation-drawer permanent width="256" color="#102216" class="border-green" border="e">
    <div class="d-flex flex-column h-100 pa-4">
      <div class="d-flex flex-column ga-6">
        <!-- Logo -->
        <div class="d-flex align-center ga-3 px-2">
          <div class="d-flex align-center justify-center rounded-lg pa-2" style="background: rgba(19,236,91,0.2)">
            <span class="material-symbols-outlined text-primary" style="font-size: 28px">dns</span>
          </div>
          <div>
            <h1 class="text-white text-lg font-weight-bold">BlockNode</h1>
            <p class="text-muted text-caption">Manager v2.4</p>
          </div>
        </div>

        <!-- Navigation -->
        <nav class="d-flex flex-column ga-2">
          <router-link to="/" custom v-slot="{ isActive, navigate }">
            <div @click="navigate" :class="['nav-item', { active: isActive }]">
              <span class="material-symbols-outlined">dashboard</span>
              <span>Dashboard</span>
            </div>
          </router-link>
          <div class="nav-item">
            <span class="material-symbols-outlined">group</span>
            <span>Members</span>
          </div>
          <div class="nav-item">
            <span class="material-symbols-outlined">settings_input_component</span>
            <span>Global Settings</span>
          </div>
          <div class="nav-item">
            <span class="material-symbols-outlined">terminal</span>
            <span>Logs</span>
          </div>
        </nav>
      </div>

      <v-spacer />

      <!-- User Profile -->
      <div class="border-t border-green pt-4">
        <v-menu>
          <template #activator="{ props }">
            <div v-bind="props" class="d-flex align-center ga-3 px-2 py-2 rounded-xl cursor-pointer user-profile">
              <v-avatar size="40" color="primary" variant="tonal">
                <span class="text-primary font-weight-bold">{{ userInitial }}</span>
              </v-avatar>
              <div class="flex-grow-1 overflow-hidden">
                <p class="text-white text-body-2 font-weight-bold text-truncate">{{ userName }}</p>
                <p class="text-muted text-caption text-truncate">{{ userRole }}</p>
              </div>
              <span class="material-symbols-outlined text-muted">expand_more</span>
            </div>
          </template>
          <v-list density="compact" bg-color="surface">
            <v-list-item @click="logout">
              <template #prepend>
                <span class="material-symbols-outlined mr-2">logout</span>
              </template>
              <v-list-item-title>Sign Out</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </div>
    </div>
  </v-navigation-drawer>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../../stores/user'

const router = useRouter()
const userStore = useUserStore()

const userName = computed(() => userStore.fullname || 'User')
const userInitial = computed(() => userName.value[0]?.toUpperCase() || 'U')
const userRole = computed(() => userStore.isAdmin ? 'Admin' : 'Member')

const logout = async () => {
  await userStore.logout()
  router.push('/auth')
}
</script>

<style scoped lang="scss">
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  cursor: pointer;
  color: #9db9a6;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;

  &:hover {
    background: rgba(255,255,255,0.05);
    color: white;
  }

  &.active {
    background: rgba(19,236,91,0.1);
    border: 1px solid rgba(19,236,91,0.2);
    color: white;
    font-weight: 700;
    .material-symbols-outlined { color: #13ec5b; }
  }
}

.user-profile:hover {
  background: rgba(255,255,255,0.05);
}
</style>
