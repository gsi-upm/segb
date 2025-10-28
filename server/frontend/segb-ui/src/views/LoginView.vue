<template>
  <section class="login-container centered">
    <h1 class="login-title">🔐 Access Portal</h1>

    
    <input
      id="token"
      v-model="token"
      type="password"
      class="login-input"
      placeholder="Enter your secure token"
    />

    <button class="btn primary" @click="doLogin">Login</button>

    <p v-if="err" class="login-error">{{ err }}</p>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const token = ref('')
const err = ref('')

function doLogin() {
  if (!token.value) {
    err.value = 'Please enter your token.'
    return
  }
  auth.login(token.value)
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600&display=swap');

.login-container {
  max-width: 50rem;
  margin: 80px auto;
  padding: 2rem 2.5rem;
  background: rgba(255, 255, 255, 0.9);
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

.login-title {
  text-align: center;
  color: var(--brand-dark);
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
  letter-spacing: 0.5px;
}

.login-input {
  width: calc(100% - 2rem);
  padding-inline: 1rem;
  padding-block: 0.8rem;
  font-size: 1rem;
  border-radius: 8px;
  border: 1px solid #ccc;
  transition: border-color 0.25s ease, box-shadow 0.25s ease;
  margin-bottom: 2rem;
}

.login-input:focus {
  border-color: var(--brand);
  outline: none;
  box-shadow: 0 0 6px rgba(0, 169, 224, 0.4);
}

.login-error {
  margin-top: 1rem;
  color: #721c24;
  background: #f8d7da;
  border: 2px solid #f5c6cb;
  padding: 0.8rem;
  border-radius: 8px;
  font-size: 0.95rem;
  text-align: center;
}
</style>
