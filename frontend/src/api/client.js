// src/api/client.js — singleton axios instance with token management
import axios from 'axios'

const BASE = '/api'

const instance = axios.create({ baseURL: BASE })

// ── Token helpers ─────────────────────────────────────────────────────────
instance.getToken    = ()       => localStorage.getItem('gg_access')
instance.getRefresh  = ()       => localStorage.getItem('gg_refresh')
instance.setTokens   = (a, r)  => {
  localStorage.setItem('gg_access', a)
  localStorage.setItem('gg_refresh', r)
}
instance.clearTokens = ()       => {
  localStorage.removeItem('gg_access')
  localStorage.removeItem('gg_refresh')
}

// ── Inject access token ───────────────────────────────────────────────────
instance.interceptors.request.use(cfg => {
  const token = instance.getToken()
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

// ── Auto-refresh on 401 ───────────────────────────────────────────────────
instance.interceptors.response.use(
  res => res.data,           // unwrap .data so callers get the payload directly
  async err => {
    const orig = err.config
    if (err.response?.status === 401 && !orig._retry) {
      orig._retry = true
      const refresh = instance.getRefresh()
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE}/auth/refresh/`, { refresh })
          instance.setTokens(data.access, data.refresh || refresh)
          orig.headers.Authorization = `Bearer ${data.access}`
          return instance(orig)
        } catch {
          instance.clearTokens()
          window.location.href = '/login'
        }
      }
    }
    // Normalise error so callers can do err.response?.data?.error
    return Promise.reject(err)
  }
)

export { instance as api }
export default instance
