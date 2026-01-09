<template>
  <v-card color="surface-variant" class="border-green pa-6" border="thin">
    <div class="d-flex justify-space-between align-start mb-6">
      <div>
        <h4 class="text-white text-body-1 font-weight-bold">Resource Watchdog</h4>
        <p class="text-muted text-body-2">Auto-shutdown when idle to save resources.</p>
      </div>
      <v-switch v-model="enabled" color="primary" hide-details inset />
    </div>

    <div v-if="enabled" class="d-flex flex-column ga-6">
      <div>
        <div class="d-flex justify-space-between text-body-2 mb-2">
          <span class="text-white">CPU Idle Threshold</span>
          <span class="text-primary font-mono">{{ threshold }}%</span>
        </div>
        <v-slider 
          v-model="threshold"
          :min="1" 
          :max="100" 
          color="primary" 
          track-color="#28392e" 
          hide-details 
        />
      </div>

      <v-text-field 
        v-model.number="evaluationPeriod"
        label="Idle Duration (minutes)" 
        type="number" 
        bg-color="surface" 
        hide-details 
      />
    </div>

    <div v-else class="text-center py-4">
      <p class="text-muted text-body-2">CPU-based auto-shutdown is disabled</p>
    </div>
  </v-card>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({ modelValue: Object })
const emit = defineEmits(['update:modelValue'])

const enabled = ref(false)
const threshold = ref(15)
const evaluationPeriod = ref(10)

let isUpdatingFromProps = false

// Initialize from props
watch(() => props.modelValue, (cfg) => {
  if (!cfg || isUpdatingFromProps) return
  isUpdatingFromProps = true
  
  // If alarmThreshold > 0, CPU shutdown is enabled
  enabled.value = cfg.alarmThreshold > 0
  threshold.value = cfg.alarmThreshold || 15
  evaluationPeriod.value = cfg.alarmEvaluationPeriod || 10
  
  setTimeout(() => { isUpdatingFromProps = false }, 0)
}, { immediate: true })

// Emit changes
watch([enabled, threshold, evaluationPeriod], () => {
  if (isUpdatingFromProps) return
  
  emit('update:modelValue', {
    ...props.modelValue,
    alarmThreshold: enabled.value ? threshold.value : 0,
    alarmEvaluationPeriod: evaluationPeriod.value
  })
})
</script>

<style scoped>
.font-mono { font-family: monospace; }
</style>
