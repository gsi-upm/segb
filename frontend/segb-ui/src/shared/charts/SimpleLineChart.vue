<template>
  <div class="chart-block">
    <h4 class="chart-title">{{ title }}</h4>

    <div class="legend">
      <div v-for="item in legendItems" :key="item.key" class="legend-item">
        <span class="legend-swatch" :style="{ backgroundColor: item.color }" />
        <span>{{ item.label }}</span>
      </div>
    </div>

    <div
      ref="scrollEl"
      class="chart-scroll"
      @scroll="hidePointTooltip"
      @wheel="onWheelScroll"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
      @pointerleave="onPointerUp"
    >
      <div class="chart-canvas" :style="chartCanvasStyle">
        <svg :width="chartWidth" :height="height" :viewBox="`0 0 ${chartWidth} ${height}`" class="chart">
          <g v-for="tick in yTicks" :key="tick.label">
            <line :x1="paddingLeft" :y1="tick.y" :x2="chartWidth - paddingRight" :y2="tick.y" class="grid-line" />
            <text :x="paddingLeft - 10" :y="tick.y + 4" class="y-tick">{{ tick.label }}</text>
          </g>

          <line :x1="paddingLeft" :y1="height - paddingBottom" :x2="chartWidth - paddingRight" :y2="height - paddingBottom" class="axis" />
          <line :x1="paddingLeft" :y1="paddingTop" :x2="paddingLeft" :y2="height - paddingBottom" class="axis" />

          <polyline :points="polylinePoints" class="line" />

          <g v-for="(point, idx) in scaledPoints" :key="idx">
            <circle
              class="point-dot"
              :cx="point.x"
              :cy="point.plotY"
              :r="pointRadius"
              :fill="emotionStyle(point.tag).color"
              @pointerenter="onPointPointerEnter($event, point)"
              @pointermove="onPointPointerMove($event)"
              @pointerleave="hidePointTooltip"
              @pointercancel="hidePointTooltip"
            />
            <text :x="point.x" :y="height - paddingBottom + 16" class="tick">
              <tspan :x="point.x">{{ splitTickLabel(point.xLabel)[0] }}</tspan>
              <tspan v-if="splitTickLabel(point.xLabel)[1]" :x="point.x" dy="11">
                {{ splitTickLabel(point.xLabel)[1] }}
              </tspan>
            </text>
          </g>

          <text :x="chartWidth / 2" :y="height - 8" class="axis-title x-axis-title">Timestamp (UTC)</text>
          <text
            :x="yAxisTitleX"
            :y="height / 2"
            class="axis-title y-axis-title"
            :transform="`rotate(-90 ${yAxisTitleX} ${height / 2})`"
          >
            Emotion intensity (%)
          </text>
        </svg>
      </div>
    </div>

    <div
      v-if="tooltip.visible"
      class="point-tooltip"
      :style="{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }"
      role="tooltip"
    >
      <div v-for="(line, index) in tooltip.lines" :key="index">{{ line }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { formatRatioAsPercent } from '@/shared/utils/format'

export type LinePoint = {
  xLabel: string
  y: number
  tag: string
  activity?: string
  trigger?: string
  confidence?: number | null
}

type EmotionLegendItem = {
  key: string
  label: string
  color: string
}

const props = defineProps<{
  title: string
  points: LinePoint[]
  yMax?: number
}>()

const height = 420
const paddingTop = 24
const paddingRight = 74
const paddingBottom = 106
const paddingLeft = 74
const yAxisTitleX = 18
const minPointSpacing = 130
const pointRadius = 9.2

const INSIDE_OUT_PALETTE = {
  joy: { key: 'joy', label: 'Joy', color: '#facc15' },
  sadness: { key: 'sadness', label: 'Sadness', color: '#2563eb' },
  anger: { key: 'anger', label: 'Anger', color: '#dc2626' },
  fear: { key: 'fear', label: 'Fear', color: '#9333ea' },
  disgust: { key: 'disgust', label: 'Disgust', color: '#16a34a' },
  surprise: { key: 'surprise', label: 'Surprise', color: '#60a5fa' },
} satisfies Record<string, EmotionLegendItem>

type EmotionKey = keyof typeof INSIDE_OUT_PALETTE

const legendOrder: EmotionKey[] = [
  'joy',
  'sadness',
  'anger',
  'fear',
  'disgust',
  'surprise',
]

const safeYMax = computed(() => {
  const maxData = props.points.reduce((max, point) => Math.max(max, point.y), 0)
  return Math.max(props.yMax ?? 1, maxData, 1)
})

function normalizeEmotionKey(tag: string): EmotionKey {
  const normalized = tag.trim().toLowerCase()
  if (normalized.includes('happiness') || normalized.includes('joy') || normalized.includes('alegr')) return 'joy'
  if (normalized.includes('sad') || normalized.includes('triste')) return 'sadness'
  if (normalized.includes('anger') || normalized.includes('ira')) return 'anger'
  if (normalized.includes('fear') || normalized.includes('miedo')) return 'fear'
  if (normalized.includes('anxiety') || normalized.includes('ansiedad')) return 'fear'
  if (normalized.includes('disgust') || normalized.includes('desagrado')) return 'disgust'
  if (normalized.includes('surprise') || normalized.includes('sorpresa')) return 'surprise'
  return 'surprise'
}

function emotionStyle(tag: string): EmotionLegendItem {
  return INSIDE_OUT_PALETTE[normalizeEmotionKey(tag)]
}

function splitTickLabel(value: string): [string, string?] {
  const [first = value, second] = value.split(', ', 2)
  if (second) {
    return [first, second]
  }
  return [value]
}

function pointTooltipLines(point: LinePoint): string[] {
  const lines = [
    `Emotion: ${point.tag}`,
    `Intensity: ${formatRatioAsPercent(point.y, 0)}`,
    `Timestamp: ${point.xLabel} UTC`,
  ]
  if (point.trigger && point.trigger.trim().length > 0) {
    lines.push(`Trigger: ${point.trigger}`)
  }
  if (point.activity && point.activity.trim().length > 0) {
    lines.push(`Analysis activity: ${point.activity}`)
  }
  if (typeof point.confidence === 'number') {
    lines.push(`Confidence: ${formatRatioAsPercent(point.confidence, 0)}`)
  }
  return lines
}

const chartWidth = computed(() => {
  const pointCount = Math.max(props.points.length, 2)
  const maxLabelLength = props.points.reduce((max, point) => Math.max(max, point.xLabel.length), 0)
  const dynamicSpacing = Math.max(minPointSpacing, Math.min(260, maxLabelLength * 8))
  const requiredWidth = paddingLeft + paddingRight + (pointCount - 1) * dynamicSpacing
  return Math.max(containerWidth.value, requiredWidth)
})

const chartCanvasStyle = computed(() => ({
  width: `${chartWidth.value}px`,
}))

const yTicks = computed(() => {
  const steps = 4
  return Array.from({ length: steps }, (_, index) => index + 1)
    .map((step) => {
      const value = (safeYMax.value / steps) * step
      const ratio = safeYMax.value === 0 ? 0 : value / safeYMax.value
      const y = height - paddingBottom - ratio * (height - paddingTop - paddingBottom)
      return { value, y, label: formatRatioAsPercent(value, 0) }
    })
    .filter((tick) => tick.value > 0)
})

type ScaledPoint = LinePoint & { x: number; plotY: number }

const scaledPoints = computed<ScaledPoint[]>(() => {
  if (props.points.length === 0) {
    return []
  }

  const xSpan = chartWidth.value - paddingLeft - paddingRight
  const ySpan = height - paddingTop - paddingBottom

  return props.points.map((point, index) => {
    const x =
      props.points.length === 1
        ? chartWidth.value / 2
        : paddingLeft + (index / (props.points.length - 1)) * xSpan
    const plotY = height - paddingBottom - (Math.max(Math.min(point.y, safeYMax.value), 0) / safeYMax.value) * ySpan
    return {
      ...point,
      x,
      plotY,
    }
  })
})

const polylinePoints = computed(() => scaledPoints.value.map((point) => `${point.x},${point.plotY}`).join(' '))

const legendItems = computed<EmotionLegendItem[]>(() => legendOrder.map((key) => INSIDE_OUT_PALETTE[key]))

const scrollEl = ref<HTMLDivElement | null>(null)
const containerWidth = ref(0)
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartLeft = ref(0)
const tooltip = ref<{ visible: boolean; x: number; y: number; lines: string[] }>({
  visible: false,
  x: 0,
  y: 0,
  lines: [],
})
let resizeObserver: ResizeObserver | null = null

function updateTooltipPosition(clientX: number, clientY: number): void {
  const margin = 12
  const estimatedWidth = 340
  const estimatedHeight = Math.max(88, tooltip.value.lines.length * 22)
  let x = clientX + margin
  let y = clientY + margin

  if (typeof window !== 'undefined') {
    if (x + estimatedWidth > window.innerWidth - 8) {
      x = Math.max(8, clientX - estimatedWidth - margin)
    }
    if (y + estimatedHeight > window.innerHeight - 8) {
      y = Math.max(8, clientY - estimatedHeight - margin)
    }
  }

  tooltip.value.x = x
  tooltip.value.y = y
}

function onPointPointerEnter(event: PointerEvent, point: LinePoint): void {
  tooltip.value.lines = pointTooltipLines(point)
  tooltip.value.visible = true
  updateTooltipPosition(event.clientX, event.clientY)
}

function onPointPointerMove(event: PointerEvent): void {
  if (!tooltip.value.visible) {
    return
  }
  updateTooltipPosition(event.clientX, event.clientY)
}

function hidePointTooltip(): void {
  tooltip.value.visible = false
}

function updateContainerWidth(): void {
  const container = scrollEl.value
  if (!container) {
    return
  }
  containerWidth.value = container.clientWidth
}

onMounted(() => {
  updateContainerWidth()
  window.addEventListener('resize', updateContainerWidth)
  if (typeof ResizeObserver !== 'undefined' && scrollEl.value) {
    resizeObserver = new ResizeObserver(() => updateContainerWidth())
    resizeObserver.observe(scrollEl.value)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateContainerWidth)
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})

function onWheelScroll(event: WheelEvent): void {
  const container = scrollEl.value
  if (!container) {
    return
  }
  if (container.scrollWidth <= container.clientWidth) {
    return
  }

  event.preventDefault()
  const delta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY
  container.scrollLeft += delta
}

function onPointerDown(event: PointerEvent): void {
  hidePointTooltip()
  const container = scrollEl.value
  if (!container || container.scrollWidth <= container.clientWidth) {
    return
  }
  isDragging.value = true
  dragStartX.value = event.clientX
  dragStartLeft.value = container.scrollLeft
  container.setPointerCapture(event.pointerId)
}

function onPointerMove(event: PointerEvent): void {
  const container = scrollEl.value
  if (!container || !isDragging.value) {
    return
  }
  const delta = event.clientX - dragStartX.value
  container.scrollLeft = dragStartLeft.value - delta
}

function onPointerUp(event: PointerEvent): void {
  const container = scrollEl.value
  if (!container || !isDragging.value) {
    return
  }
  isDragging.value = false
  if (container.hasPointerCapture(event.pointerId)) {
    container.releasePointerCapture(event.pointerId)
  }
}
</script>

<style scoped>
.chart-block {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 0.75rem;
  background: #ffffff;
  width: 100%;
  min-width: 0;
  overflow: hidden;
}

.chart-title {
  margin: 0 0 0.25rem;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--ink-800);
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.42rem 0.8rem;
  margin-bottom: 0.65rem;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 1rem;
  color: var(--ink-700);
}

.legend-swatch {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
}

.chart-scroll {
  overflow-x: auto;
  overflow-y: hidden;
  width: 100%;
  max-width: 100%;
  -webkit-overflow-scrolling: touch;
  scrollbar-gutter: stable;
  padding-bottom: 0.25rem;
  cursor: grab;
  touch-action: pan-x;
}

.chart-scroll:active {
  cursor: grabbing;
}

.chart-canvas {
  min-width: 0;
}

.chart-scroll::-webkit-scrollbar {
  height: 12px;
}

.chart-scroll::-webkit-scrollbar-track {
  background: #e2e8f0;
  border-radius: 999px;
}

.chart-scroll::-webkit-scrollbar-thumb {
  background: #94a3b8;
  border-radius: 999px;
}

.chart {
  display: block;
}

.grid-line {
  stroke: #e2e8f0;
  stroke-width: 1;
}

.axis {
  stroke: #64748b;
  stroke-width: 2.2;
}

.line {
  fill: none;
  stroke: #64748b;
  stroke-width: 2.6;
}

.point-dot {
  cursor: pointer;
}

.tick {
  font-size: 14.5px;
  text-anchor: middle;
  fill: #475569;
  font-weight: 600;
}

.y-tick {
  font-size: 14.5px;
  text-anchor: end;
  fill: #475569;
  font-weight: 700;
}

.axis-title {
  font-size: 17px;
  fill: #334155;
  font-weight: 800;
}

.x-axis-title {
  text-anchor: middle;
}

.y-axis-title {
  text-anchor: middle;
}

.point-tooltip {
  position: fixed;
  z-index: 1200;
  pointer-events: none;
  background: rgba(15, 23, 42, 0.96);
  color: #f8fafc;
  border: 1px solid rgba(148, 163, 184, 0.55);
  border-radius: 8px;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.3);
  padding: 0.45rem 0.6rem;
  max-width: min(360px, calc(100vw - 16px));
  font-size: 0.82rem;
  line-height: 1.35;
}
</style>
