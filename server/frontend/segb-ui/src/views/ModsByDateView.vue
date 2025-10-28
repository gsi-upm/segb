<template>
  <section class="card centered">
    <h1 class="title">📅 View Modifications by Date</h1>
    <p class="description">
      Select a time range to fetch modification logs and generate an interactive user→change graph.
    </p>

    <div class="row">
      <div class="field">
        <label class="label" for="start">Start</label>
        <input id="start" type="datetime-local" v-model="start" class="in" />
      </div>
      <div class="field">
        <label class="label" for="end">End</label>
        <input id="end" type="datetime-local" v-model="end" class="in" />
      </div>
    </div>

    <div class="actions">
      <button class="btn primary" @click="fetchLogs" :disabled="loading">
        {{ loading ? 'Loading…' : 'Fetch Logs by Date' }}
      </button>
    </div>

    <p v-if="!logs.length && info" class="info">{{ info }}</p>

    <div v-for="l in logs" :key="l.log_id" class="log-card">
      <pre class="code block">{{ l }}</pre>
    </div>

    <h2 class="subtitle" style="margin-top:2rem;">
      <span class="emoji">🖧</span> Historical Graph Visualization
    </h2>
    <p class="description">
           Visualize the modification logs linear graph.
    </p>

    <div class="actions">
      <button class="btn primary" @click="visualize">Visualize Graph by Date</button>
    </div>

    <GraphViewer v-if="graphTTL" :ttl="graphTTL" style="margin-top:1rem" />
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '@/api/client'
import GraphViewer from '@/components/GraphViewer.vue'

type ModLog = { log_id: string; user?: string; ttl_content?: string; [k: string]: any }

const start = ref<string>('')
const end = ref<string>('')
const logs = ref<ModLog[]>([])
const info = ref<string>('')
const graphTTL = ref<string>('')
const loading = ref(false)

async function fetchLogs() {
  info.value = ''
  logs.value = []
  loading.value = true
  try {
    const r = await api.get('/modifications_date', {
      params: { start_date: start.value, end_date: end.value },
    })
    logs.value = r.data || []
    if (!logs.value.length) info.value = 'No modifications available for the selected range.'
  } catch (e: any) {
    info.value = e?.message || 'Error loading data.'
  } finally {
    loading.value = false
  }
}

function visualize() {
  const triples: string[] = []
  for (const l of logs.value) {
    const user = encodeURIComponent(l.user || 'anonymous')
    const change = encodeURIComponent(l.log_id)
    triples.push(`<https://user/${user}> <https://action/made> <https://change/${change}> .`)
  }
  graphTTL.value = triples.join('\n')
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

.centered { display: flex; flex-direction: column; align-items: center; text-align: center; }

.description { color: #555; font-size: 1.10rem; margin-bottom: 2rem; max-width: 48rem; }

.row { display: flex; gap: 12px; align-items: end; margin-bottom: 2rem; flex-wrap: wrap; }
.field { display: flex; flex-direction: column; gap: .5rem; }

.label {
  font-family: 'Montserrat', sans-serif;
  font-weight: 600;
  color: #333;
  display: flex;
  align-items: center;
  justify-content: center;
}

.in {
  padding: 10px 12px;
  border: 1px solid #d0d7de;
  border-radius: 10px;
  background: #fff;
  font-size: 1rem;
  transition: border-color .2s ease, box-shadow .2s ease;
}
.in:focus { outline: none; border-color: var(--brand); box-shadow: 0 0 0 4px rgba(0,169,224,.15); }

.actions { display: flex; gap: .8rem; flex-wrap: wrap; justify-content: center; margin-bottom: 1rem; }

.info {
  background: #cce5ff;
  color: #004085;
  border: 2px solid #b8daff;
  padding: .8rem 1rem;
  border-radius: 10px;
  margin-top: .8rem;
  text-align: center;
  font-size: .95rem;
}

.log-card { width: 100%; }

.code.block {
  margin-top: .6rem;
  border-radius: 12px;
  padding: 1rem;
  background: #0b0f17;
  color: #cde;
  overflow: auto;
  max-width: 100%;
  text-align: left;
}
</style>
