<template>
  <div class="stack">
    <BaseCard title="Backend health" subtitle="/healthz/live and /healthz/ready endpoints.">
      <div class="actions">
        <button class="btn" :disabled="loading" @click="load">
          {{ loading ? 'Checking…' : 'Check health' }}
        </button>
      </div>
      <StatusBanner v-if="error" tone="error" :message="error" />
    </BaseCard>

    <div class="grid two">
      <BaseCard title="Live probe">
        <pre class="raw">{{ liveOutput || 'Not checked yet.' }}</pre>
      </BaseCard>
      <BaseCard title="Ready probe">
        <pre class="raw">{{ readyOutput || 'Not checked yet.' }}</pre>
      </BaseCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import BaseCard from '@/shared/ui/BaseCard.vue'
import StatusBanner from '@/shared/ui/StatusBanner.vue'
import { getLiveHealth, getReadyHealth } from '@/core/api/segbApi'
import { normalizeApiError } from '@/core/api/error'

const loading = ref(false)
const error = ref('')
const liveOutput = ref('')
const readyOutput = ref('')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''

  try {
    const [live, ready] = await Promise.all([getLiveHealth(), getReadyHealth()])
    liveOutput.value = JSON.stringify(live, null, 2)
    readyOutput.value = JSON.stringify(ready, null, 2)
  } catch (unknownError) {
    error.value = normalizeApiError(unknownError).message
  } finally {
    loading.value = false
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

.actions {
  display: flex;
  gap: 0.5rem;
}

.raw {
  margin: 0;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.75rem;
  background: linear-gradient(155deg, var(--panel-dark), var(--panel-dark-2));
  color: var(--panel-ink);
  overflow: auto;
  max-height: 320px;
  font-size: 0.84rem;
}

@media (max-width: 980px) {
  .grid.two {
    grid-template-columns: 1fr;
  }
}
</style>
