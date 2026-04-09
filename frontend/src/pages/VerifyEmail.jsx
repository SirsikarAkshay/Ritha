import { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { api } from '../api/client.js'
import styles from './Auth.module.css'
import Logo from '../components/Logo.jsx'

export default function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const emailFromUrl = searchParams.get('email') || ''
  const tokenFromUrl = searchParams.get('token') || ''

  const [email, setEmail] = useState(emailFromUrl)
  const [token, setToken] = useState(tokenFromUrl)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [resending, setResending] = useState(false)
  const nav = useNavigate()

  const submit = async e => {
    e.preventDefault()
    setError('')
    setMessage('')
    setLoading(true)
    try {
      await api.post('/auth/verify-email/', { email, token })
      setMessage('Email verified successfully! Redirecting to login...')
      setTimeout(() => nav('/login'), 2000)
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Verification failed. Please check your code and try again.')
    } finally {
      setLoading(false)
    }
  }

  const resendEmail = async () => {
    if (!email) {
      setError('Please enter your email address first.')
      return
    }
    setResending(true)
    setError('')
    try {
      await api.post('/auth/resend-verification/', { email })
      setMessage('A new verification link has been sent to your email.')
    } catch (err) {
      setError('Failed to resend. Please try again later.')
    } finally {
      setResending(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.panel}>
        <div className={styles.logo}>
          <Logo style={{ height: '44px', width: 'auto' }} />
        </div>

        <div className={styles.tagline}>
          <em>Verify your email.</em>
        </div>

        <p style={{ color: 'var(--cream-dim)', fontSize: '0.9rem', marginBottom: '24px', textAlign: 'center' }}>
          Check your inbox for a verification link. Click the link or enter the code below.
        </p>

        <form onSubmit={submit} className={styles.form}>
          <div className="field">
            <label>Email</label>
            <input className="input" type="email" value={email}
              onChange={e => setEmail(e.target.value)} required autoFocus />
          </div>
          <div className="field">
            <label>Verification Code</label>
            <input className="input" type="text" value={token}
              onChange={e => setToken(e.target.value)} placeholder="Paste the code from the email" required />
          </div>

          {error && <p className={styles.error}>{error}</p>}
          {message && <p className={styles.message}>{message}</p>}

          <button className="btn btn-primary btn-full btn-lg" type="submit" disabled={loading}>
            {loading ? <span className="spinner" /> : 'Verify Email'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: '16px' }}>
          <button onClick={resendEmail} disabled={resending}
            style={{ background: 'none', border: 'none', color: 'var(--terra-light)', cursor: resending ? 'not-allowed' : 'pointer', fontSize: '0.875rem' }}>
            {resending ? 'Sending...' : 'Resend verification email'}
          </button>
        </p>

        <p className={styles.switchLink}>
          <Link to="/login">Back to login</Link>
        </p>
      </div>

      <div className={styles.visual}>
        <div className={styles.visualInner}>
          <div className={styles.visualQuote}>
            <span>One wardrobe.</span>
            <span>One calendar.</span>
            <span>One perfect outfit.</span>
          </div>
        </div>
      </div>
    </div>
  )
}