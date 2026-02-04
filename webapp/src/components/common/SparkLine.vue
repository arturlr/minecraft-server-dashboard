<template>
  <svg :width="width" :height="height" class="sparkline">
    <path :d="linePath" fill="none" :stroke="color" stroke-width="1.5" />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  width: { type: Number, default: 100 },
  height: { type: Number, default: 40 },
  color: { type: String, default: '#171717' }
})

const validData = computed(() => {
  const arr = props.data || []
  return arr.filter(v => typeof v === 'number' && !isNaN(v) && isFinite(v))
})

const points = computed(() => {
  if (validData.value.length === 0) return []
  
  const values = validData.value
  const max = Math.max(...values, 1)
  const min = Math.min(...values, 0)
  const range = max - min || 1
  
  return values.map((val, i) => ({
    x: values.length === 1 ? props.width / 2 : (i / (values.length - 1)) * props.width,
    y: props.height - ((val - min) / range) * (props.height - 4) - 2
  }))
})

const linePath = computed(() => {
  if (points.value.length < 2) return ''
  return points.value.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
})
</script>

<style scoped>
.sparkline { 
  display: block;
  opacity: 0.6;
}
</style>
