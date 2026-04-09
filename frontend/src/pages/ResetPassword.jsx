import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import styles from './Auth.module.css'
import Logo from '../components/Logo.jsx'

export default function ResetPassword() {
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const { resetPassword } = useAuth()
  const nav = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const email = searchParams.get('email')

  useEffect(() => {
    if (!token || !email) {
      setError('Invalid password reset link. Please try again.')
    }
  }, [token, email])

  const submit = async e => {
    e.preventDefault()
    if (password !== passwordConfirm) {
      return setError('Passwords do not match.')
    }
    if (password.length < 8) {
      return setError('Password must be at least 8 characters.')
    }
    setError('')
    setMessage('')
    setLoading(true)
    try {
      await resetPassword(token, email, password)
      setMessage('Password has been reset successfully. You can now log in.')
      setTimeout(() => nav('/login'), 3000)
    } catch (err) {
      setError(err.response?.data?.error?.message || err.message || 'Failed to reset password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.panel}>
        <div className={styles.logo}>
          <Logo style={{ height: '44px', width: 'auto' }} />
        </div>

        <div className={styles.tagline}>
          <em>Reset your password.</em>
        </div>

        <form onSubmit={submit} className={styles.form}>
          <div className="field">
            <label>New Password</label>
            <input className="input" type="password" value={password}
              onChange={e => setPassword(e.target.value)} required />
          </div>
          <div className="field">
            <label>Confirm New Password</label>
            <input className="input" type="password" value={passwordConfirm}
              onChange={e => setPasswordConfirm(e.target.value)} required />
          </div>

          {error && <p className={styles.error}>{error}</p>}
          {message && <p className={styles.message}>{message}</p>}

          <button className="btn btn-primary btn-full btn-lg" type="submit" disabled={loading || !token || !email}>
            {loading ? <span className="spinner" /> : 'Reset Password'}
          </button>
        </form>

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