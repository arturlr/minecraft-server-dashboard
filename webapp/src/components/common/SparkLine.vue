<template>
  <div class="sparkline-container">
    <svg :width="width" :height="height" class="sparkline">
      <path :d="linePath" fill="none" :stroke="color" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      <path :d="areaPath" :fill="color" fill-opacity="0.2" />
    </svg>
    <span v-if="label" class="sparkline-label text-muted">{{ label }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  width: { type: Number, default: 100 },
  height: { type: Number, default: 40 },
  color: { type: String, default: '#13ec5b' },
  label: { type: String, default: '' }
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

const areaPath = computed(() => {
  if (points.value.length < 2) return ''
  const line = points.value.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
  return `${line} L ${props.width} ${props.height} L 0 ${props.height} Z`
})
</script>

<style scoped>
.sparkline-container { 
  display: flex;
  align-items: center;
  gap: 6px;
}
.sparkline { display: block; }
.sparkline-label { 
  font-size: 10px;
  white-space: nowrap;
}
</style>
