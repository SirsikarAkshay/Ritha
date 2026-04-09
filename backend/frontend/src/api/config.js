// frontend/src/api/config.js
// Fetches /api/config safely — never throws, always returns an object

const DEFAULT_CONFIG = {
  auth_trusted_header:     null,
  google_oauth_enabled:    false,
  microsoft_oauth_enabled: false,
  mistral_enabled:         false,
  email_verification:      true,
  version:                 '1.0.0',
  environment:             'development',
}

let _config = null

export async function loadConfig() {
  if (_config) return _config
  try {
    const res = await fetch('/api/config', { headers: { Accept: 'application/json' } })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    _config = { ...DEFAULT_CONFIG, ...data }
  } catch (err) {
    console.warn('[Arokah] Could not load /api/config, using defaults:', err.message)
    _config = { ...DEFAULT_CONFIG }
  }
  return _config
}

export function getConfig() {
  return _config || DEFAULT_CONFIG
}
