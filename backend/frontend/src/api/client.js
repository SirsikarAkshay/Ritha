// src/api/client.js
import axios from 'axios'

const BASE = '/api'
const instance = axios.create({ baseURL: BASE })

instance.getToken    = ()      => localStorage.getItem('gg_access')
instance.getRefresh  = ()      => localStorage.getItem('gg_refresh')
instance.setTokens   = (a, r) => {
  localStorage.setItem('gg_access', a)
  localStorage.setItem('gg_refresh', r)
}
instance.clearTokens = () => {
  localStorage.removeItem('gg_access')
  localStorage.removeItem('gg_refresh')
}

instance.interceptors.request.use(cfg => {
  const token = instance.getToken()
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

instance.interceptors.response.use(
  res => res.data,
  async err => {
    const orig   = err.config
    const status = err.response?.status
    const url    = orig?.url || ''

    const isAuthUrl = [
      '/auth/login/', '/auth/register/', '/auth/refresh/',
      '/auth/forgot-password/', '/auth/reset-password/',
      '/auth/verify-email/', '/auth/resend-verification/',
      '/api/config', 'config',
    ].some(p => url.includes(p))

    if (status === 401 && !orig._retry && !isAuthUrl) {
      orig._retry = true
      const refresh = instance.getRefresh()
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE}/auth/refresh/`, { refresh })
          instance.setTokens(data.access, data.refresh || refresh)
          instance.defaults.headers.common.Authorization = `Bearer ${data.access}`
          return instance(orig)
        } catch {
          instance.clearTokens()
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(err)
  }
)

export { instance as api }
export default instance
