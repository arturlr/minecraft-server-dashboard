<template>
  <v-row>
    <v-col cols="12" sm="6">
      <div class="stat-card">
        <div class="stat-label">Servers Online</div>
        <div class="stat-value">{{ online }}<span class="stat-total">/{{ total }}</span></div>
      </div>
    </v-col>
    <v-col cols="12" sm="6">
      <div class="stat-card">
        <div class="stat-label">Active Players</div>
        <div class="stat-value">{{ players }}</div>
      </div>
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

<style scoped>
.stat-card {
  padding: 24px 0;
  border-bottom: 1px solid #e5e5e5;
}
.stat-label {
  font-size: 13px;
  font-weight: 500;
  color: #737373;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}
.stat-value {
  font-size: 36px;
  font-weight: 300;
  color: #171717;
  line-height: 1;
}
.stat-total {
  font-size: 20px;
  color: #a3a3a3;
  margin-left: 4px;
}
</style>
