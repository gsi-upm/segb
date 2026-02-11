<template>
  <section class="card centered">
    <h1 class="title">❓ Run Custom SPARQL Query</h1>
    <p class="description">
      Execute custom SPARQL queries over the SEGB Knowledge Graph and visualize the results as an interactive network.
    </p>

    <textarea
      v-model="query"
      rows="10"
      class="ta"
      placeholder="Write your SPARQL query here..."
    ></textarea>

    <div class="actions" style="margin-top:1.5rem;">
      <button class="btn primary" @click="execute" :disabled="loading">
        {{ loading ? 'Running…' : 'Execute Query' }}
      </button>
      <button class="btn" @click="visualize">Visualize Graph</button>
    </div>

    <transition name="fade">
      <div v-if="ttl" class="results">
        <h2 class="subtitle" style="margin-top:2rem;">📄 Query Results</h2>
        <pre class="code block">{{ ttl }}</pre>

        <h2 class="subtitle" style="margin-top:2rem;">
          <span class="emoji">🖧</span> Knowledge Graph Visualization
        </h2>
        <GraphViewer v-if="showGraph" :ttl="ttl" style="margin-top:1rem" />
      </div>
    </transition>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '@/api/client'
import GraphViewer from '@/components/GraphViewer.vue'

const query = ref('')
const ttl = ref('')
const showGraph = ref(false)
const loading = ref(false)

async function execute() {
  if (!query.value.trim()) return
  loading.value = true
  try {
    const r = await api.get('/query', {
      params: { query: query.value },
      responseType: 'text',
    })
    ttl.value = r.data
    showGraph.value = false
  } catch (e: any) {
    ttl.value = `Error: ${e?.message || 'Failed to execute query.'}`
  } finally {
    loading.value = false
  }
}

function visualize() {
  if (ttl.value) showGraph.value = true
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&display=swap');

.emoji { color: #ff9900; font-weight: normal; }

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

.btn{
    background-color: #eff0f2;
}

.description { color: #555; font-size: 1.10rem; margin-bottom: 2rem; max-width: 48rem; }

.ta {
  width: 100%;
  min-height: 220px;
  border-radius: 10px;
  padding: 12px;
  border: 1px solid #d0d7de;
  background: #fff;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 1rem;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.ta:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 4px rgba(0, 169, 224, 0.15);
}

.actions {
  display: flex;
  gap: 0.8rem;
  flex-wrap: wrap;
  justify-content: center;
}

.results {
  width: 100%;
  text-align: left;
}

.code.block {
  margin-top: 1rem;
  border-radius: 12px;
  padding: 1rem;
  background: #0b0f17;
  color: #cde;
  overflow: auto;
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
