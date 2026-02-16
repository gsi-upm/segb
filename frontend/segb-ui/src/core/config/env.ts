const DEFAULT_API_URL = '/api'

export const env = {
  apiBaseUrl: String(import.meta.env.VITE_API_URL || DEFAULT_API_URL),
  requestTimeoutMs: 20000,
  tokenStorageKey: 'segb_token',
}
