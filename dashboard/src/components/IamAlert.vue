<script setup>
import { ref } from 'vue';

const props = defineProps({
  servers: {
    type: Array,
    required: true,
    default: () => []
  }
});

const emit = defineEmits(['fix-iam']);

const fixingServers = ref(new Set());

function handleFixIam(serverId) {
  fixingServers.value.add(serverId);
  emit('fix-iam', serverId);
}

// Remove server from fixing set when it's no longer in the servers list
function isFixing(serverId) {
  return fixingServers.value.has(serverId);
}
</script>

<template>
  <v-alert
    v-if="servers.length > 0"
    type="warning"
    variant="tonal"
    border="start"
    border-color="warning"
    class="mb-4"
  >
    <template #prepend>
      <v-icon size="large">mdi-alert-circle</v-icon>
    </template>

    <div class="font-weight-medium text-h6 mb-2">IAM Role Issues Detected</div>
    <div class="mb-3 text-body-2">
      The following servers need IAM role fixes to enable power control and other operations:
    </div>

    <v-list density="compact" class="bg-transparent">
      <v-list-item
        v-for="server in servers"
        :key="server.id"
        class="px-0 mb-2"
      >
        <template #prepend>
          <v-icon color="warning" size="small" class="mr-2">
            mdi-server-off
          </v-icon>
        </template>

        <v-list-item-title class="font-weight-medium">
          {{ server.name && server.name.length > 2 ? server.name : server.id }}
        </v-list-item-title>

        <v-list-item-subtitle class="text-caption">
          Instance ID: {{ server.id }}
        </v-list-item-subtitle>

        <template #append>
          <v-btn
            color="warning"
            variant="elevated"
            size="small"
            @click="handleFixIam(server.id)"
            :loading="isFixing(server.id)"
            :disabled="isFixing(server.id)"
            prepend-icon="mdi-wrench"
            class="fix-btn"
          >
            Fix IAM Role
          </v-btn>
        </template>
      </v-list-item>
    </v-list>
  </v-alert>
</template>

<style scoped>
/* Mobile responsive adjustments */
@media (max-width: 599px) {
  :deep(.v-list-item) {
    flex-direction: column;
    align-items: flex-start !important;
  }

  :deep(.v-list-item__append) {
    margin-top: 8px;
    margin-left: 0 !important;
  }

  .fix-btn {
    width: 100%;
  }

  :deep(.v-list-item-subtitle) {
    font-size: 0.7rem;
  }
}

/* Tablet adjustments */
@media (min-width: 600px) and (max-width: 959px) {
  .fix-btn {
    min-width: 140px;
  }
}
</style>
