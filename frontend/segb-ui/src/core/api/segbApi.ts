import httpClient from '@/core/api/httpClient'
import { parseSelectResultTurtle, type SelectRow } from '@/shared/rdf/parseSelectResult'

export type TtlInsertPayload = {
  ttl_content: string
  user?: string
}

export type TtlInsertResponse = {
  message: string
  log_id: string
}

export type ModificationLog = {
  log_id: string
  user: string
  action: string
  timestamp: string
  origin_ip: string
  ttl_content: string
}

export type SharedContextResolvePayload = {
  event_kind: string
  observed_at: string
  subject_uri?: string
  modality?: string
  text?: string
  observation_uri?: string
  robot_uri?: string
  time_window_seconds?: number
}

export type SharedContextResolveResponse = {
  shared_context_uri: string
  status: 'matched' | 'created' | 'ambiguous'
  confidence: number
  resolver_version: string
  candidate_count: number
  matched_candidate_uri?: string | null
  close_candidates: string[]
  score_breakdown: Record<string, number>
}

export type SharedContextReconcileResponse = {
  scanned_ambiguous: number
  merged_count: number
  mappings: Record<string, string>
  resolver_version: string
}

export type SharedContextStatsResponse = {
  resolver_version: string
  active_contexts: number
  ambiguous_contexts: number
  merged_contexts: number
  aliases: number
}

export type ReadyResponse = {
  ready: boolean
  neo4j: boolean
  virtuoso: boolean
}

function fromJsonLikePayload(payload: unknown): string {
  if (typeof payload === 'string') {
    return payload
  }

  if (typeof payload === 'object' && payload !== null) {
    const data = payload as Record<string, unknown>
    const detail = typeof data.detail === 'string' ? data.detail : null
    const message = typeof data.message === 'string' ? data.message : null
    if (detail || message) {
      throw new Error(detail ?? message ?? 'Backend query failed.')
    }
  }

  throw new Error('Unexpected /query response format. Expected text/turtle.')
}

function normalizeQueryResponse(data: unknown): string {
  if (typeof data !== 'string') {
    return fromJsonLikePayload(data)
  }

  const trimmed = data.trim()
  if (!trimmed) {
    return data
  }

  const mightBeJson =
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith('{') && trimmed.endsWith('}'))

  if (!mightBeJson) {
    return data
  }

  try {
    const parsed = JSON.parse(trimmed) as unknown
    return fromJsonLikePayload(parsed)
  } catch {
    return data
  }
}

export async function getLiveHealth(): Promise<{ live: boolean }> {
  const { data } = await httpClient.get<{ live: boolean }>('/healthz/live')
  return data
}

export async function getReadyHealth(): Promise<ReadyResponse> {
  const { data } = await httpClient.get<ReadyResponse>('/healthz/ready')
  return data
}

export async function insertTtl(payload: TtlInsertPayload): Promise<TtlInsertResponse> {
  const { data } = await httpClient.post<TtlInsertResponse>('/ttl', payload)
  return data
}

export async function getEventsTurtle(): Promise<string> {
  const { data } = await httpClient.get<string>('/events', {
    responseType: 'text',
  })
  return data
}

export async function runQueryTurtle(query: string): Promise<string> {
  const { data } = await httpClient.get<string>('/query', {
    params: { query },
    responseType: 'text',
  })
  return normalizeQueryResponse(data)
}

export async function runSelectQuery(query: string): Promise<SelectRow[]> {
  const turtle = await runQueryTurtle(query)
  return parseSelectResultTurtle(turtle)
}

export async function getModifications(limit: number): Promise<ModificationLog[]> {
  const { data } = await httpClient.get<ModificationLog[]>('/modifications', {
    params: { limit },
  })
  return data
}

export async function getModificationsByDate(startDate: string, endDate: string): Promise<ModificationLog[]> {
  const { data } = await httpClient.get<ModificationLog[]>('/modifications_date', {
    params: {
      start_date: startDate,
      end_date: endDate,
    },
  })
  return data
}

export async function deleteAllTtls(user?: string): Promise<{ message: string }> {
  const { data } = await httpClient.post<{ message: string }>('/ttl/delete_all', {
    user,
  })
  return data
}

export async function resolveSharedContext(
  payload: SharedContextResolvePayload,
): Promise<SharedContextResolveResponse> {
  const { data } = await httpClient.post<SharedContextResolveResponse>('/shared-context/resolve', payload)
  return data
}

export async function reconcileSharedContext(): Promise<SharedContextReconcileResponse> {
  const { data } = await httpClient.post<SharedContextReconcileResponse>('/shared-context/reconcile')
  return data
}

export async function getSharedContextStats(): Promise<SharedContextStatsResponse> {
  const { data } = await httpClient.get<SharedContextStatsResponse>('/shared-context/stats')
  return data
}
