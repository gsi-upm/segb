<template>
  <section class="card centered">
    <h1 class="title">🔍 View Existing Semantic Logs</h1>
    <p class="description">
      Retrieve and explore all registered semantic logs. You can visualize the data directly as a knowledge graph.
    </p>

    <div class="actions">
      <button class="btn primary" style="margin-bottom: 3rem;" @click="load" :disabled="loading">
        {{ loading ? 'Loading…' : 'Load Semantic Logs' }}
      </button>
    </div>

    <p v-if="msg" class="info">{{ msg }}</p>
    <transition name="fade">
      <pre v-if="ttl" class="code block">{{ ttl }}</pre>
    </transition>

    <h2 class="subtitle" style="margin-top:2rem;">
    <span class="emoji">🖧</span> View Knowledge Graph
    </h2>
    <p class="description">
      Generate an interactive visualization of your semantic data to better understand entities and relations.
    </p>

    <div class="actions">
      <button class="btn primary" @click="visualize">Load Graph</button>
    </div>

    <GraphViewer v-if="showGraph && ttl" :ttl="ttl" style="margin-top:1rem" />
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '@/api/client'
import GraphViewer from '@/components/GraphViewer.vue'

const ttl = ref('')
const msg = ref('')
const loading = ref(false)
const showGraph = ref(false)

async function load() {
  msg.value = ''
  ttl.value = ''
  showGraph.value = false 
  loading.value = true
  try {
    const r = await api.get('/events', { responseType: 'text' })
    if (!r.data || r.data.length === 0)
      msg.value = 'No semantic logs have been inserted yet.'
    else ttl.value = r.data
  } catch (e: any) {
    msg.value = e?.message || 'Error loading data.'
  } finally {
    loading.value = false
  }
}

function visualize() {
  if (!ttl.value) {
    msg.value = 'Please load the TTL data first.'
    return
  }
  showGraph.value = true
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&display=swap');

.emoji {
  color: #ff9900; 
  font-weight: normal; 
}

.card {
  max-width: 64rem;
  margin: 64px auto;
  padding: 2rem 2.5rem;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(6px);
  font-family: 'Montserrat', sans-serif;
}


.centered {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.description {
  color: #555;
  font-size: 1.10rem; 
  margin-bottom: 1rem;
  max-width: 48rem;
}

.actions {
  display: flex;
  gap: 0.8rem;
  flex-wrap: wrap;
  justify-content: center;
  margin-bottom: 1rem;
}

.info {
  background: #cce5ff;
  color: #004085;
  border: 2px solid #b8daff;
  padding: 0.8rem 1rem;
  border-radius: 10px;
  margin-top: 0.8rem;
  text-align: center;
  font-size: 0.95rem;
}

.code.block {
  margin-top: 1rem;
  border-radius: 12px;
  padding: 1rem;
  background: #0b0f17;
  color: #cde;
  overflow: auto;
  max-width: 100%;
  text-align: left;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>