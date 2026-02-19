<template>
  <div class="stack">
    <BaseCard
      title="Notebook Reports Dashboard"
      subtitle="Predefined analyses sourced from KG queries: participants, ML usage, emotions, and displacement."
    >
      <div class="actions">
        <button class="btn" :disabled="loading" @click="loadAllReports">
          {{ loading ? 'Loading reports…' : 'Refresh reports' }}
        </button>
      </div>
      <StatusBanner
        v-if="error"
        tone="error"
        :message="error"
      />
    </BaseCard>

    <div class="grid top-reports">
      <BaseCard title="Report 1: Participants">
        <div class="participants-sections">
          <section class="participants-section">
            <h4 class="section-title">Humans</h4>
            <DataTable :columns="participantColumns" :rows="humanParticipantsRows" :max-height="compactTableMaxHeight" />
          </section>

          <section class="participants-section">
            <h4 class="section-title">Robots</h4>
            <DataTable :columns="participantColumns" :rows="robotParticipantsRows" :max-height="compactTableMaxHeight" />
          </section>
        </div>
      </BaseCard>

      <BaseCard title="Report 2: ML Usage">
        <DataTable :columns="mlColumns" :rows="mlRows" :max-height="largeTableMaxHeight" />
      </BaseCard>
    </div>

    <BaseCard title="Report 3: Temporal Emotions">
      <p class="note">
        One line per participant, one emotion sample per timestamp.
      </p>
      <div v-if="emotionCharts.length === 0" class="empty">No emotion timeline data available.</div>
      <div v-else class="chart-grid">
        <SimpleLineChart
          v-for="chart in emotionCharts"
          :key="chart.title"
          :title="chart.title"
          :points="chart.points"
          :y-max="100"
        />
      </div>
    </BaseCard>

    <div class="grid two">
      <BaseCard title="Report 4: Extreme Emotions (>= 75%)">
        <template v-if="extremeRows.length > 0">
          <DataTable :columns="extremeColumns" :rows="extremeRows" :max-height="regularTableMaxHeight" />
        </template>
        <StatusBanner
          v-else
          tone="warning"
          :message="extremeEmptyMessage"
        />
      </BaseCard>

      <BaseCard title="Extreme Emotion Distribution">
        <template v-if="extremeBars.length > 1">
          <SimpleBarChart title="Extreme emotion counts" :bars="extremeBars" />
        </template>
        <StatusBanner
          v-else
          tone="warning"
          message="Not enough emotion categories for a meaningful distribution chart."
        />
      </BaseCard>
    </div>

    <div class="grid two">
      <BaseCard title="Report 8: Robot State Timeline">
        <DataTable :columns="stateColumns" :rows="stateRows" :max-height="regularTableMaxHeight" />
      </BaseCard>

      <BaseCard title="Report 8: Displacement Summary">
        <DataTable :columns="summaryColumns" :rows="summaryRows" :max-height="regularTableMaxHeight" />
      </BaseCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'

import BaseCard from '@/shared/ui/BaseCard.vue'
import DataTable, { type TableColumn } from '@/shared/ui/DataTable.vue'
import StatusBanner from '@/shared/ui/StatusBanner.vue'
import SimpleLineChart from '@/shared/charts/SimpleLineChart.vue'
import SimpleBarChart from '@/shared/charts/SimpleBarChart.vue'
import { formatRatioAsPercent } from '@/shared/utils/format'
import { useReports } from '@/features/reports/useReports'

const {
  loading,
  error,
  humanParticipants,
  robotParticipants,
  mlUsage,
  emotionTimelineByParticipant,
  maxEmotionIntensity,
  extremeEmotion,
  extremeEmotionBars,
  robotStates,
  displacementSummary,
  loadAllReports,
  normalizeEmotionLabel,
  formatUtcTimestamp,
} = useReports()

const participantColumns: TableColumn[] = [
  { key: 'participant', label: 'Participant' },
  { key: 'interactedWith', label: 'Interacted with' },
]

const mlColumns: TableColumn[] = [
  { key: 'usedBy', label: 'Used by' },
  { key: 'usedAt', label: 'When (UTC)' },
  { key: 'activity', label: 'Activity' },
  { key: 'activityType', label: 'Activity Type' },
  { key: 'modelLabel', label: 'Model' },
  { key: 'version', label: 'Version' },
  { key: 'datasetLabel', label: 'Dataset' },
  { key: 'score', label: 'Evaluation Score (%)' },
]

const extremeColumns: TableColumn[] = [
  { key: 'timestamp', label: 'Timestamp' },
  { key: 'target', label: 'Subject' },
  { key: 'category', label: 'Emotion' },
  { key: 'intensity', label: 'Intensity (%)' },
  { key: 'confidence', label: 'Confidence (%)' },
]

const stateColumns: TableColumn[] = [
  { key: 'robot', label: 'Robot' },
  { key: 'timestamp', label: 'Timestamp' },
  { key: 'location', label: 'Location' },
]

const summaryColumns: TableColumn[] = [
  { key: 'robot', label: 'Robot' },
  { key: 'samples', label: 'State Samples' },
  { key: 'locationChanges', label: 'Location Changes' },
  { key: 'path', label: 'Observed Path' },
]

const humanParticipantsRows = computed(() => humanParticipants.value)
const robotParticipantsRows = computed(() => robotParticipants.value)
const mlRows = computed(() => mlUsage.value)
const compactTableMaxHeight = 190
const regularTableMaxHeight = 340
const largeTableMaxHeight = 560
const EXTREME_THRESHOLD = 0.75

const emotionCharts = computed(() => {
  return Array.from(emotionTimelineByParticipant.value.entries()).map(([participant, points]) => ({
    title: participant,
    points,
  }))
})

const extremeRows = computed(() => {
  return extremeEmotion.value.map((row) => ({
    timestamp: formatUtcTimestamp(row.t),
    target: row.targetLabel,
    category: normalizeEmotionLabel(row.category),
    intensity: formatRatioAsPercent(row.intensity, 0),
    confidence: formatRatioAsPercent(row.confidence, 0),
  }))
})

const extremeEmptyMessage = computed(() => {
  if (maxEmotionIntensity.value === null) {
    return 'No emotion timeline data available yet.'
  }
  return `No extreme emotions found with threshold >= ${formatRatioAsPercent(EXTREME_THRESHOLD, 0)}. Current max intensity: ${formatRatioAsPercent(maxEmotionIntensity.value, 0)}.`
})

const extremeBars = computed(() => extremeEmotionBars.value)

const stateRows = computed(() => {
  return robotStates.value.map((row) => ({
    robot: row.robotName,
    timestamp: formatUtcTimestamp(row.t),
    location: row.location,
  }))
})

const summaryRows = computed(() => displacementSummary.value)

onMounted(() => {
  void loadAllReports()
})
</script>

<style scoped>
.stack {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.grid {
  display: grid;
  gap: 0.9rem;
}

.grid.top-reports {
  grid-template-columns: minmax(320px, 0.65fr) minmax(0, 1.35fr);
  align-items: start;
}

.grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.participants-sections {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.participants-section {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.section-title {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 700;
  color: var(--ink-700);
}

.actions {
  display: flex;
  gap: 0.6rem;
}

.note {
  margin: 0;
  font-size: 0.9rem;
  color: var(--ink-600);
}

.chart-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.8rem;
  min-width: 0;
}

.chart-grid > * {
  min-width: 0;
}

.empty {
  color: var(--ink-500);
  font-size: 0.92rem;
}

@media (max-width: 1200px) {
  .grid.top-reports {
    grid-template-columns: 1fr;
  }

  .grid.two {
    grid-template-columns: 1fr;
  }
}
</style>
