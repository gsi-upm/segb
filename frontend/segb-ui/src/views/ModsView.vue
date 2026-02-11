<template>
  <section class="card centered">
    <h1 class="title">🔄 View Modification Logs</h1>
    <p class="description">
      Inspect recent changes to the knowledge base. Filter by limit, visualize relationships, and drill down by user.
    </p>

    <div class="actions" style="margin-bottom:4rem;">
      <label class="label" for="limit">Limit</label>
      <input id="limit" type="number" v-model.number="limit" min="1" max="100" class="in" />
      <button class="btn primary" @click="load" :disabled="loading">
        {{ loading ? 'Loading…' : 'Load Modifications' }}
      </button>
    </div>

    <p v-if="info" class="info">{{ info }}</p>

    <div v-for="log in logs" :key="log.log_id" class="log-card">
      <pre class="code block">{{ log }}</pre>
    </div>

    <h2 class="subtitle" style="margin-top:1rem;">
      <span class="emoji">🖧</span> Historical Graph Visualization
    </h2>
    <p class="description">
      Visualize the modification logs linear graph.
    </p>
    <div class="actions">
      <button class="btn primary" @click="visualize">Visualize Graph</button>
    </div>
    <GraphViewer v-if="graphTTL" :ttl="graphTTL" style="margin-top:1rem" />

    <div v-if="users.length" class="users">
      <h2 class="subtitle" style="margin-top:2rem;">👤 Users – Select to view their logs</h2>
      <div class="actions">
        <button class="btn" v-for="u in users" :key="u" @click="selectUser(u)">{{ u }}</button>
      </div>

      <div v-if="selectedUser" class="user-logs">
        <h3 class="subtitle">Logs for user: {{ selectedUser }}</h3>
        <div class="actions">
          <button class="btn" v-for="l in userLogs" :key="l.log_id" @click="selectLog(l.log_id)">
            {{ l.log_id }}
          </button>
        </div>
      </div>

      <div v-if="selectedLog" class="ttl-view">
        <h3 class="subtitle">Log ID: {{ selectedLog }}</h3>
        <textarea class="ta" :value="ttlOfSelected" rows="12" readonly></textarea>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import api from '@/api/client'
import GraphViewer from '@/components/GraphViewer.vue'

type ModLog = {
  log_id: string
  user?: string
  ttl_content?: string
  [k: string]: any
}

const limit = ref(10)
const logs = ref<ModLog[]>([])
const info = ref('')
const graphTTL = ref('')
const loading = ref(false)

const grouped = computed(() => {
  const m = new Map<string, ModLog[]>()
  for (const l of logs.value) {
    const u = l.user || 'Unknown'
    if (!m.has(u)) m.set(u, [])
    m.get(u)!.push(l)
  }
  return m
})
const users = computed(() => Array.from(grouped.value.keys()))
const selectedUser = ref('')
const selectedLog = ref('')

const userLogs = computed(() => grouped.value.get(selectedUser.value) || [])
const ttlOfSelected = computed(() => userLogs.value.find(x => x.log_id === selectedLog.value)?.ttl_content || '')

async function load() {
  info.value = ''
  logs.value = []
  loading.value = true
  try {
    const r = await api.get('/modifications', { params: { limit: limit.value } })
    logs.value = r.data || []
    if (!logs.value.length) info.value = 'No modifications have been made.'
  } catch (e: any) {
    info.value = e?.message || 'Error loading modifications.'
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

function selectUser(u: string) {
  selectedUser.value = u
  selectedLog.value = ''
}
function selectLog(id: string) {
  selectedLog.value = id
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&display=swap');

.emoji { color: #ff9900; font-weight: normal; }


.description { color: #555; font-size: 1.10rem; margin-bottom: 2rem; max-width: 48rem; }

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

.in {
  width: 180px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #d0d7de;
  background: #fff;
  font-size: 1rem;
  transition: border-color .2s ease, box-shadow .2s ease;
}
.in:focus { outline: none; border-color: var(--brand); box-shadow: 0 0 0 4px rgba(0,169,224,.15); }

.ta {
  width: 100%;
  border-radius: 10px;
  padding: 10px 12px;
  border: 1px solid #d0d7de;
  background: #fff;
  min-height: 220px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}

.label {
  font-family: 'Montserrat', sans-serif;
  font-weight: 600;
  color: #333;
  display: flex;
  align-items: center; 
  justify-content: center;
  font-size: 1rem;
  margin-right: 0.5rem;
}

.users, .user-logs, .ttl-view { width: 100%; }

.fade-enter-active, .fade-leave-active { transition: opacity .18s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
