<template>
  <div class="scheduler-card">
    <div class="card-header">
      <div>
        <div class="card-title">Task Scheduler</div>
        <div class="card-subtitle">Automatic start/stop times</div>
      </div>
      <v-switch v-model="enabled" color="primary" hide-details inset density="compact" />
    </div>

    <div v-if="enabled" class="card-content">
      <div class="schedule-group">
        <div class="schedule-label">Auto Start</div>
        <div class="schedule-inputs">
          <v-text-field
            v-model="startTime"
            type="time"
            variant="outlined"
            density="compact"
            hide-details
          />
          <v-select
            v-model="startDays"
            :items="dayOptions"
            multiple
            chips
            variant="outlined"
            density="compact"
            hide-details
            placeholder="Days"
          />
        </div>
      </div>

      <div class="schedule-group">
        <div class="schedule-label">Auto Stop</div>
        <div class="schedule-inputs">
          <v-text-field
            v-model="stopTime"
            type="time"
            variant="outlined"
            density="compact"
            hide-details
          />
          <v-select
            v-model="stopDays"
            :items="dayOptions"
            multiple
            chips
            variant="outlined"
            density="compact"
            hide-details
            placeholder="Days"
          />
        </div>
      </div>

      <v-select
        v-model="timezone"
        :items="timezones"
        variant="outlined"
        density="compact"
        hide-details
        label="Timezone"
      />
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
const startTime = ref('')
const startDays = ref([])
const stopTime = ref('')
const stopDays = ref([])
const timezone = ref('America/New_York')

const dayOptions = [
  { title: 'Mon', value: '1' },
  { title: 'Tue', value: '2' },
  { title: 'Wed', value: '3' },
  { title: 'Thu', value: '4' },
  { title: 'Fri', value: '5' },
  { title: 'Sat', value: '6' },
  { title: 'Sun', value: '0' },
]

const timezones = [
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'UTC'
]

// Parse cron to time/days
const parseCron = (cron) => {
  if (!cron) return { time: '', days: [] }
  const parts = cron.split(' ')
  if (parts.length < 5) return { time: '', days: [] }
  const minute = parts[0].padStart(2, '0')
  const hour = parts[1].padStart(2, '0')
  const days = parts[4] === '*' ? ['0','1','2','3','4','5','6'] : parts[4].split(',')
  return { time: `${hour}:${minute}`, days }
}

// Build cron from time/days
const buildCron = (time, days) => {
  if (!time) return ''
  const [hour, minute] = time.split(':')
  const dayStr = days.length === 0 || days.length === 7 ? '*' : days.join(',')
  return `${parseInt(minute)} ${parseInt(hour)} * * ${dayStr}`
}

let isUpdatingFromProps = false

// Initialize from config (only once)
watch(() => props.modelValue, (cfg) => {
  if (!cfg || isUpdatingFromProps) return
  isUpdatingFromProps = true
  
  if (cfg.startScheduleExpression || cfg.stopScheduleExpression) {
    enabled.value = true
    const start = parseCron(cfg.startScheduleExpression)
    const stop = parseCron(cfg.stopScheduleExpression)
    startTime.value = start.time
    startDays.value = start.days
    stopTime.value = stop.time
    stopDays.value = stop.days
  }
  if (cfg.timezone) timezone.value = cfg.timezone
  
  setTimeout(() => { isUpdatingFromProps = false }, 0)
}, { immediate: true })

// Update config when values change
watch([enabled, startTime, startDays, stopTime, stopDays, timezone], () => {
  if (isUpdatingFromProps) return
  
  const update = { ...props.modelValue, timezone: timezone.value }
  if (enabled.value) {
    update.startScheduleExpression = buildCron(startTime.value, startDays.value)
    update.stopScheduleExpression = buildCron(stopTime.value, stopDays.value)
  } else {
    update.startScheduleExpression = ''
    update.stopScheduleExpression = ''
  }
  emit('update:modelValue', update)
})
</script>

<style scoped>
.scheduler-card {
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
  gap: 20px;
}
.card-empty {
  padding: 32px 0;
  text-align: center;
  font-size: 13px;
  color: #a3a3a3;
}
.schedule-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.schedule-label {
  font-size: 11px;
  font-weight: 500;
  color: #a3a3a3;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.schedule-inputs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
</style>
