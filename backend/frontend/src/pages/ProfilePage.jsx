// src/pages/ProfilePage.jsx
import { useState } from 'react'
import { useAuth } from '../hooks/useAuth.jsx'
import { auth as authApi } from '../api/index.js'

export default function ProfilePage() {
  const { user, updateUser } = useAuth()

  const [profile, setProfile]       = useState({ first_name: user?.first_name || '', last_name: user?.last_name || '', timezone: user?.timezone || 'UTC', location_name: user?.location_name || '' })
  const [passwords, setPasswords]   = useState({ current_password: '', new_password: '' })
  const [saving,    setSaving]       = useState(false)
  const [changingPw,setChangingPw]  = useState(false)
  const [msg,       setMsg]          = useState({ text: '', type: '' })

  const flash = (text, type = 'success') => {
    setMsg({ text, type })
    setTimeout(() => setMsg({ text: '', type: '' }), 3000)
  }

  const saveProfile = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const updated = await authApi.updateMe(profile)
      updateUser(updated)
      flash('Profile updated.')
    } catch (err) {
      flash(err.response?.data?.error?.message || 'Failed to save.', 'error')
    } finally {
      setSaving(false)
    }
  }

  const changePassword = async (e) => {
    e.preventDefault()
    if (passwords.new_password.length < 8) {
      flash('New password must be at least 8 characters.', 'error')
      return
    }
    setChangingPw(true)
    try {
      await authApi.changePassword(passwords)
      setPasswords({ current_password: '', new_password: '' })
      flash('Password changed successfully.')
    } catch (err) {
      flash(err.response?.data?.error?.detail?.current_password?.[0] || err.response?.data?.error?.message || 'Failed to change password.', 'error')
    } finally {
      setChangingPw(false)
    }
  }

  const sp = k => e => setProfile(p => ({ ...p, [k]: e.target.value }))
  const sw = k => e => setPasswords(p => ({ ...p, [k]: e.target.value }))

  const initial = (user?.first_name?.[0] || user?.email?.[0] || '?').toUpperCase()

  return (
    <div>
      <div className="page-header fade-up">
        <div className="date-line">Account</div>
        <h1>Your Profile</h1>
        <p>Manage your account settings and preferences.</p>
      </div>

      {msg.text && (
        <div className={`alert alert-${msg.type} fade-up`} style={{ marginBottom: '20px' }}>
          {msg.type === 'success' ? '✓' : '⚠'} {msg.text}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }} className="fade-up fade-up-delay-1">

        {/* Profile info */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
            <div style={{
              width: '56px', height: '56px', borderRadius: '50%',
              background: 'var(--terra-dim)', border: '2px solid rgba(212,114,74,0.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: 'var(--font-display)', fontSize: '1.5rem', color: 'var(--terra-light)',
            }}>
              {initial}
            </div>
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.125rem', color: 'var(--cream)' }}>
                {user?.first_name || 'Your account'}
              </div>
              <div style={{ fontSize: '0.875rem', color: 'var(--cream-dim)' }}>{user?.email}</div>
            </div>
          </div>

          <form onSubmit={saveProfile} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div className="input-group">
                <label className="input-label">First name</label>
                <input className="input" value={profile.first_name} onChange={sp('first_name')} placeholder="Jane" />
              </div>
              <div className="input-group">
                <label className="input-label">Last name</label>
                <input className="input" value={profile.last_name} onChange={sp('last_name')} placeholder="Doe" />
              </div>
            </div>
            <div className="input-group">
              <label className="input-label">
                Email
                {user?.is_email_verified
                  ? <span className="badge badge-sage" style={{ marginLeft: '8px', verticalAlign: 'middle' }}>✓ Verified</span>
                  : <span className="badge badge-terra" style={{ marginLeft: '8px', verticalAlign: 'middle' }}>⚠ Unverified</span>
                }
              </label>
              <input className="input" value={user?.email || ''} disabled style={{ opacity: 0.5 }} />
              {!user?.is_email_verified && (
                <span className="input-hint" style={{ color: 'var(--terra)' }}>
                  Check your inbox for a verification link, or{' '}
                  <button
                    type="button"
                    onClick={async () => {
                      await fetch('/api/auth/resend-verification/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email: user.email }),
                      })
                      flash('Verification email sent — check your inbox.')
                    }}
                    style={{ background: 'none', border: 'none', color: 'var(--terra-light)', cursor: 'pointer', padding: 0, textDecoration: 'underline', font: 'inherit', fontSize: '0.75rem' }}
                  >
                    resend now
                  </button>.
                </span>
              )}
            </div>
            <div className="input-group">
              <label className="input-label">Home city (for weather)</label>
              <input className="input" value={profile.location_name} onChange={sp('location_name')} placeholder="e.g. Zurich, London, New York" />
              <span className="input-hint">Used to fetch weather for your daily outfit suggestion.</span>
            </div>
            <div className="input-group">
              <label className="input-label">Timezone</label>
              <select className="input" value={profile.timezone} onChange={sp('timezone')}>
                {['UTC', 'Europe/Zurich', 'Europe/London', 'America/New_York', 'America/Los_Angeles', 'Asia/Tokyo', 'Asia/Singapore', 'Australia/Sydney'].map(tz => (
                  <option key={tz} value={tz}>{tz}</option>
                ))}
              </select>
            </div>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : 'Save changes'}
            </button>
          </form>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Change password */}
          <div className="card">
            <div className="card-label" style={{ marginBottom: '16px' }}>Change password</div>
            <form onSubmit={changePassword} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div className="input-group">
                <label className="input-label">Current password</label>
                <input className="input" type="password" value={passwords.current_password} onChange={sw('current_password')} required />
              </div>
              <div className="input-group">
                <label className="input-label">New password</label>
                <input className="input" type="password" value={passwords.new_password} onChange={sw('new_password')} required minLength={8} />
                <span className="input-hint">Minimum 8 characters.</span>
              </div>
              <button type="submit" className="btn btn-secondary" disabled={changingPw}>
                {changingPw ? 'Changing…' : 'Change password'}
              </button>
            </form>
          </div>

          {/* Account info */}
          <div className="card">
            <div className="card-label" style={{ marginBottom: '12px' }}>Account details</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <Row label="Member since" value={user?.created_at ? new Date(user.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }) : '—'} />
              <Row label="Email verified" value={user?.is_email_verified ? '✓ Verified' : '✗ Not verified'} />
              <RowWithCalendar user={user} />
              <Row label="Push notifications" value="Not configured" note="Add Firebase key to enable" />
              <Row label="AI engine" value="Mistral AI" />
              <Row label="Data region" value="Switzerland 🇨🇭" />
            </div>
          </div>

          {/* Danger zone */}
          <div className="card" style={{ borderColor: 'rgba(220,70,60,0.2)' }}>
            <div className="card-label" style={{ marginBottom: '12px', color: '#f87171' }}>Danger zone</div>
            <p style={{ fontSize: '0.875rem', color: 'var(--cream-dim)', marginBottom: '14px' }}>
              Permanently delete your account and all associated data. This cannot be undone.
            </p>
            <button
              className="btn btn-ghost btn-sm"
              style={{ color: '#f87171', borderColor: 'rgba(220,70,60,0.3)' }}
              onClick={() => {
                if (window.confirm('Are you sure? This will permanently delete your account and all your data.')) {
                  alert('Account deletion coming soon — please contact support@arokah.com')
                }
              }}
            >
              Delete account
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function RowWithCalendar({ user }) {
  const connected = [
    user?.google_calendar_connected && 'Google',
    user?.apple_calendar_connected  && 'Apple',
    user?.outlook_calendar_connected && 'Outlook',
  ].filter(Boolean)

  return (
    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', fontSize:'0.875rem', paddingBottom:'10px', borderBottom:'1px solid var(--border)' }}>
      <span style={{ color:'var(--cream-dim)' }}>Calendar</span>
      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
        {connected.length > 0 ? (
          <span style={{ color:'var(--sage)', fontSize:'0.8rem' }}>
            ✓ {connected.join(', ')}
          </span>
        ) : (
          <span style={{ color:'var(--cream-dim)', fontSize:'0.8rem' }}>Not connected</span>
        )}
        <a href="/calendar" style={{ color:'var(--terra)', fontSize:'0.8rem', textDecoration:'none' }}>Manage →</a>
      </div>
    </div>
  )
}

function RowWithLink({ label, href, linkText }) {
  return (
    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', fontSize:'0.875rem', paddingBottom:'10px', borderBottom:'1px solid var(--border)' }}>
      <span style={{ color:'var(--cream-dim)' }}>{label}</span>
      <a href={href} style={{ color:'var(--terra)', fontSize:'0.8rem', textDecoration:'none' }}>{linkText}</a>
    </div>
  )
}

function Row({ label, value, note }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.875rem', paddingBottom: '10px', borderBottom: '1px solid var(--border)' }}>
      <span style={{ color: 'var(--cream-dim)' }}>{label}</span>
      <span style={{ color: 'var(--cream)', display: 'flex', alignItems: 'center', gap: '6px' }}>
        {value}
        {note && <span style={{ fontSize: '0.7rem', color: 'var(--cream-dim)' }}>({note})</span>}
      </span>
    </div>
  )
}
