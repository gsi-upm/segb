import { computed, ref } from 'vue'

import { runSelectQuery } from '@/core/api/segbApi'
import { compactUri, formatRatioAsPercent, formatUtcTimestamp, titleCase, toNumber } from '@/shared/utils/format'
import { reportQueries } from '@/features/reports/queries'
import type {
  ReportDisplacementSummary,
  ReportEmotionSample,
  ReportMlUsage,
  ReportParticipantInteraction,
  ReportStateSample,
} from '@/features/reports/types'

const PARTICIPANT_SEPARATOR = '__SEGB_LINE_BREAK__'

function normalizeEmotionLabel(uri: string): string {
  const compact = compactUri(uri)
  return titleCase(compact.replace(/^big6[_-]/i, ''))
}

function asLines(value: string): string[] {
  return value
    .split(PARTICIPANT_SEPARATOR)
    .flatMap((chunk) => chunk.split('\n'))
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
}

function decorateParticipants(value: string, icon: string): string {
  const unique = Array.from(new Set(asLines(value)))
  if (unique.length === 0) {
    return ''
  }
  return unique.map((name) => `${icon} ${name}`).join('\n')
}

function decorateParticipant(name: string, icon: string): string {
  const normalized = name.trim()
  return normalized.length > 0 ? `${icon} ${normalized}` : ''
}

function mergeParticipantLists(...lists: string[]): string {
  const merged = Array.from(new Set(lists.flatMap((value) => asLines(value))))
  return merged.join('\n')
}

export function useReports() {
  const loading = ref(false)
  const error = ref('')

  const humanParticipants = ref<ReportParticipantInteraction[]>([])
  const robotParticipants = ref<ReportParticipantInteraction[]>([])
  const mlUsage = ref<ReportMlUsage[]>([])
  const emotionTimeline = ref<ReportEmotionSample[]>([])
  const extremeEmotion = ref<ReportEmotionSample[]>([])
  const robotStates = ref<ReportStateSample[]>([])
  const displacementSummary = ref<ReportDisplacementSummary[]>([])

  const emotionTimelineByParticipant = computed(() => {
    const grouped = new Map<string, Array<{ xLabel: string; y: number; tag: string }>>()

    for (const row of emotionTimeline.value) {
      const participant = row.targetLabel || compactUri(row.targetEntity)
      const intensity = toNumber(row.intensity)
      if (intensity === null) {
        continue
      }
      if (!grouped.has(participant)) {
        grouped.set(participant, [])
      }
      grouped.get(participant)?.push({
        xLabel: formatUtcTimestamp(row.t).replace(' UTC', ''),
        y: intensity,
        tag: normalizeEmotionLabel(row.category),
      })
    }

    for (const [participant, points] of grouped.entries()) {
      points.sort((a, b) => a.xLabel.localeCompare(b.xLabel))
      grouped.set(participant, points)
    }

    return grouped
  })

  const maxEmotionIntensity = computed<number | null>(() => {
    let maxValue: number | null = null
    for (const row of emotionTimeline.value) {
      const intensity = toNumber(row.intensity)
      if (intensity === null) {
        continue
      }
      maxValue = maxValue === null ? intensity : Math.max(maxValue, intensity)
    }
    return maxValue
  })

  const extremeEmotionBars = computed(() => {
    const counters = new Map<string, number>()
    for (const row of extremeEmotion.value) {
      const emotion = normalizeEmotionLabel(row.category)
      counters.set(emotion, (counters.get(emotion) ?? 0) + 1)
    }
    return Array.from(counters.entries())
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value)
  })

  async function loadAllReports(): Promise<void> {
    loading.value = true
    error.value = ''

    try {
      const [
        humanParticipantsRows,
        robotParticipantsRows,
        mlRows,
        emotionRows,
        extremeRows,
        stateRows,
      ] = await Promise.all([
        runSelectQuery(reportQueries.participantsHumans),
        runSelectQuery(reportQueries.participantsRobots),
        runSelectQuery(reportQueries.mlUsage),
        runSelectQuery(reportQueries.emotionTimeline),
        runSelectQuery(reportQueries.extremeEmotion),
        runSelectQuery(reportQueries.robotState),
      ])

      humanParticipants.value = humanParticipantsRows
        .map((row) => ({
          participant: decorateParticipant(row.participant ?? '', '🧑'),
          interactedWith: decorateParticipants(row.interactedRobots ?? '', '🤖'),
        }))
        .filter((row) => row.participant.length > 0)

      robotParticipants.value = robotParticipantsRows
        .map((row) => ({
          participant: decorateParticipant(row.participant ?? '', '🤖'),
          interactedWith: mergeParticipantLists(
            decorateParticipants(row.interactedHumans ?? '', '🧑'),
            decorateParticipants(row.interactedRobots ?? '', '🤖'),
          ),
        }))
        .filter((row) => row.participant.length > 0)

      mlUsage.value = mlRows.map((row) => ({
        activity: compactUri(row.activity ?? ''),
        activityType: compactUri(row.activityType ?? ''),
        usedBy: row.usedByName ?? compactUri(row.usedBy ?? ''),
        usedAt: formatUtcTimestamp(row.startedAt ?? ''),
        model: compactUri(row.model ?? ''),
        modelLabel: row.modelLabel ?? '',
        version: row.version ?? '',
        dataset: compactUri(row.dataset ?? ''),
        datasetLabel: row.datasetLabel ?? '',
        score: formatRatioAsPercent(row.score ?? ''),
      }))

      emotionTimeline.value = emotionRows.map((row) => ({
        t: row.t ?? '',
        sourceActivity: compactUri(row.sourceActivity ?? ''),
        targetEntity: row.targetEntity ?? '',
        targetType: row.targetType ?? '',
        targetLabel: row.targetLabel ?? compactUri(row.targetEntity ?? ''),
        category: row.category ?? '',
        intensity: row.intensity ?? '',
        confidence: row.confidence ?? '',
      }))

      extremeEmotion.value = extremeRows.map((row) => ({
        t: row.t ?? '',
        sourceActivity: compactUri(row.sourceActivity ?? ''),
        targetEntity: row.targetEntity ?? '',
        targetType: row.targetType ?? '',
        targetLabel: row.targetLabel ?? compactUri(row.targetEntity ?? ''),
        category: row.category ?? '',
        intensity: row.intensity ?? '',
        confidence: row.confidence ?? '',
      }))

      robotStates.value = stateRows.map((row) => ({
        robot: row.robot ?? '',
        robotName: row.robotName ?? compactUri(row.robot ?? ''),
        t: row.t ?? '',
        location: compactUri(row.location ?? ''),
      }))

      buildDisplacementSummary()
    } catch (backendError) {
      error.value = backendError instanceof Error ? backendError.message : 'Failed to load reports.'
    } finally {
      loading.value = false
    }
  }

  function buildDisplacementSummary(): void {
    const grouped = new Map<string, ReportStateSample[]>()
    for (const row of robotStates.value) {
      const key = row.robotName || compactUri(row.robot)
      if (!grouped.has(key)) {
        grouped.set(key, [])
      }
      grouped.get(key)?.push(row)
    }

    const summary: ReportDisplacementSummary[] = []
    for (const [robot, samples] of grouped.entries()) {
      const ordered = [...samples].sort((a, b) => a.t.localeCompare(b.t))
      const path = ordered.map((row) => row.location)
      let changes = 0
      for (let index = 1; index < path.length; index += 1) {
        if (path[index] !== path[index - 1]) {
          changes += 1
        }
      }
      summary.push({
        robot,
        samples: path.length,
        locationChanges: changes,
        path: path.join(' -> '),
      })
    }

    summary.sort((a, b) => a.robot.localeCompare(b.robot))
    displacementSummary.value = summary
  }

  return {
    loading,
    error,
    humanParticipants,
    robotParticipants,
    mlUsage,
    emotionTimeline,
    emotionTimelineByParticipant,
    maxEmotionIntensity,
    extremeEmotion,
    extremeEmotionBars,
    robotStates,
    displacementSummary,
    loadAllReports,
    normalizeEmotionLabel,
    formatUtcTimestamp,
  }
}
