<template>
  <v-card color="surface-variant" class="border-green pa-6" border="thin">
    <div class="d-flex justify-space-between align-start mb-6">
      <div>
        <h4 class="text-white text-body-1 font-weight-bold">Resource Watchdog</h4>
        <p class="text-muted text-body-2">Auto-shutdown when idle to save resources.</p>
      </div>
      <v-switch v-model="enabled" color="primary" hide-details inset />
    </div>

    <div class="d-flex flex-column ga-6">
      <div>
        <div class="d-flex justify-space-between text-body-2 mb-2">
          <span class="text-white">CPU Idle Threshold</span>
          <span class="text-primary font-mono">{{ config.alarmThreshold || 15 }}%</span>
        </div>
        <v-slider 
          :model-value="config.alarmThreshold || 15"
          @update:model-value="updateField('alarmThreshold', $event)"
          :min="0" 
          :max="100" 
          color="primary" 
          track-color="#28392e" 
          hide-details 
        />
      </div>

      <v-text-field 
        :model-value="config.alarmEvaluationPeriod || 10"
        @update:model-value="updateField('alarmEvaluationPeriod', $event)"
        label="Idle Duration (minutes)" 
        type="number" 
        bg-color="surface" 
        hide-details 
      />
    </div>
  </v-card>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({ modelValue: Object })
const emit = defineEmits(['update:modelValue'])

const config = computed(() => props.modelValue || {})
const enabled = ref(true)

const updateField = (field, value) => {
  emit('update:modelValue', { ...config.value, [field]: value })
}
</script>

<style scoped>
.font-mono { font-family: monospace; }
</style>
