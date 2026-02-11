import { defineStore } from 'pinia'
import router from '../router'

interface AuthState {
  token: string | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem('segb_token') || null,
  }),

  actions: {
    login(token: string) {
      this.token = token
      localStorage.setItem('segb_token', token)
      router.push({ name: 'home' })
    },

    logout() {
      this.token = null
      localStorage.removeItem('segb_token')
      router.push({ name: 'login' })
    },
  },
})
