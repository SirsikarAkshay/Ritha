// src/pages/LoginPage.jsx
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import { auth as authApi } from '../api/index.js'

export default function LoginPage() {
  const [mode,     setMode]     = useState('login')   // 'login' | 'register'
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [firstName,setFirstName]= useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  const { login } = useAuth()
  const navigate  = useNavigate()

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'register') {
        const result = await authApi.register({ email, password, first_name: firstName })
        // Redirect to verification page with email
        navigate(`/verify-email?email=${encodeURIComponent(email)}`)
      } else {
        await login(email, password)
        navigate('/')
      }
    } catch (err) {
      const errorData = err.response?.data?.error
      if (errorData?.code === 'email_not_verified') {
        setError('Please verify your email before logging in. Check your inbox for a verification link.')
      } else if (mode === 'register' && errorData?.code === 'validation_error') {
        const details = errorData.detail
        const firstError = Object.values(details || {})[0] || 'Registration failed. Please check your input.'
        setError(firstError)
      } else {
        setError(err.response?.data?.error?.message || err.message || 'Invalid credentials.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      background: 'var(--midnight)',
    }}>
      {/* Left — branding panel */}
      <div style={{
        background: 'var(--surface-1)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '48px',
      }}>
        <div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.75rem', color: 'var(--cream)', letterSpacing: '-0.02em' }}>
            Ritha
          </div>
          <div style={{ fontSize: '0.7rem', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--terra)', marginTop: '4px' }}>
            Your wardrobe assistant
          </div>
        </div>

        <div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(2rem, 4vw, 3rem)', lineHeight: 1.1, color: 'var(--cream)', letterSpacing: '-0.02em', marginBottom: '24px' }}>
            Dress for your day.<br />
            <span style={{ color: 'var(--terra)' }}>Every day.</span>
          </div>
          <p style={{ color: 'var(--cream-dim)', lineHeight: 1.6, fontSize: '0.9375rem', maxWidth: '340px' }}>
            Your wardrobe, your calendar, the weather — unified into one smart outfit suggestion every morning.
          </p>

          <div style={{ marginTop: '48px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {[
              { icon: '📅', text: 'Syncs with Google Calendar' },
              { icon: '🌤', text: 'Live weather-aware suggestions' },
              { icon: '✈', text: 'Trip packing with 5-4-3-2-1 capsule logic' },
              { icon: '🌱', text: 'Tracks CO₂ saved by packing light' },
            ].map(({ icon, text }) => (
              <div key={text} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '1rem' }}>{icon}</span>
                <span style={{ fontSize: '0.875rem', color: 'var(--cream-dim)' }}>{text}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', opacity: 0.5 }}>
          Built with Swiss precision · Data stored in Switzerland
        </div>
      </div>

      {/* Right — form panel */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px',
      }}>
        <div style={{ width: '100%', maxWidth: '400px' }} className="fade-up">
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.75rem', color: 'var(--cream)', marginBottom: '8px', letterSpacing: '-0.02em' }}>
            {mode === 'login' ? 'Welcome back' : 'Create account'}
          </h2>
          <p style={{ color: 'var(--cream-dim)', fontSize: '0.9rem', marginBottom: '32px' }}>
            {mode === 'login'
              ? 'Sign in to your style companion.'
              : 'Start your AI-powered wardrobe journey.'}
          </p>

          {error && (
            <div className="alert alert-error" style={{ marginBottom: '20px' }}>
              ⚠ {error}
            </div>
          )}

          <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {mode === 'register' && (
              <div className="input-group">
                <label className="input-label">First name</label>
                <input
                  className="input"
                  type="text"
                  placeholder="Jane"
                  value={firstName}
                  onChange={e => setFirstName(e.target.value)}
                />
              </div>
            )}
            <div className="input-group">
              <label className="input-label">Email</label>
              <input
                className="input"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="input-group">
              <label className="input-label">Password</label>
              <input
                className="input"
                type="password"
                placeholder={mode === 'register' ? 'Min. 8 characters' : '••••••••'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-lg"
              disabled={loading}
              style={{ marginTop: '8px' }}
            >
              {loading
                ? <><span className="spinner" style={{ width: 16, height: 16 }} /> Loading…</>
                : mode === 'login' ? 'Sign in' : 'Create account'
              }
            </button>
          </form>

          {mode === 'login' && (
            <div style={{ textAlign: 'center', marginTop: '16px' }}>
              <Link to="/forgot-password" style={{ fontSize: '0.875rem', color: 'var(--terra-light)', textDecoration: 'none' }}>
                Forgot password?
              </Link>
            </div>
          )}

          <div style={{ textAlign: 'center', marginTop: '24px', fontSize: '0.875rem', color: 'var(--cream-dim)' }}>
            {mode === 'login' ? (
              <>Don't have an account?{' '}
                <button onClick={() => setMode('register')} style={{ background: 'none', border: 'none', color: 'var(--terra-light)', cursor: 'pointer' }}>
                  Sign up
                </button>
              </>
            ) : (
              <>Already have an account?{' '}
                <button onClick={() => setMode('login')} style={{ background: 'none', border: 'none', color: 'var(--terra-light)', cursor: 'pointer' }}>
                  Sign in
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
