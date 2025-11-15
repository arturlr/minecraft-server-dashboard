<template>
  <div class="actions-menu d-flex align-center ga-1">
    <v-tooltip text="View Statistics" location="top">
      <template v-slot:activator="{ props }">
        <v-btn 
          icon 
          size="small" 
          variant="text"
          class="action-btn"
          v-bind="props" 
          @click="$emit('open-stats')"
        >
          <v-icon>mdi-chart-line</v-icon>
        </v-btn>
      </template>
    </v-tooltip>
    
    <v-tooltip text="Configuration" location="top">
      <template v-slot:activator="{ props }">
        <v-btn 
          icon 
          size="small" 
          variant="text"
          class="action-btn"
          v-bind="props" 
          @click="$emit('open-config')"
        >
          <v-icon>mdi-cog</v-icon>
        </v-btn>
      </template>
    </v-tooltip>
  </div>
</template>

<script setup>
const props = defineProps({
  serverId: {
    type: String,
    required: true
  },
  serverState: {
    type: String,
    required: true
  },
  iamStatus: {
    type: String,
    default: 'ok'
  }
})

const emit = defineEmits(['open-config', 'open-stats'])
</script>

<style scoped>
/* Mobile responsive adjustments for action buttons */
@media (max-width: 599px) {
  .actions-menu {
    gap: 4px !important;
  }
  
  /* Make action buttons touch-friendly on mobile (44x44px minimum) */
  .action-btn {
    min-width: 44px !important;
    min-height: 44px !important;
    width: 44px !important;
    height: 44px !important;
  }
  
  .action-btn :deep(.v-icon) {
    font-size: 20px;
  }
}

/* Tablet adjustments */
@media (min-width: 600px) and (max-width: 959px) {
  .actions-menu {
    gap: 6px !important;
  }
  
  .action-btn {
    min-width: 40px !important;
    min-height: 40px !important;
  }
}

/* Desktop - default spacing */
@media (min-width: 960px) {
  .actions-menu {
    gap: 8px !important;
  }
}
</style>
