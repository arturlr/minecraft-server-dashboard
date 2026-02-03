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
      />
      <v-text-field 
        v-model="form.workDir" 
        label="Working Directory" 
        variant="outlined"
        density="compact"
        placeholder="/home/minecraft" 
      />
      <v-text-field 
        v-model="form.minecraftVersion" 
        label="Minecraft Version" 
        variant="outlined"
        density="compact"
        placeholder="1.20.4" 
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
  set: (val) => emit('update:modelValue', val)
})
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
