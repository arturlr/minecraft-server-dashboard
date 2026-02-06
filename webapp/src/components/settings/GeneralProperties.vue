<template>
  <div>
    <div class="section-header">
      <span class="material-symbols-outlined">tune</span>
      <h3>General Properties</h3>
    </div>

    <div class="properties-grid">
      <v-text-field 
        v-model="form.runCommand" 
        label="Run Command" 
        variant="outlined"
        density="compact"
        placeholder="java -jar server.jar"
        hint="Legacy field - not used with Docker"
        persistent-hint
        disabled
      />
      <v-text-field 
        v-model="form.workDir" 
        label="Working Directory" 
        variant="outlined"
        density="compact"
        placeholder="/home/minecraft"
        hint="Legacy field - not used with Docker"
        persistent-hint
        disabled
      />
      <v-text-field 
        v-model="form.minecraftVersion" 
        label="Minecraft Version" 
        variant="outlined"
        density="compact"
        placeholder="1.20.4" 
      />
      <v-text-field 
        v-model="form.dockerImageTag" 
        label="Docker Image Tag" 
        variant="outlined"
        density="compact"
        placeholder="latest"
        hint="Stop and start server to update containers"
        persistent-hint
        :rules="dockerTagRules"
      />
      <v-text-field 
        v-model="form.dockerComposeVersion" 
        label="Docker Compose Version" 
        variant="outlined"
        density="compact"
        placeholder="1.0.0"
        hint="Version of docker-compose.yml configuration"
        persistent-hint
        :rules="dockerTagRules"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ modelValue: Object })
const emit = defineEmits(['update:modelValue'])

const form = computed({
  get: () => props.modelValue || {},
  set: (val) => {
    if (val && typeof val === 'object') {
      emit('update:modelValue', { ...val })
    }
  }
})

const dockerTagRules = [
  v => !v || /^[a-zA-Z0-9._-]+$/.test(v) || 'Only alphanumeric, dots, dashes, and underscores allowed'
]
</script>

<style scoped>
.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e5e5;
}
.section-header .material-symbols-outlined {
  font-size: 20px;
  color: #171717;
}
.section-header h3 {
  font-size: 16px;
  font-weight: 500;
  color: #171717;
  margin: 0;
}
.properties-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}
</style>
