import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

import { env } from '@/core/config/env'
import { useSessionStore } from '@/core/auth/sessionStore'

const httpClient: AxiosInstance = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: env.requestTimeoutMs,
  headers: {
    Accept: 'application/json, text/plain, text/turtle',
  },
})

httpClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const session = useSessionStore()
  const token = session.token.trim()

  config.headers = config.headers ?? {}
  if (token.length > 0) {
    config.headers.Authorization = `Bearer ${token}`
  } else if ('Authorization' in config.headers) {
    delete config.headers.Authorization
  }

  return config
})

export default httpClient
