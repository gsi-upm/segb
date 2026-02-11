import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/stores/auth'

const baseURL = import.meta.env.VITE_API_URL || '/api'
const api: AxiosInstance = axios.create({ baseURL })

api.interceptors.request.use((cfg: InternalAxiosRequestConfig) => {
  const auth = useAuthStore()
  cfg.headers = cfg.headers ?? {}
  if (auth.token) {
    (cfg.headers as any).Authorization = `Bearer ${auth.token}`
  }
  return cfg
})

export default api