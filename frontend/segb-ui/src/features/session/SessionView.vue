<template>
  <div class="stack">
    <BaseCard title="Session token" subtitle="Stored in sessionStorage and attached as Bearer token on API calls.">
      <label class="field">
        <span>JWT token (optional if backend security is disabled)</span>
        <textarea
          v-model="tokenDraft"
          rows="6"
          class="text-area"
          placeholder="eyJhbGciOi..."
        />
      </label>

      <div class="actions">
        <button class="btn" @click="save">Save token</button>
        <button class="btn ghost" @click="clear">Clear token</button>
      </div>

      <StatusBanner v-if="message" tone="success" :message="message" />
    </BaseCard>

    <BaseCard title="Decoded payload (UI hint only)">
      <pre class="raw">{{ decodedOutput }}</pre>
    </BaseCard>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import BaseCard from '@/shared/ui/BaseCard.vue'
import StatusBanner from '@/shared/ui/StatusBanner.vue'
import { useSessionStore } from '@/core/auth/sessionStore'

const session = useSessionStore()
const tokenDraft = ref(session.token)
const message = ref('')

const decodedOutput = computed(() => {
  const payload = {
    isAuthenticated: session.isAuthenticated,
    isExpired: session.isExpired,
    decoded: session.decodedToken,
  }
  return JSON.stringify(payload, null, 2)
})

function save(): void {
  session.setToken(tokenDraft.value)
  message.value = 'Token saved in session storage.'
}

function clear(): void {
  session.clearToken()
  tokenDraft.value = ''
  message.value = 'Token removed from session storage.'
}
</script>

<style scoped>
.stack {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.9rem;
  color: var(--ink-700);
}

.text-area {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.65rem 0.7rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
  font-size: 0.84rem;
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
</style>
