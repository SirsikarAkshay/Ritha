// src/pages/VerifyEmailPage.jsx
import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { auth as authApi } from '../api/index.js'

export default function VerifyEmailPage() {
  const [searchParams]        = useSearchParams()
  const [status, setStatus]   = useState('verifying') // verifying | success | error
  const [message, setMessage] = useState('')
  const navigate              = useNavigate()

  const token = searchParams.get('token') || ''
  const email = searchParams.get('email') || ''

  useEffect(() => {
    if (!token || !email) {
      setStatus('error')
      setMessage('Invalid verification link. Please check your email for the correct link.')
      return
    }
    verify()
  }, [])

  const verify = async () => {
    try {
      const data = await authApi.verifyEmail({ token, email })
      setStatus('success')
      setMessage(data.message || 'Email verified successfully!')
      setTimeout(() => navigate('/login'), 2500)
    } catch (err) {
      setStatus('error')
      setMessage(
        err.response?.data?.error?.message ||
        'Verification failed. The link may have expired.'
      )
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--midnight)',
      padding: '24px',
    }}>
      <div style={{ width: '100%', maxWidth: '440px', textAlign: 'center' }}>
        {/* Logo */}
        <div style={{ marginBottom: '40px' }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', color: 'var(--cream)', letterSpacing: '-0.02em' }}>
            Arokah
          </div>
          <div style={{ fontSize: '0.7rem', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--terra)', marginTop: '4px' }}>
            AI Style Companion
          </div>
        </div>

        <div className="card" style={{ padding: '40px 32px' }}>
          {status === 'verifying' && (
            <>
              <div style={{ marginBottom: '20px' }}>
                <span className="spinner" style={{ width: '32px', height: '32px', borderWidth: '3px', display: 'inline-block' }} />
              </div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', color: 'var(--cream)', marginBottom: '8px' }}>
                Verifying your email…
              </div>
              <p style={{ color: 'var(--cream-dim)', fontSize: '0.875rem' }}>
                Just a moment.
              </p>
            </>
          )}

          {status === 'success' && (
            <>
              <div style={{ fontSize: '3rem', marginBottom: '20px' }}>✓</div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', color: 'var(--sage)', marginBottom: '12px' }}>
                Email verified!
              </div>
              <p style={{ color: 'var(--cream-dim)', fontSize: '0.875rem', marginBottom: '24px' }}>
                {message}
              </p>
              <p style={{ color: 'var(--cream-dim)', fontSize: '0.8rem' }}>
                Redirecting to login…
              </p>
            </>
          )}

          {status === 'error' && (
            <>
              <div style={{ fontSize: '3rem', marginBottom: '20px' }}>✕</div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', color: 'var(--cream)', marginBottom: '12px' }}>
                Verification failed
              </div>
              <p style={{ color: 'var(--cream-dim)', fontSize: '0.875rem', marginBottom: '24px', lineHeight: 1.6 }}>
                {message}
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {email && <ResendButton email={email} />}
                <Link to="/login" className="btn btn-ghost" style={{ textAlign: 'center' }}>
                  Back to login
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function ResendButton({ email }) {
  const [sent,    setSent]    = useState(false)
  const [loading, setLoading] = useState(false)

  const resend = async () => {
    setLoading(true)
    try {
      await fetch('/api/auth/resend-verification/', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ email }),
      })
      setSent(true)
    } finally {
      setLoading(false)
    }
  }

  if (sent) return (
    <p style={{ color: 'var(--sage)', fontSize: '0.875rem' }}>
      ✓ New verification email sent. Check your inbox.
    </p>
  )

  return (
    <button className="btn btn-secondary" onClick={resend} disabled={loading}>
      {loading ? 'Sending…' : '↻ Resend verification email'}
    </button>
  )
}
