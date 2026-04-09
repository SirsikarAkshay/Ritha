import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import styles from './Auth.module.css'
import Logo from '../components/Logo.jsx'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { forgotPassword } = useAuth()

  const submit = async e => {
    e.preventDefault()
    setError('')
    setMessage('')
    setLoading(true)
    try {
      await forgotPassword(email)
      setMessage('If an account exists for that email, a password reset link has been sent. Check your inbox (and spam folder).')
    } catch (err) {
      setError(err.response?.data?.error?.message || err.message || 'An error occurred. Please try again.')
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
            <label>Email</label>
            <input className="input" type="email" value={email}
              onChange={e => setEmail(e.target.value)} required autoFocus />
          </div>

          {error && <p className={styles.error}>{error}</p>}
          {message && <p className={styles.message}>{message}</p>}

          <button className="btn btn-primary btn-full btn-lg" type="submit" disabled={loading}>
            {loading ? <span className="spinner" /> : 'Send reset link'}
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