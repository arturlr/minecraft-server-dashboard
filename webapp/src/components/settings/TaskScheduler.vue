<template>
  <v-card color="surface-variant" class="border-green pa-6 h-100 d-flex flex-column" border="thin">
    <div class="d-flex justify-space-between align-start mb-4">
      <div>
        <h4 class="text-white text-body-1 font-weight-bold">Task Scheduler</h4>
        <p class="text-muted text-body-2">Schedule automatic start/stop times.</p>
      </div>
      <v-switch v-model="enabled" color="primary" hide-details inset />
    </div>

    <div v-if="enabled" class="d-flex flex-column ga-5">
      <!-- Start Schedule -->
      <div class="schedule-section">
        <label class="text-muted text-caption text-uppercase mb-2 d-block">Auto Start</label>
        <v-row dense>
          <v-col cols="6">
            <v-text-field
              v-model="startTime"
              label="Time"
              type="time"
              bg-color="surface"
              hide-details
              density="compact"
            />
          </v-col>
          <v-col cols="6">
            <v-select
              v-model="startDays"
              label="Days"
              :items="dayOptions"
              multiple
              chips
              bg-color="surface"
              hide-details
              density="compact"
            />
          </v-col>
        </v-row>
      </div>

      <!-- Stop Schedule -->
      <div class="schedule-section">
        <label class="text-muted text-caption text-uppercase mb-2 d-block">Auto Stop</label>
        <v-row dense>
          <v-col cols="6">
            <v-text-field
              v-model="stopTime"
              label="Time"
              type="time"
              bg-color="surface"
              hide-details
              density="compact"
            />
          </v-col>
          <v-col cols="6">
            <v-select
              v-model="stopDays"
              label="Days"
              :items="dayOptions"
              multiple
              chips
              bg-color="surface"
              hide-details
              density="compact"
            />
          </v-col>
        </v-row>
      </div>

      <!-- Timezone -->
      <v-select
        v-model="timezone"
        label="Timezone"
        :items="timezones"
        bg-color="surface"
        hide-details
        density="compact"
      />
    </div>

    <div v-else class="flex-grow-1 d-flex align-center justify-center">
      <p class="text-muted text-body-2">Enable to configure scheduled start/stop times</p>
    </div>
  </v-card>
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
  const days = parts[4] === '*' ? [] : parts[4].split(',')
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
.schedule-section {
  padding: 12px;
  background: rgba(0,0,0,0.2);
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.05);
}
</style>
