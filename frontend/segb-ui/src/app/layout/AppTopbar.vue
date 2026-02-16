<template>
  <header class="topbar">
    <div>
      <h1 class="brand">Semantic Ethical Glass Box</h1>
      <p class="subtitle">Control Panel & Reports Analysis</p>
    </div>

    <div class="session-info">
      <span class="pill" :class="sessionTone">{{ sessionText }}</span>
      <RouterLink class="settings-link" to="/session">Session Settings</RouterLink>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { useSessionStore } from '@/core/auth/sessionStore'

const session = useSessionStore()

const sessionTone = computed(() => {
  if (!session.token) {
    return 'warning'
  }
  if (session.isExpired) {
    return 'error'
  }
  return 'ok'
})

const sessionText = computed(() => {
  if (!session.token) {
    return 'No token in session'
  }
  if (session.isExpired) {
    return 'Token expired'
  }
  const user = session.decodedToken?.username ?? 'token-set'
  return `Token active: ${user}`
})
</script>

<style scoped>
.topbar {
  border: 1px solid var(--border);
  border-radius: 14px;
  background: linear-gradient(92deg, var(--brand-upm-strong), var(--brand-upm) 52%, var(--brand-gsi));
  color: #f2fbff;
  padding: 0.95rem 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.brand {
  margin: 0;
  font-size: 1.35rem;
}

.subtitle {
  margin: 0.2rem 0 0;
  font-size: 0.82rem;
  color: #ddf5ff;
}

.session-info {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  align-items: flex-end;
}

.pill {
  font-size: 0.75rem;
  border-radius: 999px;
  padding: 0.35rem 0.55rem;
  border: 1px solid transparent;
}

.pill.ok {
  background: #e4f6ff;
  color: #005d8f;
  border-color: #9bd7ef;
}

.pill.warning {
  background: #fef9c3;
  color: #854d0e;
  border-color: #fde047;
}

.pill.error {
  background: #fee2e2;
  color: #991b1b;
  border-color: #fca5a5;
}

.settings-link {
  color: #f2fbff;
  text-decoration: none;
  font-size: 0.84rem;
  border-bottom: 1px dashed rgba(242, 251, 255, 0.72);
}

@media (max-width: 920px) {
  .topbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .session-info {
    align-items: flex-start;
  }
}
</style>
