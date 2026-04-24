"""
Fixes the blank page crash:
  "Cannot read properties of undefined (reading 'auth_trusted_header')"

Run from your project root (where manage.py is):
  python fix_blank_page.py
"""
import os, sys, subprocess
from pathlib import Path

if not os.path.exists('manage.py'):
    print("❌ Run this from your project root (where manage.py is)")
    sys.exit(1)

print("=" * 55)
print("Ritha — Fix blank page / auth_trusted_header crash")
print("=" * 55)

# ─────────────────────────────────────────────────────────
# STEP 1: Add /api/config endpoint to backend
# ─────────────────────────────────────────────────────────
print("\n[1/4] Adding /api/config endpoint...")

Path('ritha/config_view.py').write_text('''from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


class ConfigView(APIView):
    """GET /api/config — public config the frontend reads on startup."""
    permission_classes    = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({
            "auth_trusted_header":     None,
            "google_oauth_enabled":    bool(getattr(settings, "GOOGLE_CLIENT_ID", "")),
            "microsoft_oauth_enabled": bool(getattr(settings, "MICROSOFT_CLIENT_ID", "")),
            "mistral_enabled":         bool(getattr(settings, "MISTRAL_API_KEY", "")),
            "email_verification":      True,
            "version":                 "1.0.0",
            "environment":             "development" if settings.DEBUG else "production",
        })
''')
print("   ✅ Created ritha/config_view.py")

urls_path = Path('ritha/urls.py')
urls = urls_path.read_text()

if 'ConfigView' not in urls:
    urls = urls.replace(
        'from ritha.health import HealthCheckView',
        'from ritha.health import HealthCheckView\nfrom ritha.config_view import ConfigView'
    )
    urls = urls.replace(
        "path('api/health/",
        "path('api/config',   ConfigView.as_view(),   name='config'),\n    path('api/health/"
    )
    urls_path.write_text(urls)
    print("   ✅ Wired /api/config into urls.py")
else:
    print("   ✅ /api/config already in urls.py")

# ─────────────────────────────────────────────────────────
# STEP 2: Patch frontend source — make config fetch safe
# ─────────────────────────────────────────────────────────
print("\n[2/4] Patching frontend source files...")

# Fix client.js — stop 401 redirect loop on login endpoint
client_js = Path('frontend/src/api/client.js')
if client_js.exists():
    client_js.write_text('''// src/api/client.js
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
''')
    print("   ✅ client.js patched")

# Fix App.jsx — wrap config fetch so it never crashes the app
app_jsx = Path('frontend/src/App.jsx')
if app_jsx.exists():
    content = app_jsx.read_text()

    # If App.jsx fetches /api/config, make it safe
    if 'api/config' in content or 'auth_trusted_header' in content:
        # Wrap any existing config fetch in a try/catch
        content = content.replace(
            "fetch('/api/config')",
            "fetch('/api/config').catch(() => ({ json: () => Promise.resolve({}) }))"
        )
        # Make any .auth_trusted_header access safe
        content = content.replace(
            '.auth_trusted_header',
            '?.auth_trusted_header'
        )
        app_jsx.write_text(content)
        print("   ✅ App.jsx config fetch made safe")
    else:
        print("   ℹ  App.jsx doesn't fetch config directly")

# Fix main.jsx or index.js — anywhere config is loaded
for fname in ['frontend/src/main.jsx', 'frontend/src/main.js',
              'frontend/src/index.jsx', 'frontend/src/index.js']:
    p = Path(fname)
    if p.exists():
        content = p.read_text()
        if 'auth_trusted_header' in content:
            content = content.replace('.auth_trusted_header', '?.auth_trusted_header')
            p.write_text(content)
            print(f"   ✅ {fname} patched")

# Search ALL jsx/js files for auth_trusted_header and make safe
src_dir = Path('frontend/src')
if src_dir.exists():
    for f in src_dir.rglob('*.jsx'):
        text = f.read_text()
        if 'auth_trusted_header' in text and '?.auth_trusted_header' not in text:
            fixed = text.replace('.auth_trusted_header', '?.auth_trusted_header')
            f.write_text(fixed)
            print(f"   ✅ Fixed {f.relative_to(src_dir.parent)}")
    for f in src_dir.rglob('*.js'):
        if 'node_modules' in str(f): continue
        text = f.read_text()
        if 'auth_trusted_header' in text and '?.auth_trusted_header' not in text:
            fixed = text.replace('.auth_trusted_header', '?.auth_trusted_header')
            f.write_text(fixed)
            print(f"   ✅ Fixed {f.relative_to(src_dir.parent)}")

# ─────────────────────────────────────────────────────────
# STEP 3: Write a safe config loader that any component can use
# ─────────────────────────────────────────────────────────
print("\n[3/4] Writing safe config loader...")

config_loader = Path('frontend/src/api/config.js')
config_loader.write_text('''// frontend/src/api/config.js
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
    console.warn('[Ritha] Could not load /api/config, using defaults:', err.message)
    _config = { ...DEFAULT_CONFIG }
  }
  return _config
}

export function getConfig() {
  return _config || DEFAULT_CONFIG
}
''')
print("   ✅ Created frontend/src/api/config.js")

# ─────────────────────────────────────────────────────────
# STEP 4: Django check + rebuild frontend
# ─────────────────────────────────────────────────────────
print("\n[4/4] Verifying and rebuilding...")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ritha.settings')
try:
    import django
    django.setup()
    from django.test import Client
    import json as _json
    c = Client(SERVER_NAME='localhost')
    r = c.get('/api/config')
    data = _json.loads(r.content)
    assert r.status_code == 200
    assert 'auth_trusted_header' in data
    print(f"   ✅ GET /api/config → 200, auth_trusted_header={data['auth_trusted_header']!r}")
except Exception as e:
    print(f"   ⚠  Backend test failed: {e}")
    print("      Make sure you restart the server after this script finishes")

# Rebuild
frontend_dir = Path('frontend')
if frontend_dir.exists() and (frontend_dir / 'package.json').exists():
    print("   Building frontend (this takes ~10 seconds)...")
    r = subprocess.run(['npm', 'run', 'build'], capture_output=True, text=True, cwd='frontend')
    if r.returncode == 0:
        print("   ✅ Frontend rebuilt successfully")
    else:
        print("   ❌ Build failed:")
        print(r.stdout[-800:] if r.stdout else '')
        print(r.stderr[-400:] if r.stderr else '')
        print("   Fix errors above, then run: cd frontend && npm run build")
else:
    print("   ⚠  frontend/ not found — run 'cd frontend && npm run build' manually")

print()
print("=" * 55)
print("✅ Done! Follow these steps:")
print()
print("  1. Restart the backend:")
print("       python manage.py runserver")
print()
print("  2. In a second terminal, start the frontend:")
print("       cd frontend && npm run dev")
print()
print("  3. Open http://localhost:3000")
print()
print("  When you sign up, look in Terminal 1 for:")
print("  'Verify your email: http://localhost:3000/verify-email?token=...'")
print("  Copy that URL and open it to verify your account.")
print("=" * 55)