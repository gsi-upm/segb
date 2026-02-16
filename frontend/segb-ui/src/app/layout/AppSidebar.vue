<template>
  <aside class="sidebar">
    <p class="section">Analytics</p>
    <RouterLink class="nav-link" to="/reports">Reports Dashboard</RouterLink>
    <RouterLink class="nav-link" to="/kg-graph">KG Visual Explorer</RouterLink>

    <p class="section">Operations</p>
    <RouterLink class="nav-link" to="/logs/insert">Insert TTL</RouterLink>
    <RouterLink class="nav-link" to="/logs/modifications">Modification Logs</RouterLink>
    <RouterLink class="nav-link" to="/query">SPARQL Workbench</RouterLink>

    <p class="section">Shared Context</p>
    <RouterLink class="nav-link" to="/shared-context">Resolver Console</RouterLink>

    <p class="section">System</p>
    <RouterLink class="nav-link" to="/health">Health</RouterLink>
    <RouterLink class="nav-link" to="/session">Session</RouterLink>
  </aside>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<style scoped>
.sidebar {
  position: sticky;
  top: 0;
  align-self: start;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface);
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.section {
  margin: 0.75rem 0 0.2rem;
  color: var(--ink-500);
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.nav-link {
  text-decoration: none;
  color: var(--ink-800);
  font-weight: 540;
  font-size: 0.92rem;
  border-radius: 10px;
  padding: 0.48rem 0.56rem;
}

.nav-link:hover {
  background: var(--surface-alt);
}

.nav-link.router-link-active {
  color: #005d91;
  background: #dff3fc;
}
</style>
