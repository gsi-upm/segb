<template>
  <div class="stack">
    <BaseCard title="Shared Context Resolver" subtitle="Resolve one independent observation to canonical shared-context URI.">
      <div class="form-grid">
        <label class="field">
          <span>event_kind</span>
          <input v-model="payload.event_kind" class="text-input" placeholder="human_utterance" />
        </label>

        <label class="field">
          <span>observed_at (UTC ISO)</span>
          <input v-model="payload.observed_at" class="text-input" placeholder="2026-02-10T12:00:00Z" />
        </label>

        <label class="field">
          <span>subject_uri</span>
          <input v-model="payload.subject_uri" class="text-input" placeholder="https://example.org/human/maria" />
        </label>

        <label class="field">
          <span>modality</span>
          <input v-model="payload.modality" class="text-input" placeholder="speech" />
        </label>

        <label class="field full">
          <span>text</span>
          <textarea v-model="payload.text" rows="4" class="text-area" />
        </label>
      </div>

      <div class="actions">
        <button class="btn" :disabled="loadingResolve" @click="resolve">{{ loadingResolve ? 'Resolving…' : 'Resolve' }}</button>
        <button class="btn ghost" :disabled="loadingStats" @click="loadStats">{{ loadingStats ? 'Loading…' : 'Load stats' }}</button>
        <button class="btn ghost" :disabled="loadingReconcile" @click="reconcile">{{ loadingReconcile ? 'Reconciling…' : 'Reconcile pending' }}</button>
      </div>

      <StatusBanner v-if="error" tone="error" :message="error" />
    </BaseCard>

    <BaseCard title="Resolve response">
      <pre class="raw">{{ resolveOutput || 'No response yet.' }}</pre>
    </BaseCard>

    <div class="grid two">
      <BaseCard title="Resolver stats">
        <pre class="raw">{{ statsOutput || 'No stats loaded.' }}</pre>
      </BaseCard>
      <BaseCard title="Reconcile result">
        <pre class="raw">{{ reconcileOutput || 'No reconcile run yet.' }}</pre>
      </BaseCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'

import BaseCard from '@/shared/ui/BaseCard.vue'
import StatusBanner from '@/shared/ui/StatusBanner.vue'
import { normalizeApiError } from '@/core/api/error'
import { getSharedContextStats, reconcileSharedContext, resolveSharedContext } from '@/core/api/segbApi'

const payload = reactive({
  event_kind: 'human_utterance',
  observed_at: new Date().toISOString(),
  subject_uri: '',
  modality: 'speech',
  text: '',
})

const loadingResolve = ref(false)
const loadingStats = ref(false)
const loadingReconcile = ref(false)
const error = ref('')
const resolveOutput = ref('')
const statsOutput = ref('')
const reconcileOutput = ref('')

async function resolve(): Promise<void> {
  loadingResolve.value = true
  error.value = ''

  try {
    const response = await resolveSharedContext({
      event_kind: payload.event_kind,
      observed_at: payload.observed_at,
      subject_uri: payload.subject_uri || undefined,
      modality: payload.modality || undefined,
      text: payload.text || undefined,
    })
    resolveOutput.value = JSON.stringify(response, null, 2)
  } catch (unknownError) {
    error.value = normalizeApiError(unknownError).message
  } finally {
    loadingResolve.value = false
  }
}

async function loadStats(): Promise<void> {
  loadingStats.value = true
  error.value = ''

  try {
    const response = await getSharedContextStats()
    statsOutput.value = JSON.stringify(response, null, 2)
  } catch (unknownError) {
    error.value = normalizeApiError(unknownError).message
  } finally {
    loadingStats.value = false
  }
}

async function reconcile(): Promise<void> {
  loadingReconcile.value = true
  error.value = ''

  try {
    const response = await reconcileSharedContext()
    reconcileOutput.value = JSON.stringify(response, null, 2)
  } catch (unknownError) {
    error.value = normalizeApiError(unknownError).message
  } finally {
    loadingReconcile.value = false
  }
}
</script>

<style scoped>
.stack {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.grid.two {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.7rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.9rem;
  color: var(--ink-700);
}

.field.full {
  grid-column: 1 / -1;
}

.text-input,
.text-area {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.58rem 0.62rem;
  font: inherit;
}

.actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.raw {
  margin: 0;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.75rem;
  background: linear-gradient(155deg, var(--panel-dark), var(--panel-dark-2));
  color: var(--panel-ink);
  overflow: auto;
  max-height: 380px;
  font-size: 0.82rem;
}

@media (max-width: 980px) {
  .form-grid,
  .grid.two {
    grid-template-columns: 1fr;
  }
}
</style>
