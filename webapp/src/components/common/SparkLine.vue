<template>
  <div class="sparkline-container" @mousemove="handleMouseMove" @mouseleave="handleMouseLeave">
    <svg :width="width" :height="height" class="sparkline">
      <path :d="linePath" fill="none" :stroke="color" stroke-width="1.5" />
      <circle 
        v-if="hoveredPoint" 
        :cx="hoveredPoint.x" 
        :cy="hoveredPoint.y" 
        r="3" 
        :fill="color" 
      />
    </svg>
    <div 
      v-if="hoveredPoint" 
      class="tooltip" 
      :style="{ left: `${hoveredPoint.x}px`, top: `${hoveredPoint.y - 25}px` }"
    >
      {{ hoveredPoint.value.toFixed(1) }}
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  width: { type: Number, default: 100 },
  height: { type: Number, default: 40 },
  color: { type: String, default: '#171717' }
})

const hoveredPoint = ref(null)

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
    y: props.height - ((val - min) / range) * (props.height - 4) - 2,
    value: val
  }))
})

const linePath = computed(() => {
  if (points.value.length < 2) return ''
  return points.value.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
})

const handleMouseMove = (event) => {
  if (points.value.length === 0) return
  
  const rect = event.currentTarget.getBoundingClientRect()
  const mouseX = event.clientX - rect.left
  
  // Find closest point
  let closest = points.value[0]
  let minDist = Math.abs(mouseX - closest.x)
  
  for (const point of points.value) {
    const dist = Math.abs(mouseX - point.x)
    if (dist < minDist) {
      minDist = dist
      closest = point
    }
  }
  
  hoveredPoint.value = closest
}

const handleMouseLeave = () => {
  hoveredPoint.value = null
}
</script>

<style scoped>
.sparkline-container {
  position: relative;
  display: inline-block;
}

.sparkline { 
  display: block;
  opacity: 0.6;
}

.tooltip {
  position: absolute;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  pointer-events: none;
  white-space: nowrap;
  transform: translateX(-50%);
  z-index: 10;
}
</style>
