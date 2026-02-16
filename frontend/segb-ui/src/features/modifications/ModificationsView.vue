<template>
  <div class="stack">
    <BaseCard title="Modification Logs" subtitle="Audit trail stored in Neo4j via /modifications and /modifications_date.">
      <div class="filters">
        <label class="field compact">
          <span>Limit</span>
          <input v-model.number="limit" type="number" min="1" max="500" class="text-input" />
        </label>

        <label class="field compact">
          <span>Start date</span>
          <input v-model="startDate" type="datetime-local" class="text-input" />
        </label>

        <label class="field compact">
          <span>End date</span>
          <input v-model="endDate" type="datetime-local" class="text-input" />
        </label>
      </div>

      <div class="actions">
        <button class="btn" :disabled="loading" @click="loadRecent">
          {{ loading ? 'Loading…' : 'Load recent' }}
        </button>
        <button class="btn ghost" :disabled="loading || !startDate || !endDate" @click="loadByDate">
          Load by date range
        </button>
      </div>

      <StatusBanner v-if="message" tone="info" :message="message" />
      <StatusBanner v-if="error" tone="error" :message="error" />
    </BaseCard>

    <BaseCard title="Audit entries">
      <DataTable :columns="columns" :rows="rows" />
    </BaseCard>

    <BaseCard
      title="Administrative Action"
      subtitle="Dangerous operation: clears Virtuoso graph and writes deletion audit logs."
    >
      <div class="danger-zone">
        <label class="field compact">
          <span>Type DELETE to confirm</span>
          <input v-model="deleteConfirmation" class="text-input" placeholder="DELETE" />
        </label>
        <button class="btn danger" :disabled="loadingDelete || deleteConfirmation !== 'DELETE'" @click="deleteAll">
          {{ loadingDelete ? 'Deleting…' : 'Delete all triples' }}
        </button>
      </div>
      <StatusBanner v-if="deleteMessage" tone="warning" :message="deleteMessage" />
    </BaseCard>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import BaseCard from '@/shared/ui/BaseCard.vue'
import DataTable, { type TableColumn } from '@/shared/ui/DataTable.vue'
import StatusBanner from '@/shared/ui/StatusBanner.vue'
import { deleteAllTtls, getModifications, getModificationsByDate, type ModificationLog } from '@/core/api/segbApi'
import { normalizeApiError } from '@/core/api/error'
import { formatUtcTimestamp } from '@/shared/utils/format'

const limit = ref(25)
const startDate = ref('')
const endDate = ref('')
const logs = ref<ModificationLog[]>([])
const loading = ref(false)
const message = ref('')
const error = ref('')

const deleteConfirmation = ref('')
const loadingDelete = ref(false)
const deleteMessage = ref('')

const columns: TableColumn[] = [
  { key: 'timestamp', label: 'Timestamp' },
  { key: 'user', label: 'User' },
  { key: 'action', label: 'Action' },
  { key: 'origin_ip', label: 'Origin IP' },
  { key: 'log_id', label: 'Log ID' },
  { key: 'ttl_preview', label: 'TTL Preview' },
]

const rows = computed(() => {
  return logs.value.map((log) => ({
    timestamp: formatUtcTimestamp(log.timestamp),
    user: log.user,
    action: log.action,
    origin_ip: log.origin_ip,
    log_id: log.log_id,
    ttl_preview: log.ttl_content.slice(0, 120).replace(/\s+/g, ' '),
  }))
})

async function loadRecent(): Promise<void> {
  loading.value = true
  message.value = ''
  error.value = ''

  try {
    logs.value = await getModifications(limit.value)
    message.value = `Loaded ${logs.value.length} modifications.`
  } catch (unknownError) {
    error.value = normalizeApiError(unknownError).message
  } finally {
    loading.value = false
  }
}

async function loadByDate(): Promise<void> {
  loading.value = true
  message.value = ''
  error.value = ''

  try {
    logs.value = await getModificationsByDate(startDate.value, endDate.value)
    message.value = `Loaded ${logs.value.length} modifications in range.`
  } catch (unknownError) {
    error.value = normalizeApiError(unknownError).message
  } finally {
    loading.value = false
  }
}

async function deleteAll(): Promise<void> {
  loadingDelete.value = true
  deleteMessage.value = ''
  error.value = ''

  try {
    const response = await deleteAllTtls()
    deleteMessage.value = response.message
    deleteConfirmation.value = ''
  } catch (unknownError) {
    error.value = normalizeApiError(unknownError).message
  } finally {
    loadingDelete.value = false
  }
}
</script>

<style scoped>
.stack {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.7rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.9rem;
  color: var(--ink-700);
}

.field.compact span {
  font-size: 0.82rem;
}

.text-input {
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

.danger-zone {
  display: flex;
  gap: 0.65rem;
  align-items: flex-end;
  flex-wrap: wrap;
}

@media (max-width: 980px) {
  .filters {
    grid-template-columns: 1fr;
  }
}
</style>
