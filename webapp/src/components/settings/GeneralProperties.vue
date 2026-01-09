<template>
  <div>
    <div class="d-flex align-center ga-2 mb-5 pb-3 border-b border-green">
      <span class="material-symbols-outlined text-primary">tune</span>
      <h3 class="text-white text-h6 font-weight-bold">General Properties</h3>
    </div>

    <v-row>
      <v-col cols="12" md="6">
        <v-text-field v-model="form.runCommand" label="Run Command" bg-color="surface" placeholder="java -jar server.jar" />
      </v-col>
      <v-col cols="12" md="6">
        <v-text-field v-model="form.workDir" label="Working Directory" bg-color="surface" placeholder="/home/minecraft" />
      </v-col>
      <v-col cols="12" md="6">
        <v-text-field v-model="form.minecraftVersion" label="Minecraft Version" bg-color="surface" placeholder="1.20.4" />
      </v-col>
    </v-row>
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
