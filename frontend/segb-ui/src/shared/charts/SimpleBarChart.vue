<template>
  <div class="chart-block">
    <h4 class="chart-title">{{ title }}</h4>
    <svg :viewBox="`0 0 ${width} ${height}`" class="chart">
      <line :x1="padding" :y1="height - padding" :x2="width - padding" :y2="height - padding" class="axis" />
      <line :x1="padding" :y1="padding" :x2="padding" :y2="height - padding" class="axis" />

      <g v-for="(bar, index) in scaledBars" :key="bar.label">
        <rect :x="bar.x" :y="bar.y" :width="bar.width" :height="bar.height" class="bar" />
        <text :x="bar.x + bar.width / 2" :y="bar.y - 6" class="value">{{ bar.value }}</text>
        <text :x="bar.x + bar.width / 2" :y="height - padding + 14" class="tick">{{ bar.label }}</text>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  title: string
  bars: Array<{ label: string; value: number }>
}>()

const width = 900
const height = 280
const padding = 40

const scaledBars = computed(() => {
  if (props.bars.length === 0) {
    return []
  }

  const maxValue = Math.max(...props.bars.map((bar) => bar.value), 1)
  const xSpan = width - padding * 2
  const ySpan = height - padding * 2
  const gap = 10
  const barWidth = Math.max(24, (xSpan - gap * (props.bars.length - 1)) / props.bars.length)

  return props.bars.map((bar, index) => {
    const heightValue = (bar.value / maxValue) * ySpan
    const x = padding + index * (barWidth + gap)
    const y = height - padding - heightValue
    return {
      ...bar,
      width: barWidth,
      x,
      y,
      height: heightValue,
    }
  })
})
</script>

<style scoped>
.chart-block {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 0.75rem;
  background: #ffffff;
}

.chart-title {
  margin: 0 0 0.4rem;
  font-size: 0.95rem;
  color: var(--ink-800);
}

.chart {
  width: 100%;
  height: auto;
}

.axis {
  stroke: #bfd6e6;
  stroke-width: 1;
}

.bar {
  fill: var(--accent);
}

.value {
  font-size: 10px;
  fill: #0f172a;
  text-anchor: middle;
}

.tick {
  font-size: 9px;
  fill: #475569;
  text-anchor: middle;
}
</style>
