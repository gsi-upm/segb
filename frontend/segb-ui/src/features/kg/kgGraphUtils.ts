import { Parser } from 'n3'

import { compactUri } from '@/shared/utils/format'

const RDF_TYPE_URI = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'

const LABEL_TOKENS = new Set([
  'label',
  'hasname',
  'firstname',
  'description',
  'comment',
  'identifier',
  'hastext',
  'title',
  'name',
])

const TIME_TOKENS = new Set([
  'startedattime',
  'endedattime',
  'generatedattime',
  'observedat',
  'timestamp',
  'datecreated',
  'datemodified',
])

export type KgNodeKind =
  | 'person'
  | 'robot'
  | 'activity'
  | 'event'
  | 'message'
  | 'model'
  | 'emotion'
  | 'annotation'
  | 'state'
  | 'location'
  | 'shared'
  | 'literal'
  | 'other'

export type KgNode = {
  id: string
  label: string
  termType: 'named' | 'blank' | 'literal'
  kind: KgNodeKind
  types: string[]
  timestamps: number[]
  degree: number
  rawValue?: string
}

export type KgEdge = {
  id: string
  source: string
  target: string
  predicate: string
  predicateLabel: string
  isType: boolean
}

export type KgDataset = {
  nodes: KgNode[]
  edges: KgEdge[]
  triples: number
}

export type KgFilterOptions = {
  query: string
  participantId: string
  includeLiterals: boolean
  includeTypeEdges: boolean
  selectedKinds: Set<KgNodeKind>
  timeFromMs: number | null
  timeToMs: number | null
  maxNodes: number
}

export type KgFilteredGraph = {
  nodes: KgNode[]
  edges: KgEdge[]
  predicateCounts: Array<{ predicate: string; count: number }>
}

export type KgPositionedNode = KgNode & {
  x: number
  y: number
  r: number
  color: string
}

type QuadTerm = {
  termType: string
  value: string
}

type ParsedQuad = {
  subject: QuadTerm
  predicate: QuadTerm
  object: QuadTerm
}

type NodeBuilder = {
  id: string
  termType: 'named' | 'blank' | 'literal'
  label: string
  rawValue?: string
  types: Set<string>
  timestamps: number[]
}

export const KG_KIND_ORDER: KgNodeKind[] = [
  'person',
  'robot',
  'activity',
  'event',
  'message',
  'model',
  'emotion',
  'annotation',
  'state',
  'location',
  'shared',
  'other',
  'literal',
]

export const KG_KIND_STYLE: Record<KgNodeKind, { label: string; color: string }> = {
  person: { label: 'Person', color: '#2563eb' },
  robot: { label: 'Robot', color: '#00a9e0' },
  activity: { label: 'Activity', color: '#6366f1' },
  event: { label: 'Event', color: '#f59e0b' },
  message: { label: 'Message', color: '#14b8a6' },
  model: { label: 'Model/Dataset', color: '#8b5cf6' },
  emotion: { label: 'Emotion', color: '#ef4444' },
  annotation: { label: 'Annotation', color: '#ec4899' },
  state: { label: 'State', color: '#10b981' },
  location: { label: 'Location', color: '#84cc16' },
  shared: { label: 'Shared Context', color: '#0ea5e9' },
  other: { label: 'Other', color: '#475569' },
  literal: { label: 'Literal Value', color: '#a1a1aa' },
}

function localToken(uri: string): string {
  return compactUri(uri).replace(/[_-]/g, '').toLowerCase()
}

function shortLiteral(value: string): string {
  const compact = value.replace(/\s+/g, ' ').trim()
  if (compact.length <= 46) {
    return compact
  }
  return `${compact.slice(0, 43)}...`
}

function parseTimeMs(raw: string): number | null {
  const parsed = Date.parse(raw)
  if (Number.isNaN(parsed)) {
    return null
  }
  return parsed
}

function hashString(value: string): number {
  let hash = 2166136261
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  return hash >>> 0
}

function inferNodeKind(nodeId: string, termType: KgNode['termType'], types: Set<string>): KgNodeKind {
  if (termType === 'literal') {
    return 'literal'
  }

  const idLower = nodeId.toLowerCase()
  const typeTokens = Array.from(types).map((item) => localToken(item))
  const hasType = (token: string): boolean => typeTokens.some((item) => item.includes(token))

  if (
    hasType('human') ||
    hasType('person') ||
    idLower.includes('/human/') ||
    idLower.includes('/person/')
  ) {
    return 'person'
  }

  if (hasType('robot') || idLower.includes('/robot/')) {
    return 'robot'
  }

  if (
    hasType('sharedevent') ||
    hasType('sharedcontext') ||
    idLower.includes('/shared-events/') ||
    idLower.includes('shared-event')
  ) {
    return 'shared'
  }

  if (hasType('activity') || idLower.includes('/activity/')) {
    return 'activity'
  }

  if (hasType('event') || idLower.includes('/event/')) {
    return 'event'
  }

  if (hasType('message') || idLower.includes('/message/')) {
    return 'message'
  }

  if (hasType('annotation') || idLower.includes('/annotation/')) {
    return 'annotation'
  }

  if (hasType('emotion') || idLower.includes('/emotion/')) {
    return 'emotion'
  }

  if (hasType('state') || idLower.includes('/state/')) {
    return 'state'
  }

  if (hasType('location') || idLower.includes('/location/')) {
    return 'location'
  }

  if (
    hasType('model') ||
    hasType('dataset') ||
    hasType('run') ||
    idLower.includes('/model/') ||
    idLower.includes('/dataset/')
  ) {
    return 'model'
  }

  return 'other'
}

function isLabelPredicate(uri: string): boolean {
  return LABEL_TOKENS.has(localToken(uri))
}

function isTimePredicate(uri: string): boolean {
  return TIME_TOKENS.has(localToken(uri))
}

function nodeIdFromTerm(term: QuadTerm): string {
  if (term.termType === 'NamedNode') {
    return term.value
  }
  if (term.termType === 'BlankNode') {
    return `_:${term.value}`
  }
  return term.value
}

export function parseTurtleToKgDataset(ttl: string): KgDataset {
  const parser = new Parser()
  const quads = parser.parse(ttl) as ParsedQuad[]

  const builders = new Map<string, NodeBuilder>()
  const edges: KgEdge[] = []

  function ensureResourceNode(term: QuadTerm): NodeBuilder {
    const id = nodeIdFromTerm(term)
    const existing = builders.get(id)
    if (existing) {
      return existing
    }

    const termType: KgNode['termType'] = term.termType === 'BlankNode' ? 'blank' : 'named'
    const baseLabel = termType === 'blank' ? id : compactUri(id)
    const builder: NodeBuilder = {
      id,
      termType,
      label: baseLabel || id,
      types: new Set<string>(),
      timestamps: [],
    }
    builders.set(id, builder)
    return builder
  }

  quads.forEach((quad, index) => {
    const subjectNode = ensureResourceNode(quad.subject)
    const predicateUri = quad.predicate.value

    if (predicateUri === RDF_TYPE_URI && quad.object.termType !== 'Literal') {
      subjectNode.types.add(quad.object.value)
    }

    if (quad.object.termType === 'Literal' && isLabelPredicate(predicateUri)) {
      const labelValue = quad.object.value.trim()
      if (labelValue.length > 0) {
        subjectNode.label = labelValue
      }
    }

    if (quad.object.termType === 'Literal' && isTimePredicate(predicateUri)) {
      const timeMs = parseTimeMs(quad.object.value)
      if (timeMs !== null) {
        subjectNode.timestamps.push(timeMs)
      }
    }

    let targetId = ''
    if (quad.object.termType === 'Literal') {
      targetId = `lit:${index}`
      builders.set(targetId, {
        id: targetId,
        termType: 'literal',
        label: shortLiteral(quad.object.value),
        rawValue: quad.object.value,
        types: new Set<string>(),
        timestamps: [],
      })
    } else {
      const objectNode = ensureResourceNode(quad.object)
      targetId = objectNode.id
    }

    edges.push({
      id: `edge-${index}`,
      source: subjectNode.id,
      target: targetId,
      predicate: predicateUri,
      predicateLabel: compactUri(predicateUri),
      isType: predicateUri === RDF_TYPE_URI,
    })
  })

  const degreeMap = new Map<string, number>()
  for (const edge of edges) {
    degreeMap.set(edge.source, (degreeMap.get(edge.source) ?? 0) + 1)
    degreeMap.set(edge.target, (degreeMap.get(edge.target) ?? 0) + 1)
  }

  const nodes: KgNode[] = Array.from(builders.values()).map((builder) => {
    const uniqueTimes = Array.from(new Set(builder.timestamps)).sort((a, b) => a - b)
    const kind = inferNodeKind(builder.id, builder.termType, builder.types)
    return {
      id: builder.id,
      label: builder.label,
      termType: builder.termType,
      kind,
      types: Array.from(builder.types),
      timestamps: uniqueTimes,
      degree: degreeMap.get(builder.id) ?? 0,
      rawValue: builder.rawValue,
    }
  })

  return {
    nodes,
    edges,
    triples: quads.length,
  }
}

function intersectSets(base: Set<string>, mask: Set<string>): Set<string> {
  const output = new Set<string>()
  for (const id of base) {
    if (mask.has(id)) {
      output.add(id)
    }
  }
  return output
}

function expandByHops(seed: Set<string>, edges: KgEdge[], hops: number): Set<string> {
  const visited = new Set(seed)
  let frontier = new Set(seed)

  for (let hop = 0; hop < hops; hop += 1) {
    const next = new Set<string>()
    for (const edge of edges) {
      if (frontier.has(edge.source) && !visited.has(edge.target)) {
        visited.add(edge.target)
        next.add(edge.target)
      }
      if (frontier.has(edge.target) && !visited.has(edge.source)) {
        visited.add(edge.source)
        next.add(edge.source)
      }
    }
    if (next.size === 0) {
      break
    }
    frontier = next
  }

  return visited
}

function isNodeWithinTimeRange(node: KgNode, fromMs: number | null, toMs: number | null): boolean {
  if (fromMs === null && toMs === null) {
    return true
  }
  if (node.timestamps.length === 0) {
    return false
  }

  return node.timestamps.some((timestamp) => {
    if (fromMs !== null && timestamp < fromMs) {
      return false
    }
    if (toMs !== null && timestamp > toMs) {
      return false
    }
    return true
  })
}

export function buildFilteredGraph(dataset: KgDataset, options: KgFilterOptions): KgFilteredGraph {
  const nodeById = new Map(dataset.nodes.map((node) => [node.id, node]))
  const candidateIds = new Set(dataset.nodes.map((node) => node.id))
  const edges = dataset.edges.filter((edge) => options.includeTypeEdges || !edge.isType)

  if (options.selectedKinds.size === 0) {
    return { nodes: [], edges: [], predicateCounts: [] }
  }

  if (!options.includeLiterals) {
    for (const node of dataset.nodes) {
      if (node.termType === 'literal') {
        candidateIds.delete(node.id)
      }
    }
  }

  if (options.selectedKinds.size > 0) {
    for (const node of dataset.nodes) {
      if (!options.selectedKinds.has(node.kind)) {
        candidateIds.delete(node.id)
      }
    }
  }

  if (options.timeFromMs !== null || options.timeToMs !== null) {
    const timeSeed = new Set<string>()
    for (const node of dataset.nodes) {
      if (isNodeWithinTimeRange(node, options.timeFromMs, options.timeToMs)) {
        timeSeed.add(node.id)
      }
    }

    if (timeSeed.size === 0) {
      return { nodes: [], edges: [], predicateCounts: [] }
    }

    const expanded = expandByHops(timeSeed, edges, 1)
    const narrowed = intersectSets(candidateIds, expanded)
    candidateIds.clear()
    for (const id of narrowed) {
      candidateIds.add(id)
    }
  }

  if (options.participantId) {
    const participantSeed = new Set<string>([options.participantId])
    const expanded = expandByHops(participantSeed, edges, 2)
    const narrowed = intersectSets(candidateIds, expanded)
    candidateIds.clear()
    for (const id of narrowed) {
      candidateIds.add(id)
    }
  }

  const query = options.query.trim().toLowerCase()
  if (query.length > 0) {
    const searchSeed = new Set<string>()
    for (const node of dataset.nodes) {
      const haystack = [node.label, node.id, node.rawValue ?? '', ...node.types].join(' ').toLowerCase()
      if (haystack.includes(query)) {
        searchSeed.add(node.id)
      }
    }

    for (const edge of edges) {
      if (
        edge.predicateLabel.toLowerCase().includes(query) ||
        edge.predicate.toLowerCase().includes(query)
      ) {
        searchSeed.add(edge.source)
        searchSeed.add(edge.target)
      }
    }

    if (searchSeed.size === 0) {
      return { nodes: [], edges: [], predicateCounts: [] }
    }

    const expanded = expandByHops(searchSeed, edges, 1)
    const narrowed = intersectSets(candidateIds, expanded)
    candidateIds.clear()
    for (const id of narrowed) {
      candidateIds.add(id)
    }
  }

  let filteredEdges = edges.filter((edge) => candidateIds.has(edge.source) && candidateIds.has(edge.target))

  if (candidateIds.size > options.maxNodes) {
    const scoreMap = new Map<string, number>()
    for (const edge of filteredEdges) {
      scoreMap.set(edge.source, (scoreMap.get(edge.source) ?? 0) + 1)
      scoreMap.set(edge.target, (scoreMap.get(edge.target) ?? 0) + 1)
    }

    const ranked = Array.from(candidateIds).sort((leftId, rightId) => {
      const leftNode = nodeById.get(leftId)
      const rightNode = nodeById.get(rightId)
      const leftScore = scoreMap.get(leftId) ?? 0
      const rightScore = scoreMap.get(rightId) ?? 0
      const leftBoost = leftNode && (leftNode.kind === 'person' || leftNode.kind === 'robot') ? 3 : 0
      const rightBoost = rightNode && (rightNode.kind === 'person' || rightNode.kind === 'robot') ? 3 : 0
      const delta = rightScore + rightBoost - (leftScore + leftBoost)
      if (delta !== 0) {
        return delta
      }
      return leftId.localeCompare(rightId)
    })

    const keep = new Set<string>(ranked.slice(0, options.maxNodes))
    filteredEdges = filteredEdges.filter((edge) => keep.has(edge.source) && keep.has(edge.target))
    candidateIds.clear()
    for (const id of keep) {
      candidateIds.add(id)
    }
  }

  const degreeMap = new Map<string, number>()
  for (const edge of filteredEdges) {
    degreeMap.set(edge.source, (degreeMap.get(edge.source) ?? 0) + 1)
    degreeMap.set(edge.target, (degreeMap.get(edge.target) ?? 0) + 1)
  }

  const filteredNodes = dataset.nodes
    .filter((node) => candidateIds.has(node.id))
    .map((node) => ({
      ...node,
      degree: degreeMap.get(node.id) ?? 0,
    }))
    .sort((left, right) => right.degree - left.degree || left.label.localeCompare(right.label))

  const predicateCounters = new Map<string, number>()
  for (const edge of filteredEdges) {
    predicateCounters.set(edge.predicateLabel, (predicateCounters.get(edge.predicateLabel) ?? 0) + 1)
  }

  const predicateCounts = Array.from(predicateCounters.entries())
    .map(([predicate, count]) => ({ predicate, count }))
    .sort((left, right) => right.count - left.count)

  return {
    nodes: filteredNodes,
    edges: filteredEdges,
    predicateCounts,
  }
}

export function layoutKgGraph(
  nodes: KgNode[],
  edges: KgEdge[],
  width: number,
  height: number,
): KgPositionedNode[] {
  if (nodes.length === 0) {
    return []
  }

  const centerX = width / 2
  const centerY = height / 2
  const kindIndex = new Map(KG_KIND_ORDER.map((kind, index) => [kind, index]))
  const positions = nodes.map((node) => ({
    id: node.id,
    x: centerX,
    y: centerY,
    dx: 0,
    dy: 0,
  }))

  const grouped = new Map<KgNodeKind, KgNode[]>()
  for (const node of nodes) {
    const bucket = grouped.get(node.kind) ?? []
    bucket.push(node)
    grouped.set(node.kind, bucket)
  }

  const maxRadius = Math.min(width, height) * 0.42
  const minRadius = Math.min(width, height) * 0.18
  const ringStep = (maxRadius - minRadius) / Math.max(KG_KIND_ORDER.length - 1, 1)

  for (const kind of KG_KIND_ORDER) {
    const bucket = grouped.get(kind) ?? []
    if (bucket.length === 0) {
      continue
    }
    const ring = minRadius + (kindIndex.get(kind) ?? 0) * ringStep
    bucket
      .sort((left, right) => left.id.localeCompare(right.id))
      .forEach((node, index) => {
        const target = positions.find((item) => item.id === node.id)
        if (!target) {
          return
        }
        const phase = ((kindIndex.get(kind) ?? 0) * 0.37) % (Math.PI * 2)
        const angle = phase + (Math.PI * 2 * index) / bucket.length
        const jitter = ((hashString(node.id) % 1000) / 1000 - 0.5) * 22
        target.x = centerX + Math.cos(angle) * (ring + jitter)
        target.y = centerY + Math.sin(angle) * (ring + jitter)
      })
  }

  const nodeIndexById = new Map(nodes.map((node, index) => [node.id, index]))
  const edgePairs = edges
    .map((edge) => {
      const sourceIndex = nodeIndexById.get(edge.source)
      const targetIndex = nodeIndexById.get(edge.target)
      if (sourceIndex === undefined || targetIndex === undefined) {
        return null
      }
      return [sourceIndex, targetIndex] as const
    })
    .filter((pair): pair is readonly [number, number] => pair !== null)

  const repulsion = 9200
  const edgeAttraction = 0.13
  const idealLength = Math.min(width, height) * 0.14
  let temperature = Math.min(width, height) * 0.06
  const padding = 56
  const iterations = Math.min(70, 34 + nodes.length)

  for (let iteration = 0; iteration < iterations; iteration += 1) {
    for (const position of positions) {
      position.dx = 0
      position.dy = 0
    }

    for (let left = 0; left < positions.length; left += 1) {
      for (let right = left + 1; right < positions.length; right += 1) {
        const leftPos = positions[left]
        const rightPos = positions[right]
        if (!leftPos || !rightPos) {
          continue
        }
        const dx = leftPos.x - rightPos.x
        const dy = leftPos.y - rightPos.y
        const dist = Math.hypot(dx, dy) + 0.01
        const force = repulsion / (dist * dist)
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force
        leftPos.dx += fx
        leftPos.dy += fy
        rightPos.dx -= fx
        rightPos.dy -= fy
      }
    }

    for (const [sourceIndex, targetIndex] of edgePairs) {
      const source = positions[sourceIndex]
      const target = positions[targetIndex]
      if (!source || !target) {
        continue
      }
      const dx = source.x - target.x
      const dy = source.y - target.y
      const dist = Math.hypot(dx, dy) + 0.01
      const force = (dist - idealLength) * edgeAttraction
      const fx = (dx / dist) * force
      const fy = (dy / dist) * force
      source.dx -= fx
      source.dy -= fy
      target.dx += fx
      target.dy += fy
    }

    for (const position of positions) {
      position.dx += (centerX - position.x) * 0.006
      position.dy += (centerY - position.y) * 0.006
      const disp = Math.hypot(position.dx, position.dy) + 0.01
      const limited = Math.min(temperature, disp)
      position.x += (position.dx / disp) * limited
      position.y += (position.dy / disp) * limited
      position.x = Math.min(width - padding, Math.max(padding, position.x))
      position.y = Math.min(height - padding, Math.max(padding, position.y))
    }

    temperature *= 0.93
  }

  const degreeMap = new Map<string, number>()
  for (const edge of edges) {
    degreeMap.set(edge.source, (degreeMap.get(edge.source) ?? 0) + 1)
    degreeMap.set(edge.target, (degreeMap.get(edge.target) ?? 0) + 1)
  }

  return nodes.map((node) => {
    const position = positions[nodeIndexById.get(node.id) ?? 0] ?? { x: centerX, y: centerY }
    const degree = degreeMap.get(node.id) ?? 0
    const radiusBase = node.termType === 'literal' ? 4.7 : 7.2
    const radius = Math.min(16, radiusBase + Math.log1p(degree) * 1.7)
    return {
      ...node,
      x: position.x,
      y: position.y,
      r: radius,
      color: KG_KIND_STYLE[node.kind].color,
    }
  })
}
