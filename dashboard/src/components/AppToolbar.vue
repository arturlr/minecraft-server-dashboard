<script setup>
import { computed } from 'vue';
import { useUserStore } from '../stores/user';
import { signOut } from 'aws-amplify/auth';
import { useRouter } from 'vue-router';

const userStore = useUserStore();
const router = useRouter();

const fullname = computed(() => userStore.fullname);
const email = computed(() => userStore.email);
const isAdmin = computed(() => userStore.isAdmin);

async function userSignOut() {
  try {
    await signOut();
    router.push('/auth');
  } catch (error) {
    console.error('Error signing out:', error);
  }
}
</script>

<template>
  <v-app-bar color="primary" dark elevation="2">
    <v-app-bar-title class="font-weight-bold">
      <v-icon class="mr-2">mdi-minecraft</v-icon>
      Minecraft Server Dashboard
    </v-app-bar-title>

    <v-spacer></v-spacer>

    <div class="d-flex align-center mr-4 user-info">
      <v-icon class="mr-2">mdi-account-circle</v-icon>
      <div class="d-flex flex-column">
        <span class="text-body-2 font-weight-medium">{{ fullname }}</span>
        <span class="text-caption user-email">{{ email }}</span>
      </div>
      <v-chip v-if="isAdmin" color="accent" size="small" class="ml-2" label>
        Admin
      </v-chip>
    </div>

    <v-btn icon @click="userSignOut" class="ml-2">
      <v-tooltip text="Sign Out" location="bottom">
        <template v-slot:activator="{ props }">
          <v-icon v-bind="props">mdi-logout</v-icon>
        </template>
      </v-tooltip>
    </v-btn>
  </v-app-bar>
</template>

<style scoped>
/* Mobile responsive adjustments */
@media (max-width: 599px) {
  .user-email {
    display: none;
  }

  .user-info {
    margin-right: 8px !important;
  }

  :deep(.v-app-bar-title) {
    font-size: 1rem !important;
  }
}

/* Tablet adjustments */
@media (min-width: 600px) and (max-width: 959px) {
  :deep(.v-app-bar-title) {
    font-size: 1.125rem !important;
  }
}
</style>
