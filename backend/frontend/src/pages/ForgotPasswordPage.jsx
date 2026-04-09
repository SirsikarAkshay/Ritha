// src/pages/ForgotPasswordPage.jsx
import { useState } from 'react'
import { Link } from 'react-router-dom'

export default function ForgotPasswordPage() {
  const [email,   setEmail]   = useState('')
  const [sent,    setSent]    = useState(false)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const r = await fetch('/api/auth/forgot-password/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      })
      const data = await r.json()
      if (!r.ok) { setError(data.error?.message || 'Something went wrong.'); return }
      setSent(true)
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center', background: 'var(--midnight)', padding: '24px',
    }}>
      <div style={{ width: '100%', maxWidth: '420px' }}>
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', color: 'var(--cream)', letterSpacing: '-0.02em' }}>
            Arokah
          </div>
        </div>

        <div className="card" style={{ padding: '40px 32px' }}>
          {sent ? (
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '3rem', marginBottom: '16px' }}>📬</div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', color: 'var(--cream)', marginBottom: '12px' }}>
                Check your inbox
              </div>
              <p style={{ color: 'var(--cream-dim)', fontSize: '0.875rem', lineHeight: 1.6, marginBottom: '24px' }}>
                If <strong style={{ color: 'var(--cream)' }}>{email}</strong> is registered, 
                we've sent a password reset link. It expires in 1 hour.
              </p>
              <p style={{ fontSize: '0.8rem', color: 'var(--cream-dim)', marginBottom: '24px' }}>
                Check your spam folder if you don't see it.
              </p>
              <Link to="/login" className="btn btn-ghost btn-full">← Back to login</Link>
            </div>
          ) : (
            <>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', color: 'var(--cream)', marginBottom: '8px' }}>
                Forgot your password?
              </div>
              <p style={{ color: 'var(--cream-dim)', fontSize: '0.875rem', marginBottom: '24px', lineHeight: 1.6 }}>
                Enter your email and we'll send you a link to reset it.
              </p>

              {error && (
                <div className="alert alert-error" style={{ marginBottom: '16px' }}>⚠ {error}</div>
              )}

              <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div className="input-group">
                  <label className="input-label">Email address</label>
                  <input
                    className="input"
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                    autoFocus
                  />
                </div>
                <button className="btn btn-primary" type="submit" disabled={loading}>
                  {loading ? <><span className="spinner" style={{ width: 16, height: 16 }} /> Sending…</> : 'Send reset link'}
                </button>
              </form>

              <p style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.8rem', color: 'var(--cream-dim)' }}>
                Remember it? <Link to="/login" style={{ color: 'var(--terra)' }}>Sign in</Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
