<template>
  <v-dialog :model-value="modelValue" max-width="600" @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-card-title class="d-flex align-center justify-space-between pa-4">
        <span>Create Minecraft Server</span>
        <v-btn icon size="small" variant="text" @click="$emit('update:modelValue', false)">
          <span class="material-symbols-outlined">close</span>
        </v-btn>
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef" v-model="valid">
          <v-text-field
            v-model="form.serverName"
            label="Server Name"
            variant="outlined"
            density="compact"
            :rules="[v => !!v || 'Required', v => /^[a-zA-Z0-9_-]{3,50}$/.test(v) || '3-50 chars, alphanumeric, dashes, underscores']"
            class="mb-2"
          />

          <v-select
            v-model="form.instanceType"
            label="Instance Type"
            variant="outlined"
            density="compact"
            :items="instanceTypes"
            class="mb-2"
          />

          <v-divider class="my-4" />
          <div class="text-subtitle-2 mb-3">Minecraft Configuration</div>

          <v-text-field
            v-model="form.minecraftVersion"
            label="Minecraft Version"
            variant="outlined"
            density="compact"
            placeholder="LATEST"
            hint="e.g. LATEST, 1.20.4, 1.21.1"
            persistent-hint
            class="mb-2"
          />

          <v-select
            v-model="form.minecraftType"
            label="Server Type"
            variant="outlined"
            density="compact"
            :items="serverTypes"
            class="mb-2"
          />

          <v-select
            v-model="form.minecraftMemory"
            label="Memory Allocation"
            variant="outlined"
            density="compact"
            :items="memoryOptions"
            class="mb-2"
          />

          <v-divider class="my-4" />
          <div class="text-subtitle-2 mb-3">Auto-Shutdown</div>

          <v-select
            v-model="form.shutdownMethod"
            label="Shutdown Method"
            variant="outlined"
            density="compact"
            :items="shutdownMethods"
            class="mb-2"
          />

          <template v-if="form.shutdownMethod === 'CPUUtilization'">
            <v-slider
              v-model="form.alarmThreshold"
              label="CPU Threshold (%)"
              :min="0"
              :max="20"
              :step="1"
              thumb-label
              class="mb-2"
            />
            <v-slider
              v-model="form.alarmEvaluationPeriod"
              label="Evaluation Period (min)"
              :min="5"
              :max="60"
              :step="5"
              thumb-label
            />
          </template>

          <template v-if="form.shutdownMethod === 'Schedule'">
            <v-text-field
              v-model="form.startScheduleExpression"
              label="Start Schedule (cron)"
              variant="outlined"
              density="compact"
              placeholder="0 14 * * 1-5"
              hint="Minute Hour DayOfMonth Month DayOfWeek"
              persistent-hint
              class="mb-2"
            />
            <v-text-field
              v-model="form.stopScheduleExpression"
              label="Stop Schedule (cron)"
              variant="outlined"
              density="compact"
              placeholder="0 22 * * 1-5"
              hint="Minute Hour DayOfMonth Month DayOfWeek"
              persistent-hint
            />
          </template>
        </v-form>
      </v-card-text>

      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn variant="text" @click="$emit('update:modelValue', false)">Cancel</v-btn>
        <v-btn color="#171717" :loading="loading" :disabled="!valid" @click="submit">
          Create Server
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, reactive } from 'vue'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'created'])

const formRef = ref(null)
const valid = ref(false)
const loading = ref(false)

const form = reactive({
  serverName: '',
  instanceType: 't3.small',
  minecraftVersion: 'LATEST',
  minecraftType: 'VANILLA',
  minecraftMemory: '2G',
  shutdownMethod: 'CPUUtilization',
  alarmThreshold: 5,
  alarmEvaluationPeriod: 30,
  startScheduleExpression: '',
  stopScheduleExpression: '',
})

const instanceTypes = [
  { title: 't3.micro (1 vCPU, 1GB) - Testing', value: 't3.micro' },
  { title: 't3.small (2 vCPU, 2GB) - Small', value: 't3.small' },
  { title: 't3.medium (2 vCPU, 4GB) - Medium', value: 't3.medium' },
  { title: 't3.large (2 vCPU, 8GB) - Large', value: 't3.large' },
  { title: 't3.xlarge (4 vCPU, 16GB) - XL', value: 't3.xlarge' },
]

const serverTypes = [
  { title: 'Vanilla', value: 'VANILLA' },
  { title: 'Paper (Performance)', value: 'PAPER' },
  { title: 'Forge (Mods)', value: 'FORGE' },
  { title: 'Fabric (Mods)', value: 'FABRIC' },
  { title: 'Spigot (Plugins)', value: 'SPIGOT' },
]

const memoryOptions = [
  { title: '1 GB - Minimal', value: '1G' },
  { title: '2 GB - Small (1-5 players)', value: '2G' },
  { title: '4 GB - Medium (5-15 players)', value: '4G' },
  { title: '6 GB - Large (15-30 players)', value: '6G' },
  { title: '8 GB - XL (30+ players)', value: '8G' },
]

const shutdownMethods = [
  { title: 'CPU-based (auto-stop when idle)', value: 'CPUUtilization' },
  { title: 'Schedule (start/stop at specific times)', value: 'Schedule' },
  { title: 'None (manual only)', value: 'None' },
]

const submit = async () => {
  const { valid: isValid } = await formRef.value.validate()
  if (!isValid) return

  loading.value = true
  try {
    emit('created', { ...form })
    Object.assign(form, {
      serverName: '',
      instanceType: 't3.small',
      minecraftVersion: 'LATEST',
      minecraftType: 'VANILLA',
      minecraftMemory: '2G',
      shutdownMethod: 'CPUUtilization',
      alarmThreshold: 5,
      alarmEvaluationPeriod: 30,
      startScheduleExpression: '',
      stopScheduleExpression: '',
    })
    emit('update:modelValue', false)
  } finally {
    loading.value = false
  }
}
</script>
