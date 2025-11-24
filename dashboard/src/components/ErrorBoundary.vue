<script setup>
import { ref, onErrorCaptured } from 'vue';

const props = defineProps({
  fallbackMessage: {
    type: String,
    default: 'Something went wrong. Please refresh the page.'
  }
});

const emit = defineEmits(['error']);

const hasError = ref(false);
const errorMessage = ref('');
const errorDetails = ref(null);

// Capture errors from child components
onErrorCaptured((error, instance, info) => {
  console.error('Error boundary caught error:', error);
  console.error('Component:', instance);
  console.error('Error info:', info);
  
  hasError.value = true;
  errorMessage.value = error.message || props.fallbackMessage;
  errorDetails.value = {
    error,
    instance,
    info
  };
  
  // Emit error event to parent
  emit('error', { error, instance, info });
  
  // Prevent error from propagating further
  return false;
});

function reset() {
  hasError.value = false;
  errorMessage.value = '';
  errorDetails.value = null;
}

function reload() {
  window.location.reload();
}
</script>

<template>
  <div>
    <!-- Error State -->
    <v-alert
      v-if="hasError"
      type="error"
      variant="tonal"
      border="start"
      border-color="error"
      class="ma-4"
    >
      <template v-slot:prepend>
        <v-icon size="large">mdi-alert-circle</v-icon>
      </template>
      
      <div class="font-weight-medium text-h6 mb-2">Component Error</div>
      <div class="mb-3">{{ errorMessage }}</div>
      
      <div class="d-flex gap-2">
        <v-btn
          color="error"
          variant="elevated"
          size="small"
          @click="reset"
          prepend-icon="mdi-refresh"
        >
          Try Again
        </v-btn>
        
        <v-btn
          color="error"
          variant="outlined"
          size="small"
          @click="reload"
          prepend-icon="mdi-reload"
        >
          Reload Page
        </v-btn>
      </div>
    </v-alert>
    
    <!-- Normal Content -->
    <slot v-if="!hasError"></slot>
  </div>
</template>

<style scoped>
.gap-2 {
  gap: 8px;
}
</style>
