<template>
  <div class="watchdog-card">
    <div class="card-header">
      <div>
        <div class="card-title">Resource Watchdog</div>
        <div class="card-subtitle">Auto-shutdown when idle</div>
      </div>
      <v-switch v-model="enabled" color="primary" hide-details inset density="compact" />
    </div>

    <div v-if="enabled" class="card-content">
      <div class="setting-row">
        <div class="setting-label">CPU Threshold</div>
        <div class="setting-value">{{ threshold }}%</div>
      </div>
      <v-slider 
        v-model="threshold"
        :min="1" 
        :max="100" 
        color="#171717" 
        track-color="#e5e5e5" 
        hide-details 
      />
      
      <div class="setting-row mt-4">
        <div class="setting-label">Idle Duration</div>
        <v-text-field 
          v-model.number="evaluationPeriod"
          type="number" 
          suffix="min"
          variant="outlined"
          density="compact"
          hide-details 
        />
      </div>
    </div>

    <div v-else class="card-empty">
      Disabled
    </div>
  </div>
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
  threshold.value = Math.round(cfg.alarmThreshold) || 15
  evaluationPeriod.value = Math.round(cfg.alarmEvaluationPeriod) || 10
  
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
.watchdog-card {
  padding: 24px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  height: 100%;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}
.card-title {
  font-size: 16px;
  font-weight: 500;
  color: #171717;
  margin-bottom: 4px;
}
.card-subtitle {
  font-size: 13px;
  color: #737373;
}
.card-content {
  display: flex;
  flex-direction: column;
}
.card-empty {
  padding: 32px 0;
  text-align: center;
  font-size: 13px;
  color: #a3a3a3;
}
.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.setting-label {
  font-size: 13px;
  color: #737373;
}
.setting-value {
  font-size: 14px;
  font-weight: 500;
  color: #171717;
  font-family: monospace;
}
</style>
