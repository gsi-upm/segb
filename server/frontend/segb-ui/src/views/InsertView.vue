<template>
  <section class="card">
    <h1 class="title">📝 Insert Semantic Log</h1>

    <div class="centered">
      <p class="description">
        Register a semantic event in <strong>Turtle (TTL)</strong> format. The user field is optional.
      </p>
    </div>

    <div class="field">
      <label class="label" for="ttl">TTL Content</label>
      <textarea
        id="ttl"
        v-model="ttl"
        class="textarea"
        rows="14"
        placeholder="# Insert your Turtle content here"
      ></textarea>
      <small class="hint">Tip: use prefixes and validate the syntax before submitting.</small>
    </div>

    <div class="field">
      <label class="label" for="user">User (optional)</label>
      <input
        id="user"
        v-model="user"
        class="input"
        placeholder="user@domain"
      />
    </div>

    <div class="actions centered">
      <button class="btn primary" @click="submit" :disabled="loading">
        {{ loading ? 'Sending…' : 'Insert Semantic Log' }}
      </button>
    </div>

    <transition name="fade">
      <pre v-if="result" class="code block">{{ result }}</pre>
    </transition>

    <p v-if="err" class="alert error">{{ err }}</p>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '@/api/client'

const ttl = ref('')
const user = ref('')
const result = ref('')
const err = ref('')
const loading = ref(false)

async function submit() {
  err.value = ''
  result.value = ''
  loading.value = true
  try {
    const { data, status } = await api.post('/ttl', {
      ttl_content: ttl.value,
      user: user.value || undefined,
    })
    if (status === 201) result.value = JSON.stringify(data, null, 2)
  } catch (e: any) {
    err.value = e?.response?.data?.detail || e?.message || 'Unexpected error'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&display=swap');

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

.description {
  color: #555;
  font-size: 1.10rem; 
  margin-bottom: 1rem;
  max-width: 48rem;
}

.subtitle {
  color: #444;
  margin: 0 0 1.5rem 0;
  line-height: 1.5;
}

.field {
  display: flex;
  flex-direction: column;
  gap: .5rem;
  margin-bottom: 1rem;
  margin-right: 2rem;
}

.label {
  margin-top: 0.5rem;
  color: #333;
  font-weight: 600;
}

.input,
.textarea {
  width: 100%;
  border: 1px solid #d0d7de;
  border-radius: 10px;
  padding: .9rem 1rem;
  font-size: 1rem;
  transition: border-color .2s ease, box-shadow .2s ease;
  background: #fff;
  margin-bottom: 2rem;
}

.textarea {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  line-height: 1.35;
}

.input:focus,
.textarea:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 4px rgba(0, 169, 224, 0.15);
}

.hint {
  color: #666;
  font-size: .9rem;
  margin-bottom: 0.5rem;
}

.actions {
  display: flex;
  gap: .8rem;
  margin-top: .5rem;
}

.code.block {
  margin-top: 1rem;
  border-radius: 12px;
  padding: 1rem;
  background: #0b0f17;
  color: #cde;
  overflow: auto;
}

.alert.error {
  margin-top: 1rem;
  background: #f8d7da;
  color: #721c24;
  border: 2px solid #f5c6cb;
  padding: .9rem 1rem;
  border-radius: 10px;
  text-align: left;
}

.centered { display: flex; flex-direction: column; align-items: center; text-align: center; }

.fade-enter-active, .fade-leave-active { transition: opacity .18s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

</style>
