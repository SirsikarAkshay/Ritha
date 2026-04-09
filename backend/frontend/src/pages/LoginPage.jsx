// src/pages/LoginPage.jsx
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
        Arokah
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
