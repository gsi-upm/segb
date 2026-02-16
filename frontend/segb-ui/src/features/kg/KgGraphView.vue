<template>
  <div class="stack">
    <BaseCard
      title="KG Visual Explorer"
      subtitle="Interactive graph view of the current Turtle graph with filters for time, participants, and node categories."
    >
      <div class="actions">
        <button class="btn" :disabled="loading" @click="refreshGraph">
          {{ loading ? 'Loading graph...' : 'Refresh graph' }}
        </button>
        <button class="btn ghost" :disabled="loading" @click="resetFilters">Reset filters</button>
        <button class="btn ghost" :disabled="loading || positionedNodes.length === 0" @click="resetViewport">
          Reset view
        </button>
      </div>

      <StatusBanner v-if="error" tone="error" :message="error" />
      <StatusBanner v-else-if="message" tone="info" :message="message" />

      <div class="summary">
        <div class="metric">
          <span class="metric-label">Triples</span>
          <strong>{{ graphStats.triples }}</strong>
        </div>
        <div class="metric">
          <span class="metric-label">Visible nodes</span>
          <strong>{{ graphStats.visibleNodes }}</strong>
        </div>
        <div class="metric">
          <span class="metric-label">Visible edges</span>
          <strong>{{ graphStats.visibleEdges }}</strong>
        </div>
      </div>
    </BaseCard>

    <BaseCard title="Graph Filters">
      <div class="filters-grid">
        <label class="field search-field">
          <span>Search node, literal, predicate</span>
          <input v-model="queryText" class="text-input" placeholder="emotion, Maria, hasEmotionIntensity, ..." />
        </label>

        <label class="field">
          <span>Participant</span>
          <select v-model="selectedParticipant" class="select-input">
            <option value="">All participants</option>
            <option v-for="participant in participantOptions" :key="participant.id" :value="participant.id">
              {{ participant.label }} ({{ kindLabel(participant.kind) }})
            </option>
          </select>
        </label>

        <label class="field">
          <span>From time (local)</span>
          <input v-model="timeFromLocal" type="datetime-local" class="text-input" />
        </label>

        <label class="field">
          <span>To time (local)</span>
          <input v-model="timeToLocal" type="datetime-local" class="text-input" />
        </label>

        <label class="field">
          <span>Max nodes: {{ maxNodes }}</span>
          <input v-model.number="maxNodes" type="range" min="30" max="260" step="10" />
        </label>

        <div class="field">
          <span>Options</span>
          <label class="checkbox-row">
            <input v-model="includeLiterals" type="checkbox" />
            <span>Include literal values</span>
          </label>
          <label class="checkbox-row">
            <input v-model="includeTypeEdges" type="checkbox" />
            <span>Include <code>rdf:type</code> edges</span>
          </label>
        </div>
      </div>

      <div class="kind-filter">
        <span class="kind-title">Node categories</span>
        <div class="kind-grid">
          <button
            v-for="kind in selectableKinds"
            :key="kind"
            class="kind-chip"
            :class="{ active: activeKinds.includes(kind) }"
            @click="toggleKind(kind)"
          >
            <span class="dot" :style="{ backgroundColor: KG_KIND_STYLE[kind].color }" />
            {{ KG_KIND_STYLE[kind].label }}
          </button>
        </div>
      </div>
    </BaseCard>

    <BaseCard title="Graph Canvas">
      <div v-if="positionedNodes.length === 0" class="empty">
        No nodes match current filters. Relax time/category filters or increase max nodes.
      </div>

      <div v-else class="graph-shell">
        <div
          ref="graphStage"
          class="graph-stage"
          @wheel.prevent="onWheelZoom"
          @pointerdown="onStagePointerDown"
          @pointermove="onStagePointerMove"
          @pointerup="onStagePointerUp"
          @pointercancel="onStagePointerUp"
          @pointerleave="onStagePointerUp"
        >
          <svg class="graph-svg" :viewBox="`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`" role="img" aria-label="Knowledge graph">
            <defs>
              <marker
                id="edge-arrow"
                viewBox="0 0 12 12"
                refX="10"
                refY="6"
                markerWidth="8"
                markerHeight="8"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 12 6 L 0 12 z" fill="#6f879a" />
              </marker>
            </defs>

            <g :transform="graphTransform">
              <line
                v-for="edge in positionedEdges"
                :key="edge.id"
                :x1="edge.x1"
                :y1="edge.y1"
                :x2="edge.x2"
                :y2="edge.y2"
                class="kg-edge"
                :class="{ active: isEdgeActive(edge), muted: isEdgeMuted(edge) }"
                marker-end="url(#edge-arrow)"
              />

              <g
                v-for="node in renderedNodes"
                :key="node.id"
                class="kg-node"
                :class="{
                  selected: selectedNodeId === node.id,
                  connected: isNodeConnected(node.id),
                  muted: isNodeMuted(node.id),
                }"
                @click.stop="selectNode(node.id)"
                @pointerdown.stop
              >
                <circle v-if="selectedNodeId === node.id" :cx="node.x" :cy="node.y" :r="node.r + 7" class="selected-halo" />
                <circle v-else-if="isNodeConnected(node.id)" :cx="node.x" :cy="node.y" :r="node.r + 4" class="connected-halo" />
                <circle :cx="node.x" :cy="node.y" :r="node.r" :fill="node.color" />
                <text
                  v-if="shouldShowLabel(node)"
                  :x="node.x + node.r + 4"
                  :y="node.y - node.r - 2"
                  class="node-label"
                >
                  {{ shortGraphLabel(node) }}
                </text>
              </g>
            </g>
          </svg>
        </div>

        <aside class="inspector">
          <section class="inspector-section legend-section">
            <h4>Legend</h4>
            <div class="legend-list">
              <div v-for="kind in selectableKinds" :key="kind" class="legend-item">
                <span class="dot" :style="{ backgroundColor: KG_KIND_STYLE[kind].color }" />
                <span>{{ KG_KIND_STYLE[kind].label }}</span>
              </div>
            </div>
          </section>

          <section class="inspector-section selected-section">
            <h4>Selected node</h4>
            <div v-if="selectedNode" class="selected-info">
              <p><strong>Label:</strong> {{ selectedNode.label }}</p>
              <p><strong>Kind:</strong> {{ kindLabel(selectedNode.kind) }}</p>
              <p><strong>ID:</strong> <code>{{ selectedNode.id }}</code></p>
              <p v-if="selectedNode.types.length > 0"><strong>RDF types:</strong> {{ selectedNodeTypeList }}</p>
              <p v-if="selectedNode.timestamps.length > 0"><strong>Timestamps:</strong> {{ selectedNodeTimeList }}</p>
              <p><strong>Degree:</strong> {{ selectedNode.degree }}</p>
            </div>
            <p v-else class="empty-mini">Click a node to inspect its relationships.</p>
          </section>
        </aside>
      </div>
    </BaseCard>

    <div class="grid two">
      <BaseCard title="Top Predicates">
        <DataTable :columns="predicateColumns" :rows="predicateRows" :max-height="280" />
      </BaseCard>

      <BaseCard title="Selected Node Relations">
        <DataTable :columns="relationColumns" :rows="relationRows" :max-height="280" />
      </BaseCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'

import { getEventsTurtle } from '@/core/api/segbApi'
import { normalizeApiError } from '@/core/api/error'
import DataTable, { type TableColumn } from '@/shared/ui/DataTable.vue'
import BaseCard from '@/shared/ui/BaseCard.vue'
import StatusBanner from '@/shared/ui/StatusBanner.vue'
import { compactUri, formatUtcTimestamp } from '@/shared/utils/format'
import {
  buildFilteredGraph,
  KG_KIND_ORDER,
  KG_KIND_STYLE,
  layoutKgGraph,
  parseTurtleToKgDataset,
  type KgDataset,
  type KgEdge,
  type KgFilterOptions,
  type KgNode,
  type KgNodeKind,
} from '@/features/kg/kgGraphUtils'

const VIEW_WIDTH = 1540
const VIEW_HEIGHT = 860

const loading = ref(false)
const error = ref('')
const message = ref('')

const rawDataset = ref<KgDataset | null>(null)

const queryText = ref('')
const selectedParticipant = ref('')
const timeFromLocal = ref('')
const timeToLocal = ref('')
const includeLiterals = ref(false)
const includeTypeEdges = ref(false)
const maxNodes = ref(140)

const defaultKinds = KG_KIND_ORDER.filter((kind) => kind !== 'literal')
const activeKinds = ref<KgNodeKind[]>([...defaultKinds])

const selectableKinds = KG_KIND_ORDER

const selectedNodeId = ref('')

type PositionedEdge = KgEdge & {
  x1: number
  y1: number
  x2: number
  y2: number
}

const graphStage = ref<HTMLDivElement | null>(null)
const zoom = ref(1)
const pan = reactive({ x: 0, y: 0 })
const isPanning = ref(false)
const panPointerId = ref<number | null>(null)
const panStart = reactive({ x: 0, y: 0, panX: 0, panY: 0 })

function parseLocalDateMs(raw: string): number | null {
  if (!raw) {
    return null
  }
  const parsed = new Date(raw).getTime()
  if (Number.isNaN(parsed)) {
    return null
  }
  return parsed
}

const participantOptions = computed(() => {
  if (!rawDataset.value) {
    return [] as Array<{ id: string; label: string; kind: KgNodeKind }>
  }

  return rawDataset.value.nodes
    .filter((node) => node.kind === 'person' || node.kind === 'robot')
    .map((node) => ({ id: node.id, label: node.label, kind: node.kind }))
    .sort((left, right) => left.label.localeCompare(right.label))
})

const filterOptions = computed<KgFilterOptions>(() => ({
  query: queryText.value,
  participantId: selectedParticipant.value,
  includeLiterals: includeLiterals.value,
  includeTypeEdges: includeTypeEdges.value,
  selectedKinds: new Set(activeKinds.value),
  timeFromMs: parseLocalDateMs(timeFromLocal.value),
  timeToMs: parseLocalDateMs(timeToLocal.value),
  maxNodes: Math.max(30, maxNodes.value),
}))

const filteredGraph = computed(() => {
  if (!rawDataset.value) {
    return {
      nodes: [] as KgNode[],
      edges: [] as KgEdge[],
      predicateCounts: [] as Array<{ predicate: string; count: number }>,
    }
  }
  return buildFilteredGraph(rawDataset.value, filterOptions.value)
})

const positionedNodes = computed(() =>
  layoutKgGraph(filteredGraph.value.nodes, filteredGraph.value.edges, VIEW_WIDTH, VIEW_HEIGHT),
)

const nodeById = computed(() => new Map(positionedNodes.value.map((node) => [node.id, node])))

const positionedEdges = computed<PositionedEdge[]>(() => {
  const nodeMap = nodeById.value
  const edges: PositionedEdge[] = []

  for (const edge of filteredGraph.value.edges) {
    const source = nodeMap.get(edge.source)
    const target = nodeMap.get(edge.target)
    if (!source || !target) {
      continue
    }

    const dx = target.x - source.x
    const dy = target.y - source.y
    const dist = Math.hypot(dx, dy) || 1
    const ux = dx / dist
    const uy = dy / dist

    edges.push({
      ...edge,
      x1: source.x + ux * source.r,
      y1: source.y + uy * source.r,
      x2: target.x - ux * (target.r + 3),
      y2: target.y - uy * (target.r + 3),
    })
  }

  return edges
})

const graphTransform = computed(() => `translate(${pan.x} ${pan.y}) scale(${zoom.value})`)

const graphStats = computed(() => ({
  triples: rawDataset.value?.triples ?? 0,
  visibleNodes: positionedNodes.value.length,
  visibleEdges: positionedEdges.value.length,
}))

const selectedNode = computed(() => nodeById.value.get(selectedNodeId.value) ?? null)

const selectedNodeTypeList = computed(() => {
  if (!selectedNode.value) {
    return ''
  }
  return selectedNode.value.types.map((item) => compactUri(item)).join(', ')
})

const selectedNodeTimeList = computed(() => {
  if (!selectedNode.value) {
    return ''
  }
  return selectedNode.value.timestamps
    .map((timeMs) => formatUtcTimestamp(new Date(timeMs).toISOString()))
    .join(' | ')
})

const neighborSet = computed(() => {
  const selectedId = selectedNodeId.value
  const output = new Set<string>()
  if (!selectedId) {
    return output
  }

  output.add(selectedId)
  for (const edge of positionedEdges.value) {
    if (edge.source === selectedId) {
      output.add(edge.target)
    }
    if (edge.target === selectedId) {
      output.add(edge.source)
    }
  }
  return output
})

const focusedLabelSet = computed(() => {
  const selectedId = selectedNodeId.value
  const output = new Set<string>()
  if (!selectedId) {
    return output
  }

  output.add(selectedId)

  const neighbors = positionedEdges.value
    .filter((edge) => edge.source === selectedId || edge.target === selectedId)
    .map((edge) => (edge.source === selectedId ? edge.target : edge.source))
    .map((id) => nodeById.value.get(id))
    .filter((node): node is NonNullable<typeof node> => Boolean(node))
    .sort((left, right) => right.degree - left.degree)
    .slice(0, 10)

  for (const neighbor of neighbors) {
    output.add(neighbor.id)
  }
  return output
})

const showPersonRobotLabels = computed(() => positionedNodes.value.length <= 90 || zoom.value >= 1)

const renderedNodes = computed(() => {
  const selectedId = selectedNodeId.value
  const neighbors = neighborSet.value
  return [...positionedNodes.value].sort((left, right) => {
    const rank = (id: string): number => {
      if (!selectedId) {
        return 0
      }
      if (id === selectedId) {
        return 3
      }
      if (neighbors.has(id)) {
        return 2
      }
      return 1
    }

    const rankDelta = rank(left.id) - rank(right.id)
    if (rankDelta !== 0) {
      return rankDelta
    }
    return left.degree - right.degree
  })
})

const predicateColumns: TableColumn[] = [
  { key: 'predicate', label: 'Predicate' },
  { key: 'count', label: 'Count' },
]

const relationColumns: TableColumn[] = [
  { key: 'direction', label: 'Direction' },
  { key: 'predicate', label: 'Predicate' },
  { key: 'node', label: 'Connected Node' },
  { key: 'kind', label: 'Kind' },
]

const predicateRows = computed(() =>
  filteredGraph.value.predicateCounts.slice(0, 14).map((row) => ({
    predicate: row.predicate,
    count: row.count,
  })),
)

const relationRows = computed(() => {
  if (!selectedNode.value) {
    return []
  }

  const currentId = selectedNode.value.id
  const nodeMap = nodeById.value
  const rows: Array<{ direction: string; predicate: string; node: string; kind: string }> = []

  for (const edge of positionedEdges.value) {
    if (edge.source !== currentId && edge.target !== currentId) {
      continue
    }

    const connectedId = edge.source === currentId ? edge.target : edge.source
    const connectedNode = nodeMap.get(connectedId)

    rows.push({
      direction: edge.source === currentId ? 'outgoing' : 'incoming',
      predicate: edge.predicateLabel,
      node: connectedNode?.label ?? connectedId,
      kind: connectedNode ? kindLabel(connectedNode.kind) : 'Unknown',
    })
  }

  return rows.sort((left, right) => left.predicate.localeCompare(right.predicate))
})

function kindLabel(kind: KgNodeKind): string {
  return KG_KIND_STYLE[kind].label
}

function toggleKind(kind: KgNodeKind): void {
  if (activeKinds.value.includes(kind)) {
    activeKinds.value = activeKinds.value.filter((item) => item !== kind)
    return
  }
  activeKinds.value = [...activeKinds.value, kind]
}

function resetFilters(): void {
  queryText.value = ''
  selectedParticipant.value = ''
  timeFromLocal.value = ''
  timeToLocal.value = ''
  includeLiterals.value = false
  includeTypeEdges.value = false
  maxNodes.value = 140
  activeKinds.value = [...defaultKinds]
}

function resetViewport(): void {
  zoom.value = 1
  pan.x = 0
  pan.y = 0
}

async function refreshGraph(): Promise<void> {
  loading.value = true
  error.value = ''
  message.value = ''

  try {
    const turtle = await getEventsTurtle()
    rawDataset.value = parseTurtleToKgDataset(turtle)
    message.value = `Loaded ${rawDataset.value.triples} triples from /events.`
  } catch (unknownError) {
    error.value = normalizeApiError(unknownError).message
  } finally {
    loading.value = false
  }
}

function selectNode(nodeId: string): void {
  selectedNodeId.value = selectedNodeId.value === nodeId ? '' : nodeId
}

function shortGraphLabel(node: KgNode): string {
  let label = node.label.trim()

  if (node.termType === 'literal') {
    label = 'Literal value'
  } else if (label.length > 28 || /\s{2,}|[_.]{2,}/.test(label)) {
    label = compactUri(node.id) || label
  }

  const compact = label.replace(/\s+/g, ' ').trim()
  if (compact.length <= 22) {
    return compact
  }
  return `${compact.slice(0, 19)}...`
}

function shouldShowLabel(node: KgNode): boolean {
  if (selectedNodeId.value) {
    return focusedLabelSet.value.has(node.id)
  }
  if (node.kind === 'person' || node.kind === 'robot') {
    return true
  }
  if (showPersonRobotLabels.value && node.degree >= 5 && node.kind !== 'literal') {
    return true
  }
  return false
}

function isNodeConnected(nodeId: string): boolean {
  if (!selectedNodeId.value || nodeId === selectedNodeId.value) {
    return false
  }
  return neighborSet.value.has(nodeId)
}

function isNodeMuted(nodeId: string): boolean {
  if (!selectedNodeId.value) {
    return false
  }
  return !neighborSet.value.has(nodeId)
}

function isEdgeActive(edge: PositionedEdge): boolean {
  if (!selectedNodeId.value) {
    return false
  }
  return edge.source === selectedNodeId.value || edge.target === selectedNodeId.value
}

function isEdgeMuted(edge: PositionedEdge): boolean {
  if (!selectedNodeId.value) {
    return false
  }
  return !isEdgeActive(edge)
}

function onWheelZoom(event: WheelEvent): void {
  const stage = graphStage.value
  if (!stage) {
    return
  }

  const rect = stage.getBoundingClientRect()
  const pointerX = event.clientX - rect.left
  const pointerY = event.clientY - rect.top
  const scaleFactor = event.deltaY < 0 ? 1.1 : 0.9
  const nextZoom = Math.min(2.8, Math.max(0.38, zoom.value * scaleFactor))

  const worldX = (pointerX - pan.x) / zoom.value
  const worldY = (pointerY - pan.y) / zoom.value
  pan.x = pointerX - worldX * nextZoom
  pan.y = pointerY - worldY * nextZoom
  zoom.value = nextZoom
}

function onStagePointerDown(event: PointerEvent): void {
  const stage = graphStage.value
  if (!stage) {
    return
  }
  if ((event.target as HTMLElement).closest('.kg-node')) {
    return
  }

  isPanning.value = true
  panPointerId.value = event.pointerId
  panStart.x = event.clientX
  panStart.y = event.clientY
  panStart.panX = pan.x
  panStart.panY = pan.y
  stage.setPointerCapture(event.pointerId)
}

function onStagePointerMove(event: PointerEvent): void {
  if (!isPanning.value || panPointerId.value !== event.pointerId) {
    return
  }

  pan.x = panStart.panX + (event.clientX - panStart.x)
  pan.y = panStart.panY + (event.clientY - panStart.y)
}

function onStagePointerUp(event: PointerEvent): void {
  const stage = graphStage.value
  if (!stage || !isPanning.value || panPointerId.value !== event.pointerId) {
    return
  }

  isPanning.value = false
  panPointerId.value = null
  if (stage.hasPointerCapture(event.pointerId)) {
    stage.releasePointerCapture(event.pointerId)
  }
}

watch(includeLiterals, (enabled) => {
  if (enabled && !activeKinds.value.includes('literal')) {
    activeKinds.value = [...activeKinds.value, 'literal']
  }
  if (!enabled && activeKinds.value.includes('literal')) {
    activeKinds.value = activeKinds.value.filter((kind) => kind !== 'literal')
  }
})

watch(participantOptions, (options) => {
  if (!selectedParticipant.value) {
    return
  }
  if (!options.some((option) => option.id === selectedParticipant.value)) {
    selectedParticipant.value = ''
  }
})

watch(
  positionedNodes,
  (nodes) => {
    if (nodes.length === 0) {
      selectedNodeId.value = ''
      return
    }
    if (selectedNodeId.value && !nodes.some((node) => node.id === selectedNodeId.value)) {
      selectedNodeId.value = ''
    }
  },
  { immediate: true },
)

onMounted(() => {
  void refreshGraph()
})
</script>

<style scoped>
.stack {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.6rem;
}

.metric {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.55rem 0.65rem;
  background: var(--surface-alt);
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.metric-label {
  font-size: 0.78rem;
  color: var(--ink-600);
}

.metric strong {
  font-size: 1.08rem;
  color: var(--ink-900);
}

.filters-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.7rem;
}

.search-field {
  grid-column: 1 / -1;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.9rem;
  color: var(--ink-700);
}

.text-input,
.select-input {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.58rem 0.62rem;
  font: inherit;
}

.checkbox-row {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.86rem;
}

.kind-filter {
  display: flex;
  flex-direction: column;
  gap: 0.42rem;
}

.kind-title {
  font-size: 0.86rem;
  color: var(--ink-700);
  font-weight: 680;
}

.kind-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.kind-chip {
  border: 1px solid var(--border);
  border-radius: 999px;
  background: #ffffff;
  color: var(--ink-700);
  padding: 0.28rem 0.55rem;
  font-size: 0.8rem;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.kind-chip.active {
  border-color: #8ccfeb;
  background: #e6f4fc;
  color: #005c8e;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.graph-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 290px;
  gap: 0.85rem;
  min-width: 0;
}

.graph-stage {
  border: 1px solid var(--border);
  border-radius: 12px;
  background:
    radial-gradient(circle at 8% -12%, rgba(0, 169, 224, 0.16), transparent 44%),
    radial-gradient(circle at 94% 8%, rgba(99, 102, 241, 0.12), transparent 34%),
    linear-gradient(180deg, #ffffff, #f8fbff 58%, #f3f8fd);
  min-height: 640px;
  overflow: hidden;
  touch-action: none;
  cursor: grab;
}

.graph-stage:active {
  cursor: grabbing;
}

.graph-svg {
  width: 100%;
  height: 640px;
  display: block;
}

.kg-edge {
  stroke: #5d7388;
  stroke-width: 1.35;
  opacity: 0.56;
}

.kg-edge.active {
  stroke: #0b66a8;
  opacity: 1;
  stroke-width: 2.5;
}

.kg-edge.muted {
  opacity: 0.1;
}

.kg-node {
  cursor: pointer;
}

.selected-halo {
  fill: rgba(11, 102, 168, 0.2);
  stroke: rgba(11, 102, 168, 0.75);
  stroke-width: 2.2;
}

.connected-halo {
  fill: rgba(14, 165, 233, 0.12);
  stroke: rgba(14, 165, 233, 0.45);
  stroke-width: 1.5;
}

.kg-node circle {
  stroke: rgba(255, 255, 255, 0.98);
  stroke-width: 1.55;
  filter: drop-shadow(0 1px 2px rgba(15, 23, 42, 0.2));
}

.kg-node.selected circle {
  stroke: #0f172a;
  stroke-width: 2.7;
}

.kg-node.muted {
  opacity: 0.16;
}

.node-label {
  font-size: 11px;
  fill: #1b3043;
  font-weight: 700;
  paint-order: stroke;
  stroke: rgba(255, 255, 255, 0.97);
  stroke-width: 2.6;
  stroke-linejoin: round;
}

.inspector {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 0.7rem;
  background: #f8fcff;
  overflow: auto;
}

.inspector h4 {
  margin: 0.1rem 0 0.45rem;
  font-size: 0.92rem;
  color: var(--ink-800);
}

.inspector-section + .inspector-section {
  margin-top: 1rem;
  padding-top: 0.95rem;
  border-top: 1px solid #d8e7f2;
}

.legend-list {
  display: grid;
  gap: 0.28rem;
  margin-bottom: 0.1rem;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.84rem;
  color: var(--ink-700);
}

.selected-info p {
  margin: 0 0 0.45rem;
  font-size: 0.84rem;
  color: var(--ink-700);
  line-height: 1.4;
}

.selected-info code {
  background: #e8f4fc;
  padding: 0.05rem 0.25rem;
  border-radius: 6px;
  font-size: 0.78rem;
  word-break: break-all;
}

.empty,
.empty-mini {
  color: var(--ink-600);
  font-size: 0.9rem;
}

.grid.two {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
}

@media (max-width: 1320px) {
  .graph-shell {
    grid-template-columns: 1fr;
  }

  .inspector {
    max-height: 260px;
  }
}

@media (max-width: 980px) {
  .filters-grid {
    grid-template-columns: 1fr;
  }

  .grid.two,
  .summary {
    grid-template-columns: 1fr;
  }

  .graph-stage,
  .graph-svg {
    min-height: 540px;
    height: 540px;
  }
}
</style>
