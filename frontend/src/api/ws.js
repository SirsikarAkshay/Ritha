// src/api/ws.js
// Lightweight WebSocket wrapper that:
//   - appends the JWT access token as ?token=
//   - auto-reconnects with exponential backoff
//   - exposes a simple .on(event, handler) / .off() / .close() API
//
// Usage:
//   const ws = connectWebSocket('/ws/chat/42/')
//   ws.on('message', (payload) => { ... })
//   ws.on('close',   () => { ... })
//   ws.close()

const ACCESS_KEY = 'gg_access'  // Matches the key used elsewhere in the app

function buildUrl(path) {
  const token = localStorage.getItem(ACCESS_KEY) || ''

  // Prod: VITE_WS_BASE_URL (e.g. wss://api.ritha.com) is set at build time.
  // Dev: fall back to current host on :8000 (Vite doesn't proxy WS).
  const explicit = import.meta.env?.VITE_WS_BASE_URL
  if (explicit) {
    const base = explicit.replace(/\/$/, '')
    return `${base}${path}?token=${encodeURIComponent(token)}`
  }

  const isHttps = typeof window !== 'undefined' && window.location?.protocol === 'https:'
  const proto = isHttps ? 'wss:' : 'ws:'
  const host = (typeof window !== 'undefined' && window.location?.hostname) || 'localhost'
  return `${proto}//${host}:8000${path}?token=${encodeURIComponent(token)}`
}

export function connectWebSocket(path, { maxRetries = 10 } = {}) {
  const handlers = { message: [], open: [], close: [], error: [] }
  let socket = null
  let retries = 0
  let closedByUser = false
  let reconnectTimer = null

  const emit = (event, payload) => {
    (handlers[event] || []).forEach(fn => {
      try { fn(payload) } catch (e) { console.error(`[ws] handler for ${event} threw:`, e) }
    })
  }

  const open = () => {
    if (closedByUser) return
    try {
      socket = new WebSocket(buildUrl(path))
    } catch (e) {
      console.error('[ws] failed to construct WebSocket:', e)
      return
    }

    socket.onopen = () => {
      retries = 0
      emit('open')
    }
    socket.onmessage = (ev) => {
      let data
      try { data = JSON.parse(ev.data) } catch { data = ev.data }
      emit('message', data)
    }
    socket.onerror = (ev) => emit('error', ev)
    socket.onclose = (ev) => {
      emit('close', ev)
      if (closedByUser || retries >= maxRetries) return
      const delay = Math.min(30000, 500 * Math.pow(2, retries))
      retries += 1
      reconnectTimer = setTimeout(open, delay)
    }
  }

  open()

  return {
    on(event, fn) {
      if (!handlers[event]) handlers[event] = []
      handlers[event].push(fn)
      return this
    },
    off(event, fn) {
      if (!handlers[event]) return
      handlers[event] = handlers[event].filter(h => h !== fn)
    },
    send(data) {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(typeof data === 'string' ? data : JSON.stringify(data))
      }
    },
    close() {
      closedByUser = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      if (socket) socket.close()
    },
  }
}
