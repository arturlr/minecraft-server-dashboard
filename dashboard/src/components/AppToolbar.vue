<script setup>
import { computed, ref } from 'vue';
import { useUserStore } from '../stores/user';
import { signOut } from 'aws-amplify/auth';
import { useRouter } from 'vue-router';
import CreateServerDialog from './CreateServerDialog.vue';

const userStore = useUserStore();
const router = useRouter();

const fullname = computed(() => userStore.fullname);
const email = computed(() => userStore.email);
const isAdmin = computed(() => userStore.isAdmin);

const showCreateDialog = ref(false);

async function userSignOut() {
  try {
    await signOut();
    router.push('/auth');
  } catch (error) {
    console.error('Error signing out:', error);
  }
}

const emit = defineEmits(['server-created']);

function handleServerCreated() {
  // Emit event to parent to refresh server list
  emit('server-created');
  console.log('Server created successfully');
}
</script>

<template>
  <v-app-bar color="primary" dark elevation="2">
    <v-app-bar-title class="font-weight-bold">
      <v-icon class="mr-2">mdi-minecraft</v-icon>
      Minecraft Server Dashboard
    </v-app-bar-title>

    <v-spacer></v-spacer>

    <!-- Add Server Button (Admin Only) -->
    <v-btn
      v-if="isAdmin"
      @click="showCreateDialog = true"
      color="accent"
      variant="elevated"
      class="mr-4"
    >
      <v-icon class="mr-2">mdi-plus</v-icon>
      Add Server
    </v-btn>

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
        <template #activator="{ props }">
          <v-icon v-bind="props">mdi-logout</v-icon>
        </template>
      </v-tooltip>
    </v-btn>

    <!-- Create Server Dialog -->
    <CreateServerDialog
      v-model:visible="showCreateDialog"
      @server-created="handleServerCreated"
    />
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
