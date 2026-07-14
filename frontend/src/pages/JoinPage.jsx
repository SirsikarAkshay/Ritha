// Join a trip's crew via a shared invite link (/join/:token).
// Logged in → join immediately. Logged out → stash the token, send them through
// sign-up, and the invite is processed on first authenticated load (App.jsx).
import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { sharedWardrobes } from '../api/index.js'
import { useAuth } from '../hooks/useAuth.jsx'

export default function JoinPage() {
  const { token } = useParams()
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [msg, setMsg] = useState('Joining your crew…')
  const done = useRef(false)

  useEffect(() => {
    if (loading || done.current) return
    if (!user) {
      try { localStorage.setItem('ritha_pending_join', token) } catch { /* ignore */ }
      navigate('/login', { replace: true })
      return
    }
    done.current = true
    sharedWardrobes.join(token)
      .then((res) => {
        window.__toast?.(res?.already_member ? "You're already in this trip's crew." : 'Joined the trip! 🎒', 'success')
        navigate('/trips', { replace: true })
      })
      .catch(() => setMsg('This invite link is invalid or has expired.'))
  }, [user, loading, token, navigate])

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg, #0d0f14)', color: 'var(--cream, #f5f0e8)' }}>
      <div style={{ textAlign: 'center', padding: 24 }}>
        <div style={{ fontSize: '2rem', marginBottom: 12 }}>👥</div>
        <div style={{ fontSize: '1.05rem' }}>{msg}</div>
      </div>
    </div>
  )
}
