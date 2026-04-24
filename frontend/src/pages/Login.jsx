import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import styles from './Auth.module.css'
import Logo from '../components/Logo.jsx'

export default function Login() {
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const { login }               = useAuth()
  const nav                     = useNavigate()

  const submit = async e => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      nav('/')
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Invalid credentials.')
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
          <em>Dress for your day.</em> Every day.
        </div>

        <form onSubmit={submit} className={styles.form}>
          <div className="field">
            <label>Email</label>
            <input className="input" type="email" value={email}
              onChange={e => setEmail(e.target.value)} required autoFocus />
          </div>
          <div className="field">
            <label>Password</label>
            <input className="input" type="password" value={password}
              onChange={e => setPassword(e.target.value)} required />
          </div>

          {error && <p className={styles.error}>{error}</p>}

          <button className="btn btn-primary btn-full btn-lg" type="submit" disabled={loading}>
            {loading ? <span className="spinner" /> : 'Sign in'}
          </button>
        </form>

        <p className={styles.switchLink}>
          New to Ritha? <Link to="/register">Create account</Link>
        </p>

        <p className={styles.switchLink}>
          <Link to="/forgot-password">Forgot password?</Link>
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
