<template>
    <section>
        <h2>『💬』AI Assistant</h2>
        <input v-model="question" placeholder="Ask something about the events graph" class="in" />
        <input v-model="reference" placeholder="Reference answer (optional - needed for evaluation)" class="in" />
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-top:8px">
            <button class="btn" @click="ask">🤖 Obtener respuesta</button>
            <button class="btn" @click="askEval">📊 Responder + Evaluar</button>
            <label class="btn" for="file">📂 Evaluar JSON</label>
            <input id="file" type="file" accept="application/json" style="display:none" @change="loadJson" />
        </div>


        <h3 v-if="answer">Assistant Response</h3>
        <pre v-if="answer" class="code">{{ answer }}</pre>


        <h3 v-if="metrics">Evaluation Metrics</h3>
        <pre v-if="metrics" class="code">{{ metrics }}</pre>


        <div v-if="dataset">
            <button class="btn primary" @click="runBatch">🚀 Run batch evaluation</button>
        </div>


        <div v-if="batchResult">
            <h3>Averages</h3>
            <pre class="code">{{ JSON.stringify(batchResult.averages, null, 2) }}</pre>
            <h3>Per-item results</h3>
            <pre class="code">{{ JSON.stringify(batchResult.results, null, 2) }}</pre>
        </div>


        <div style="margin-top:10px"><button class="btn" @click="$router.push({ name: 'home' })">🔙</button></div>
    </section>
</template>

 <script setup>
import { ref } from 'vue'
import api from '@/api/client'


const question = ref('')
const reference = ref('')
const answer = ref('')
const metrics = ref('')
const dataset = ref(null)
const batchResult = ref(null)


async function ask() {
    const r = await api.post('/rag/ask', { question: question.value })
    answer.value = r.data?.answer || 'No answer returned.'
}


async function askEval() {
    if (!question.value || !reference.value) { alert('You must enter both the question and the reference answer.'); return }
    const r = await api.post('/rag/evaluate', { question: question.value, reference: reference.value })
    const { answer: ans, ...rest } = r.data
    answer.value = ans
    metrics.value = JSON.stringify(rest, null, 2)
}


function loadJson(ev) {
    const file = ev.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => { dataset.value = JSON.parse(reader.result) }
    reader.readAsText(file)
}


async function runBatch() {
    const r = await api.post('/rag/evaluate_batch', { dataset: dataset.value })
    batchResult.value = r.data
}
</script>



<style scoped>
    .in {
        width: 100%;
        padding: 8px;
        border: 1px solid #ccc;
        border-radius: 8px;
        margin-top: 6px
    }
</style>
