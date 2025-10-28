<template>
  <header class="app-header">
    <h1 class="title">SEGB Knowledge Hub</h1>
    <div class="spacer" />
    <button class="btn" @click="handleClick">
      {{ isLoggedIn ? 'Logout' : 'Login' }}
    </button>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

const isLoggedIn = computed(() => !!auth.token)

function handleClick() {
  if (isLoggedIn.value) {
    auth.logout()
  } else {
    router.push({ name: 'login' })
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@600&display=swap');

.app-header {
  background: linear-gradient(90deg, #001f3f 0%, #004080 100%);
  border-bottom: 4px solid #007acc;
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  font-family: 'Montserrat', sans-serif;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.title {
  color: #ffffff;
  font-size: 3rem;
  font-weight: 800;
  letter-spacing: 1px;
  text-shadow: 1px 1px 4px rgba(0, 0, 0, 0.6);
  margin: 0;
}

.spacer {
  flex: 1;
}

.btn {
  background: #ffffff;
  color: #004080;
  border: none;
  border-radius: 8px;
  padding: 15px 25px;
  margin-right: 2rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.btn:hover {
  background: #e6f0ff;
}
</style>
