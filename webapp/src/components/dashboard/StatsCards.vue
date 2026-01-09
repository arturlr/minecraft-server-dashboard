<template>
  <v-row>
    <v-col cols="12" sm="6">
      <v-card color="surface" class="pa-5 border-green" border="thin">
        <div class="d-flex justify-space-between align-center mb-1">
          <span class="text-muted text-body-2">Servers Online</span>
          <span class="material-symbols-outlined text-primary">dns</span>
        </div>
        <p class="text-white text-h4 font-weight-bold">
          {{ online }} <span class="text-grey text-body-1 font-weight-regular">/ {{ total }}</span>
        </p>
      </v-card>
    </v-col>
    <v-col cols="12" sm="6">
      <v-card color="surface" class="pa-5 border-green" border="thin">
        <div class="d-flex justify-space-between align-center mb-1">
          <span class="text-muted text-body-2">Active Players</span>
          <span class="material-symbols-outlined text-blue">person</span>
        </div>
        <p class="text-white text-h4 font-weight-bold">{{ players }}</p>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
defineProps({
  online: { type: Number, default: 3 },
  total: { type: Number, default: 5 },
  players: { type: Number, default: 42 }
})
</script>
