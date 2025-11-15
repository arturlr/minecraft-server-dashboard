<script setup>
import { ref, watch } from 'vue';
import ServerSettings from './ServerSettings.vue';

const props = defineProps({
  visible: {
    type: Boolean,
    required: true
  },
  serverId: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['update:visible', 'config-saved']);

const loading = ref(false);

// Handle configuration saved event from ServerSettings
function handleConfigSaved() {
  emit('config-saved');
  emit('update:visible', false);
}

// Handle close event from ServerSettings
function handleClose() {
  emit('update:visible', false);
}

// Watch for visibility changes to manage loading state
watch(() => props.visible, (newValue) => {
  if (!newValue) {
    loading.value = false;
  }
});
</script>

<template>
  <v-dialog 
    :model-value="visible" 
    @update:model-value="$emit('update:visible', $event)"
    max-width="900px" 
    :fullscreen="$vuetify.display.mobile"
    persistent 
    scrollable
    transition="dialog-bottom-transition"
  >
    <v-card>
      <v-overlay
        :model-value="loading"
        contained
        class="align-center justify-center"
      >
        <v-progress-circular
          indeterminate
          size="64"
          color="primary"
        ></v-progress-circular>
      </v-overlay>

      <v-card-title class="bg-primary text-white pa-6">
        <div class="d-flex align-center w-100">
          <v-icon class="me-3" size="28">mdi-cog</v-icon>
          <div>
            <div class="text-h5 font-weight-bold">Server Configuration</div>
            <div class="text-body-2 opacity-90">Manage your Minecraft server settings</div>
          </div>
          <v-spacer></v-spacer>
          <v-btn 
            icon 
            variant="text" 
            @click="handleClose"
            class="text-white"
          >
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </div>
      </v-card-title>

      <v-card-text class="pa-0">
        <ServerSettings 
          @config-saved="handleConfigSaved"
          @close="handleClose"
        />
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped>
/* Mobile responsive adjustments */
@media (max-width: 599px) {
  :deep(.v-card-title) {
    padding: 16px !important;
  }
  
  :deep(.v-card-text) {
    padding: 12px !important;
  }
  
  /* Ensure touch-friendly buttons */
  :deep(.v-btn) {
    min-width: 44px !important;
    min-height: 44px !important;
  }
}

/* Tablet adjustments */
@media (min-width: 600px) and (max-width: 959px) {
  :deep(.v-card-title) {
    padding: 20px !important;
  }
}
</style>
