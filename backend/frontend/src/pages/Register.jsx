import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import styles from './Auth.module.css'

export default function Register() {
  const [form, setForm] = useState({ email: '', password: '', first_name: '' })
  const [error, setError]   = useState('')
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const nav = useNavigate()

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

  const submit = async e => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(form.email, form.password, form.first_name)
      nav('/')
    } catch (err) {
      const d = err.response?.data?.error?.detail
      const msg = typeof d === 'object'
        ? Object.values(d).flat().join(' ')
        : err.response?.data?.error?.message || 'Registration failed.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.panel}>
        <div className={styles.logo}>
          <span className={styles.logoMark}>G</span>
          <span className={styles.logoName}>Arokah</span>
        </div>
        <div className={styles.tagline}>Your AI style companion starts here.</div>

        <form onSubmit={submit} className={styles.form}>
          <div className="field">
            <label>First name</label>
            <input className="input" value={form.first_name}
              onChange={set('first_name')} placeholder="Jane" />
          </div>
          <div className="field">
            <label>Email</label>
            <input className="input" type="email" value={form.email}
              onChange={set('email')} required />
          </div>
          <div className="field">
            <label>Password</label>
            <input className="input" type="password" value={form.password}
              onChange={set('password')} required minLength={8} />
          </div>

          {error && <p className={styles.error}>{error}</p>}

          <button className="btn btn-primary btn-full btn-lg" disabled={loading}>
            {loading ? <span className="spinner" /> : 'Create account'}
          </button>
        </form>

        <p className={styles.switchLink}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>

      <div className={styles.visual}>
        <div className={styles.visualInner}>
          <div className={styles.visualQuote}>
            <span>Know your wardrobe.</span>
            <span>Own your style.</span>
            <span>Travel light.</span>
          </div>
        </div>
      </div>
    </div>
  )
}
