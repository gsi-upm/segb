<template>
  <div class="layout">
    <AppTopbar />

    <div class="workspace">
      <AppSidebar class="sidebar" />
      <main class="content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'

import AppSidebar from '@/app/layout/AppSidebar.vue'
import AppTopbar from '@/app/layout/AppTopbar.vue'
</script>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.workspace {
  display: grid;
  grid-template-columns: minmax(220px, 260px) minmax(0, 1fr);
  gap: 0.9rem;
  align-items: start;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

@media (max-width: 1000px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: static;
  }
}
</style>
