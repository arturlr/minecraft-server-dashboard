<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <div class="logo">MC</div>
      <div class="logo-text">Minecraft Dashboard</div>
    </div>

    <nav class="nav">
      <router-link to="/" custom v-slot="{ isActive, navigate }">
        <div @click="navigate" :class="['nav-item', { active: isActive }]">
          Dashboard
        </div>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <div class="user-info">
        <div class="user-name">{{ userName }}</div>
        <button @click="logout" class="logout-btn">Sign out</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../../stores/user'

const router = useRouter()
const userStore = useUserStore()

const userName = computed(() => userStore.fullname || 'User')

const logout = async () => {
  await userStore.logout()
  router.push('/auth')
}
</script>

<style scoped>
.sidebar {
  width: 200px;
  height: 100vh;
  border-right: 1px solid #e5e5e5;
  display: flex;
  flex-direction: column;
  padding: 24px 0;
  background: #ffffff;
}
.sidebar-header {
  padding: 0 24px 24px;
  border-bottom: 1px solid #e5e5e5;
  margin-bottom: 24px;
}
.logo {
  width: 32px;
  height: 32px;
  background: #171717;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  border-radius: 4px;
  margin-bottom: 8px;
}
.logo-text {
  font-size: 13px;
  font-weight: 500;
  color: #171717;
}
.nav {
  flex: 1;
  padding: 0 16px;
}
.nav-item {
  padding: 8px 12px;
  font-size: 14px;
  color: #737373;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s;
}
.nav-item:hover {
  background: #fafafa;
  color: #171717;
}
.nav-item.active {
  background: #171717;
  color: white;
  font-weight: 500;
}
.sidebar-footer {
  padding: 24px 24px 0;
  border-top: 1px solid #e5e5e5;
}
.user-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.user-name {
  font-size: 13px;
  font-weight: 500;
  color: #171717;
}
.logout-btn {
  font-size: 12px;
  color: #737373;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  text-align: left;
}
.logout-btn:hover {
  color: #171717;
}
</style>
