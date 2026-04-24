"""
Fixes the frontend auth error display so users see clear messages.

Run from your project root:  python fix_auth_frontend.py

What this fixes:
  - 403 after signup: shows "check your email" message instead of blank/broken
  - 401 wrong password: shows "incorrect credentials" message
  - Error messages appear inline in the form, not just in the console
"""
import os, sys
from pathlib import Path

if not os.path.exists('manage.py'):
    print("❌ Run this from your project root (where manage.py is)")
    sys.exit(1)

# ── Fix 1: src/api/client.js ─────────────────────────────────────────────
# The Axios interceptor was redirecting to /login on 401, even when
# the 401 was FROM the login endpoint itself (wrong password).
# That caused a silent redirect loop instead of showing the error.

client_js = Path('frontend/src/api/client.js')
if client_js.exists():
    content = client_js.read_text()
    if 'isAuthEndpoint' not in content:
        print("⚠  client.js missing isAuthEndpoint guard — rewriting")
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
    const orig    = err.config
    const status  = err.response?.status
    const url     = orig?.url || ''

    // Never try to refresh tokens when the error is FROM an auth endpoint.
    // Doing so causes a silent redirect loop instead of showing the error.
    const isAuthUrl = [
      '/auth/login/', '/auth/register/', '/auth/refresh/',
      '/auth/forgot-password/', '/auth/reset-password/',
      '/auth/verify-email/', '/auth/resend-verification/',
      '/api/config',
    ].some(path => url.includes(path))

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
        print("✅ client.js fixed")
    else:
        print("✅ client.js already has the fix")
else:
    print("⚠  frontend/src/api/client.js not found — skipping")

# ── Fix 2: src/hooks/useAuth.jsx ─────────────────────────────────────────
use_auth = Path('frontend/src/hooks/useAuth.jsx')
if use_auth.exists():
    use_auth.write_text('''// src/hooks/useAuth.jsx
import { createContext, useContext, useState, useEffect, useCallback } from \'react\'
import { auth as authApi } from \'../api/index.js\'
import { api } from \'../api/client.js\'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null)
  const [loading, setLoading] = useState(true)

  const loadUser = useCallback(async () => {
    if (!localStorage.getItem(\'gg_access\')) { setLoading(false); return }
    try {
      const me = await authApi.me()
      setUser(me)
    } catch {
      api.clearTokens()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadUser() }, [loadUser])

  const login = async (email, password) => {
    // Throws on 401 (wrong creds) or 403 (unverified) — let LoginPage handle it
    const data = await authApi.login({ email, password })
    api.setTokens(data.access, data.refresh)
    const me = await authApi.me()
    setUser(me)
    return me
  }

  const logout = async () => {
    const refresh = localStorage.getItem(\'gg_refresh\')
    try { if (refresh) await authApi.logout(refresh) } catch {}
    api.clearTokens()
    setUser(null)
  }

  const updateUser = (updates) => setUser(u => ({ ...u, ...updates }))

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, updateUser, reload: loadUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error(\'useAuth must be used within AuthProvider\')
  return ctx
}
''')
    print("✅ useAuth.jsx rewritten")
else:
    print("⚠  frontend/src/hooks/useAuth.jsx not found")

# ── Fix 3: Replace LoginPage with a clean, minimal version ───────────────
login_page = Path('frontend/src/pages/LoginPage.jsx')

NEW_LOGIN = r'''// src/pages/LoginPage.jsx
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import { auth as authApi } from '../api/index.js'

// ── Post-register: "check your inbox" screen ─────────────────────────────
function CheckEmailScreen({ email }) {
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)

  const resend = async () => {
    setBusy(true)
    try {
      await fetch('/api/auth/resend-verification/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      setSent(true)
    } finally { setBusy(false) }
  }

  return (
    <div style={page}>
      <div style={panel}>
        <Logo />
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: 16 }}>📬</div>
          <h2 style={{ ...heading, marginBottom: 8 }}>Check your email</h2>
          <p style={{ ...sub, marginBottom: 4 }}>We sent a verification link to</p>
          <p style={{ ...sub, color: '#D4724A', fontWeight: 600, marginBottom: 24 }}>{email}</p>
          <p style={{ ...sub, marginBottom: 32 }}>
            Click the link in the email to activate your account. It expires in 24 hours.
          </p>
          <hr style={divider} />
          {sent
            ? <p style={{ ...sub, color: '#7BA688', marginTop: 16 }}>✓ Resent — check your inbox</p>
            : (
              <div style={{ marginTop: 16 }}>
                <p style={{ ...sub, marginBottom: 8 }}>Didn't receive it?</p>
                <button style={btnSecondary} onClick={resend} disabled={busy}>
                  {busy ? 'Sending…' : 'Resend verification email'}
                </button>
              </div>
            )
          }
          <p style={{ marginTop: 24, fontSize: 12, color: '#B8B0A0' }}>
            Already verified?{' '}
            <a href="/login" style={{ color: '#D4724A' }}>Sign in →</a>
          </p>
        </div>
      </div>
    </div>
  )
}

// ── Main login / register page ────────────────────────────────────────────
export default function LoginPage() {
  const [mode,          setMode]          = useState('login')
  const [email,         setEmail]         = useState('')
  const [password,      setPassword]      = useState('')
  const [firstName,     setFirstName]     = useState('')
  const [loading,       setLoading]       = useState(false)
  const [error,         setError]         = useState('')
  const [unverified,    setUnverified]    = useState('')   // email that needs verification
  const [registered,    setRegistered]    = useState('')   // email just registered

  const { login } = useAuth()
  const navigate  = useNavigate()

  const switchMode = (m) => { setMode(m); setError(''); setUnverified('') }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setUnverified('')
    setLoading(true)

    try {
      if (mode === 'register') {
        await authApi.register({
          email: email.trim().toLowerCase(),
          password,
          first_name: firstName.trim(),
        })
        setRegistered(email.trim().toLowerCase())
        return   // show email-sent screen — do NOT try to login
      }

      // Login
      await login(email.trim().toLowerCase(), password)
      navigate('/')

    } catch (err) {
      const errData = err?.response?.data?.error

      if (errData?.code === 'email_not_verified') {
        // User tried to log in before verifying their email
        setUnverified(errData.email || email)
        setError('Please verify your email address before signing in.')

      } else if (errData?.code === 'authentication_failed' || err?.response?.status === 401) {
        setError('Incorrect email or password.')

      } else if (errData?.code === 'validation_error') {
        // Field-level errors from register (e.g. email already taken)
        const detail = errData.detail || {}
        const msgs   = Object.entries(detail)
          .map(([f, m]) => f === 'non_field_errors' ? m : `${f.replace(/_/g,' ')}: ${m}`)
          .join(' ')
        setError(msgs || errData.message || 'Please check your details.')

      } else {
        setError(errData?.message || 'Something went wrong. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  // Show "check your email" screen after successful registration
  if (registered) return <CheckEmailScreen email={registered} />

  return (
    <div style={page}>
      <div style={panel}>
        <Logo />

        {/* Mode tabs */}
        <div style={tabs}>
          <button style={tab(mode === 'login')}    onClick={() => switchMode('login')}>Sign in</button>
          <button style={tab(mode === 'register')} onClick={() => switchMode('register')}>Create account</button>
        </div>

        {/* Error banner */}
        {error && (
          <div style={errorBox}>
            ⚠ {error}
          </div>
        )}

        {/* Email-not-verified banner + resend button */}
        {unverified && (
          <UnverifiedBanner email={unverified} />
        )}

        <form onSubmit={submit} style={{ display:'flex', flexDirection:'column', gap:14 }}>
          {mode === 'register' && (
            <Field label="First name (optional)">
              <input style={input} value={firstName} onChange={e => setFirstName(e.target.value)}
                     placeholder="Jane" autoComplete="given-name" />
            </Field>
          )}

          <Field label="Email">
            <input style={input} type="email" value={email}
                   onChange={e => setEmail(e.target.value)}
                   placeholder="you@example.com" required autoComplete="email" autoFocus />
          </Field>

          <Field label={
            <span style={{ display:'flex', justifyContent:'space-between', width:'100%' }}>
              <span>Password</span>
              {mode === 'login' && (
                <a href="/forgot-password" style={{ fontSize:11, color:'#B8B0A0', textDecoration:'none' }}>
                  Forgot password?
                </a>
              )}
            </span>
          }>
            <input style={input} type="password" value={password}
                   onChange={e => setPassword(e.target.value)}
                   placeholder={mode === 'register' ? 'At least 8 characters' : '••••••••'}
                   required minLength={8} autoComplete={mode === 'register' ? 'new-password' : 'current-password'} />
          </Field>

          <button style={btnPrimary} type="submit" disabled={loading}>
            {loading
              ? <span>Loading…</span>
              : mode === 'login' ? 'Sign in' : 'Create account'
            }
          </button>
        </form>

        <p style={{ textAlign:'center', fontSize:13, color:'#B8B0A0', marginTop:16 }}>
          {mode === 'login' ? (
            <>No account? <button style={link} onClick={() => switchMode('register')}>Create one</button></>
          ) : (
            <>Already have one? <button style={link} onClick={() => switchMode('login')}>Sign in</button></>
          )}
        </p>
      </div>
    </div>
  )
}

// ── Unverified email banner ────────────────────────────────────────────────
function UnverifiedBanner({ email }) {
  const [sent, setSent] = useState(false)
  const resend = async () => {
    await fetch('/api/auth/resend-verification/', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ email }),
    })
    setSent(true)
  }
  return (
    <div style={{ background:'rgba(107,154,196,0.12)', border:'1px solid rgba(107,154,196,0.3)', borderRadius:10, padding:'10px 14px', marginBottom:4, fontSize:13 }}>
      {sent
        ? <span style={{color:'#7BA688'}}>✓ Verification email sent — check your inbox.</span>
        : <span style={{color:'#B8B0A0'}}>
            Email not verified.{' '}
            <button style={link} onClick={resend}>Resend verification email →</button>
          </span>
      }
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────
function Logo() {
  return (
    <div style={{ textAlign:'center', marginBottom:28 }}>
      <div style={{ fontFamily:'Georgia,serif', fontSize:'1.8rem', color:'#F0EAD9', letterSpacing:'-0.02em' }}>
        Ritha
      </div>
      <div style={{ fontSize:'0.65rem', letterSpacing:'0.1em', textTransform:'uppercase', color:'#D4724A', marginTop:4 }}>
        AI Style Companion
      </div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:5 }}>
      <label style={{ fontSize:11, letterSpacing:'0.08em', textTransform:'uppercase', color:'#B8B0A0', display:'flex', justifyContent:'space-between' }}>
        {label}
      </label>
      {children}
    </div>
  )
}

// ── Styles ────────────────────────────────────────────────────────────────
const page = { minHeight:'100vh', display:'flex', alignItems:'center', justifyContent:'center', background:'#0A0A0B', padding:24 }
const panel = { width:'100%', maxWidth:400, background:'#111113', border:'1px solid rgba(255,255,255,0.07)', borderRadius:20, padding:36 }
const heading = { fontFamily:'Georgia,serif', fontSize:'1.4rem', color:'#F0EAD9', fontWeight:400 }
const sub     = { fontSize:14, color:'#B8B0A0', lineHeight:1.6, margin:0 }
const divider = { border:'none', borderTop:'1px solid rgba(255,255,255,0.07)', margin:'20px 0' }
const errorBox = { background:'rgba(220,70,60,0.1)', border:'1px solid rgba(220,70,60,0.3)', borderRadius:10, padding:'10px 14px', fontSize:13, color:'#f87171', marginBottom:4 }
const input   = { background:'#1c1c18', border:'1px solid rgba(255,255,255,0.12)', borderRadius:10, padding:'10px 12px', fontSize:14, color:'#F0EAD9', fontFamily:'inherit', width:'100%', boxSizing:'border-box', outline:'none' }
const tabs    = { display:'flex', background:'#1c1c18', borderRadius:10, padding:3, marginBottom:20 }
const tab     = (active) => ({ flex:1, padding:'8px 0', fontSize:13, fontWeight: active ? 600 : 400, color: active ? '#F0EAD9' : '#B8B0A0', background: active ? '#2e2e29' : 'transparent', border:'none', borderRadius:8, cursor:'pointer', transition:'all 0.2s' })
const btnPrimary   = { background:'#D4724A', color:'#fff', border:'none', borderRadius:10, padding:'12px 0', fontSize:15, fontWeight:500, cursor:'pointer', width:'100%', marginTop:4 }
const btnSecondary = { background:'transparent', color:'#B8B0A0', border:'1px solid rgba(255,255,255,0.12)', borderRadius:10, padding:'10px 0', fontSize:13, cursor:'pointer', width:'100%' }
const link    = { background:'none', border:'none', color:'#D4724A', cursor:'pointer', padding:0, fontSize:'inherit', textDecoration:'underline' }
'''

login_page.write_text(NEW_LOGIN)
print("✅ LoginPage.jsx rewritten with proper error handling")

# ── Rebuild frontend ──────────────────────────────────────────────────────
import subprocess
print("\nRebuilding frontend...")
result = subprocess.run(
    ['npm', 'run', 'build'],
    capture_output=True, text=True, cwd='frontend'
)
if result.returncode == 0:
    print("✅ Frontend built successfully")
else:
    print("⚠  Build output:")
    print(result.stdout[-500:] if result.stdout else '')
    print(result.stderr[-500:] if result.stderr else '')
    print("   Run manually: cd frontend && npm run build")

print()
print("=" * 50)
print("Done! Now:")
print("  1. python manage.py runserver")
print("  2. cd frontend && npm run dev")
print("  3. Open http://localhost:3000")
print()
print("Sign-up flow:")
print("  - Register → see 'Check your email' screen")
print("  - Look in Terminal 1 for the verification link")
print("  - Copy the link → open in browser → verified!")
print("  - Log in with your email + password")