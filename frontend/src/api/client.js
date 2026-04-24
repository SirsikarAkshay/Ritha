// src/api/client.js — fetch-based HTTP client with JWT auto-refresh

// VITE_API_BASE_URL is injected at build time. Defaults to '/api' so dev
// (Vite proxy) and same-origin prod deploys keep working without config.
const BASE = (import.meta.env?.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

// ── Token helpers ─────────────────────────────────────────────────────────
const getToken    = ()      => localStorage.getItem('gg_access')
const getRefresh  = ()      => localStorage.getItem('gg_refresh')
const setTokens   = (a, r)  => {
  localStorage.setItem('gg_access', a)
  localStorage.setItem('gg_refresh', r)
}
const clearTokens = () => {
  localStorage.removeItem('gg_access')
  localStorage.removeItem('gg_refresh')
}

class ApiError extends Error {
  constructor(status, data, statusText) {
    const msg =
      data?.error?.message ||
      data?.detail ||
      statusText ||
      `Request failed with status ${status}`
    super(msg)
    this.name = 'ApiError'
    this.response = { status, data, statusText }
  }
}

const isFormData = (body) =>
  typeof FormData !== 'undefined' && body instanceof FormData

async function parseBody(res) {
  if (res.status === 204) return null
  const contentType = res.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    try { return await res.json() } catch { return null }
  }
  const text = await res.text()
  return text || null
}

async function doFetch(method, url, body) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let payload
  if (body === undefined || body === null) {
    payload = undefined
  } else if (isFormData(body)) {
    payload = body  // let browser set multipart boundary
  } else {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  return fetch(`${BASE}${url}`, { method, headers, body: payload })
}

// ── Refresh coordination ──────────────────────────────────────────────────
// Share a single in-flight refresh across concurrent 401s.
let refreshPromise = null
function refreshAccessToken() {
  if (refreshPromise) return refreshPromise
  const refresh = getRefresh()
  if (!refresh) return Promise.resolve(null)

  refreshPromise = (async () => {
    try {
      const r = await fetch(`${BASE}/auth/refresh/`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ refresh }),
      })
      if (!r.ok) return null
      const data = await r.json()
      setTokens(data.access, data.refresh || refresh)
      return data.access
    } catch {
      return null
    }
  })().finally(() => { refreshPromise = null })

  return refreshPromise
}

// ── Core request with 401 → refresh → retry ───────────────────────────────
async function request(method, url, body) {
  let res = await doFetch(method, url, body)

  if (res.status === 401) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      res = await doFetch(method, url, body)
    } else {
      clearTokens()
      if (typeof window !== 'undefined') window.location.href = '/login'
    }
  }

  const data = await parseBody(res)
  if (!res.ok) throw new ApiError(res.status, data, res.statusText)
  return data
}

export const api = {
  get:    (url)       => request('GET',    url),
  post:   (url, body) => request('POST',   url, body),
  put:    (url, body) => request('PUT',    url, body),
  patch:  (url, body) => request('PATCH',  url, body),
  delete: (url)       => request('DELETE', url),

  // Token helpers — kept on the object for any call site that reaches in.
  getToken,
  getRefresh,
  setTokens,
  clearTokens,
}

export default api
