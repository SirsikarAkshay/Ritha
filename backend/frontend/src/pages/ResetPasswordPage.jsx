// src/pages/ResetPasswordPage.jsx
import { useState, useEffect } from 'react'
import { useSearchParams, Link, useNavigate } from 'react-router-dom'

export default function ResetPasswordPage() {
  const [searchParams]            = useSearchParams()
  const [password,  setPassword]  = useState('')
  const [confirm,   setConfirm]   = useState('')
  const [loading,   setLoading]   = useState(false)
  const [done,      setDone]      = useState(false)
  const [error,     setError]     = useState('')
  const navigate                  = useNavigate()

  const token = searchParams.get('token') || ''
  const email = searchParams.get('email') || ''

  useEffect(() => {
    if (!token || !email) setError('Invalid reset link. Please request a new one.')
  }, [token, email])

  const submit = async (e) => {
    e.preventDefault()
    setError('')

    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }

    setLoading(true)
    try {
      const r = await fetch('/api/auth/reset-password/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, email, new_password: password }),
      })
      const data = await r.json()
      if (!r.ok) { setError(data.error?.message || 'Reset failed.'); return }
      setDone(true)
      setTimeout(() => navigate('/login'), 2500)
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
          {done ? (
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '3rem', marginBottom: '16px' }}>✓</div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', color: 'var(--sage)', marginBottom: '12px' }}>
                Password reset!
              </div>
              <p style={{ color: 'var(--cream-dim)', fontSize: '0.875rem', marginBottom: '8px' }}>
                Your password has been changed successfully.
              </p>
              <p style={{ color: 'var(--cream-dim)', fontSize: '0.8rem' }}>Redirecting to login…</p>
            </div>
          ) : (
            <>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', color: 'var(--cream)', marginBottom: '8px' }}>
                Set a new password
              </div>
              {email && (
                <p style={{ color: 'var(--cream-dim)', fontSize: '0.8rem', marginBottom: '24px' }}>
                  For <strong style={{ color: 'var(--cream)' }}>{email}</strong>
                </p>
              )}

              {error && (
                <div className="alert alert-error" style={{ marginBottom: '16px' }}>
                  ⚠ {error}
                  {(error.includes('expired') || error.includes('Invalid reset')) && (
                    <div style={{ marginTop: '8px' }}>
                      <Link to="/forgot-password" style={{ color: 'var(--terra)', fontSize: '0.8rem' }}>
                        Request a new reset link →
                      </Link>
                    </div>
                  )}
                </div>
              )}

              <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div className="input-group">
                  <label className="input-label">New password</label>
                  <input
                    className="input"
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    required
                    minLength={8}
                    autoFocus
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Confirm new password</label>
                  <input
                    className="input"
                    type="password"
                    value={confirm}
                    onChange={e => setConfirm(e.target.value)}
                    placeholder="Same password again"
                    required
                  />
                </div>
                <button
                  className="btn btn-primary"
                  type="submit"
                  disabled={loading || !token || !email}
                >
                  {loading ? <><span className="spinner" style={{ width: 16, height: 16 }} /> Resetting…</> : 'Reset password'}
                </button>
              </form>

              <p style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.8rem', color: 'var(--cream-dim)' }}>
                <Link to="/login" style={{ color: 'var(--terra)' }}>← Back to login</Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
