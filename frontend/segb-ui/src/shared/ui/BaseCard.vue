<template>
  <section class="card">
    <header v-if="title || subtitle" class="header">
      <h2 v-if="title" class="title">{{ title }}</h2>
      <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
    </header>

    <div class="content">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
  subtitle?: string
}>()
</script>

<style scoped>
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 1rem 1rem 1.25rem;
  box-shadow: var(--shadow-sm);
}

.header {
  margin-bottom: 0.9rem;
}

.title {
  margin: 0;
  font-size: 1.1rem;
  color: var(--ink-900);
}

.subtitle {
  margin: 0.3rem 0 0;
  font-size: 0.9rem;
  color: var(--ink-600);
}

.content {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}
</style>
