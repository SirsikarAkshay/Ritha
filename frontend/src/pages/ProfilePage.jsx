// src/pages/ProfilePage.jsx
import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth.jsx'
import { auth as authApi, calendar as calendarApi } from '../api/index.js'

export default function ProfilePage() {
  const { user, updateUser } = useAuth()

  const [profile, setProfile]       = useState({ first_name: user?.first_name || '', last_name: user?.last_name || '', timezone: user?.timezone || 'UTC' })
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

  const [calStatus, setCalStatus] = useState(null)
  const [connecting, setConnecting] = useState(false)
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    calendarApi.status().then(setCalStatus).catch(() => {})
  }, [])

  const connectGoogle = async () => {
    setConnecting(true)
    try {
      const { auth_url } = await calendarApi.google.connect()
      // Open Google OAuth in a new window
      window.open(auth_url, '_blank', 'width=600,height=700')
      // Poll for connection status
      const poll = setInterval(async () => {
        try {
          const status = await calendarApi.status()
          if (status.google?.connected) {
            setCalStatus(status)
            clearInterval(poll)
            flash('Google Calendar connected!')
          }
        } catch {}
      }, 2000)
      // Stop polling after 2 minutes
      setTimeout(() => clearInterval(poll), 120000)
    } catch (err) {
      flash('Failed to start Google Calendar connection.', 'error')
    } finally {
      setConnecting(false)
    }
  }

  const disconnectGoogle = async () => {
    if (!confirm('Disconnect Google Calendar?')) return
    try {
      await calendarApi.google.disconnect()
      setCalStatus(prev => ({ ...prev, google: { connected: false, email: null, synced_at: null } }))
      flash('Google Calendar disconnected.')
    } catch {
      flash('Failed to disconnect.', 'error')
    }
  }

  const syncGoogle = async () => {
    setSyncing(true)
    try {
      await calendarApi.google.sync()
      setCalStatus(await calendarApi.status())
      flash('Calendar synced successfully!')
    } catch {
      flash('Sync failed.', 'error')
    } finally {
      setSyncing(false)
    }
  }

  // ── Apple Calendar ────────────────────────────────────────────────────
  const [appleModal, setAppleModal] = useState(false)
  const [appleCreds, setAppleCreds] = useState({ username: '', password: '' })
  const [appleBusy, setAppleBusy]   = useState(false)

  const connectApple = async () => {
    const username = (appleCreds.username || '').trim().toLowerCase()
    // Normalise App-Specific Password: strip whitespace, re-insert dashes
    const rawPw = (appleCreds.password || '').replace(/[\s\-]+/g, '').toLowerCase()
    const password = rawPw.length === 16
      ? `${rawPw.slice(0,4)}-${rawPw.slice(4,8)}-${rawPw.slice(8,12)}-${rawPw.slice(12,16)}`
      : appleCreds.password.trim()

    if (!username || !password) {
      flash('Apple ID and App-Specific Password are required.', 'error')
      return
    }
    setAppleBusy(true)
    try {
      await calendarApi.apple.connect({ username, password })
      setCalStatus(await calendarApi.status())
      setAppleModal(false)
      setAppleCreds({ username: '', password: '' })
      flash('Apple Calendar connected!')
    } catch (err) {
      flash(err.response?.data?.error?.message || 'Failed to connect Apple Calendar.', 'error')
    } finally {
      setAppleBusy(false)
    }
  }

  const disconnectApple = async () => {
    if (!confirm('Disconnect Apple Calendar?')) return
    try {
      await calendarApi.apple.disconnect()
      setCalStatus(prev => ({ ...prev, apple: { connected: false, username: null, synced_at: null } }))
      flash('Apple Calendar disconnected.')
    } catch {
      flash('Failed to disconnect.', 'error')
    }
  }

  const syncApple = async () => {
    setSyncing(true)
    try {
      await calendarApi.apple.sync()
      setCalStatus(await calendarApi.status())
      flash('Apple Calendar synced!')
    } catch {
      flash('Sync failed.', 'error')
    } finally {
      setSyncing(false)
    }
  }

  // ── Outlook Calendar ──────────────────────────────────────────────────
  const connectOutlook = async () => {
    setConnecting(true)
    try {
      const { auth_url } = await calendarApi.outlook.connect()
      window.open(auth_url, '_blank', 'width=600,height=700')
      const poll = setInterval(async () => {
        try {
          const status = await calendarApi.status()
          if (status.outlook?.connected) {
            setCalStatus(status)
            clearInterval(poll)
            flash('Outlook Calendar connected!')
          }
        } catch {}
      }, 2000)
      setTimeout(() => clearInterval(poll), 120000)
    } catch (err) {
      const code = err.response?.data?.error?.code
      if (code === 'not_configured') {
        flash('Outlook Calendar requires MICROSOFT_CLIENT_ID / SECRET in backend/.env.', 'error')
      } else {
        flash('Failed to start Outlook connection.', 'error')
      }
    } finally {
      setConnecting(false)
    }
  }

  const disconnectOutlook = async () => {
    if (!confirm('Disconnect Outlook Calendar?')) return
    try {
      await calendarApi.outlook.disconnect()
      setCalStatus(prev => ({ ...prev, outlook: { connected: false, email: null, synced_at: null } }))
      flash('Outlook Calendar disconnected.')
    } catch {
      flash('Failed to disconnect.', 'error')
    }
  }

  const syncOutlook = async () => {
    setSyncing(true)
    try {
      await calendarApi.outlook.sync()
      setCalStatus(await calendarApi.status())
      flash('Outlook Calendar synced!')
    } catch {
      flash('Sync failed.', 'error')
    } finally {
      setSyncing(false)
    }
  }

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
              <label className="input-label">Email</label>
              <input className="input" value={user?.email || ''} disabled style={{ opacity: 0.5 }} />
              <span className="input-hint">Email cannot be changed.</span>
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
              <Row label="Google Calendar" value={
                calStatus?.google?.connected ? (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ color: 'var(--sage)' }}>✓ Connected</span>
                    <button onClick={syncGoogle} disabled={syncing}
                      style={{ background: 'none', border: '1px solid var(--border)', borderRadius: '4px', padding: '2px 8px', fontSize: '0.7rem', color: 'var(--cream-dim)', cursor: syncing ? 'not-allowed' : 'pointer' }}>
                      {syncing ? 'Syncing…' : 'Sync now'}
                    </button>
                    <button onClick={disconnectGoogle}
                      style={{ background: 'none', border: 'none', fontSize: '0.7rem', color: '#f87171', cursor: 'pointer' }}>
                      Disconnect
                    </button>
                  </span>
                ) : (
                  <button onClick={connectGoogle} disabled={connecting}
                    style={{ background: 'none', border: '1px solid var(--terra)', borderRadius: '4px', padding: '2px 10px', fontSize: '0.7rem', color: 'var(--terra-light)', cursor: connecting ? 'not-allowed' : 'pointer' }}>
                    {connecting ? 'Connecting…' : 'Connect'}
                  </button>
                )
              } note={calStatus?.google?.email || 'Sync your events automatically'} />

              <Row label="Apple Calendar" value={
                calStatus?.apple?.connected ? (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ color: 'var(--sage)' }}>✓ Connected</span>
                    <button onClick={syncApple} disabled={syncing}
                      style={{ background: 'none', border: '1px solid var(--border)', borderRadius: '4px', padding: '2px 8px', fontSize: '0.7rem', color: 'var(--cream-dim)', cursor: syncing ? 'not-allowed' : 'pointer' }}>
                      {syncing ? 'Syncing…' : 'Sync now'}
                    </button>
                    <button onClick={disconnectApple}
                      style={{ background: 'none', border: 'none', fontSize: '0.7rem', color: '#f87171', cursor: 'pointer' }}>
                      Disconnect
                    </button>
                  </span>
                ) : (
                  <button onClick={() => setAppleModal(true)}
                    style={{ background: 'none', border: '1px solid var(--terra)', borderRadius: '4px', padding: '2px 10px', fontSize: '0.7rem', color: 'var(--terra-light)', cursor: 'pointer' }}>
                    Connect
                  </button>
                )
              } note={calStatus?.apple?.username || 'CalDAV — needs App-Specific Password'} />

              <Row label="Outlook Calendar" value={
                calStatus?.outlook?.connected ? (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ color: 'var(--sage)' }}>✓ Connected</span>
                    <button onClick={syncOutlook} disabled={syncing}
                      style={{ background: 'none', border: '1px solid var(--border)', borderRadius: '4px', padding: '2px 8px', fontSize: '0.7rem', color: 'var(--cream-dim)', cursor: syncing ? 'not-allowed' : 'pointer' }}>
                      {syncing ? 'Syncing…' : 'Sync now'}
                    </button>
                    <button onClick={disconnectOutlook}
                      style={{ background: 'none', border: 'none', fontSize: '0.7rem', color: '#f87171', cursor: 'pointer' }}>
                      Disconnect
                    </button>
                  </span>
                ) : (
                  <button onClick={connectOutlook} disabled={connecting}
                    style={{ background: 'none', border: '1px solid var(--terra)', borderRadius: '4px', padding: '2px 10px', fontSize: '0.7rem', color: 'var(--terra-light)', cursor: connecting ? 'not-allowed' : 'pointer' }}>
                    {connecting ? 'Connecting…' : 'Connect'}
                  </button>
                )
              } note={calStatus?.outlook?.email || 'Microsoft 365 via OAuth'} />

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

      {/* Apple Calendar credentials modal */}
      {appleModal && (
        <div
          onClick={() => !appleBusy && setAppleModal(false)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000, padding: '20px',
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              background: 'var(--surface-1)', border: '1px solid var(--border)',
              borderRadius: '16px', padding: '28px', maxWidth: '440px', width: '100%',
              boxShadow: 'var(--shadow-lg)',
            }}
          >
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', color: 'var(--cream)', marginBottom: '8px' }}>
              Connect Apple Calendar
            </h2>
            <p style={{ fontSize: '0.8125rem', color: 'var(--cream-dim)', marginBottom: '20px', lineHeight: 1.5 }}>
              Your regular Apple ID password will <strong>not</strong> work. Generate an{' '}
              <a href="https://appleid.apple.com/account/manage" target="_blank" rel="noreferrer"
                 style={{ color: 'var(--terra-light)' }}>
                App-Specific Password
              </a>{' '}
              at appleid.apple.com → Security → App-Specific Passwords. Credentials are encrypted at rest.
            </p>

            <div className="field" style={{ marginBottom: '12px' }}>
              <label>Apple ID email</label>
              <input
                className="input" type="email" autoFocus
                placeholder="you@icloud.com"
                value={appleCreds.username}
                onChange={e => setAppleCreds(c => ({ ...c, username: e.target.value }))}
                disabled={appleBusy}
              />
            </div>
            <div className="field" style={{ marginBottom: '20px' }}>
              <label>App-Specific Password</label>
              <input
                className="input" type="password"
                placeholder="xxxx-xxxx-xxxx-xxxx"
                value={appleCreds.password}
                onChange={e => setAppleCreds(c => ({ ...c, password: e.target.value }))}
                disabled={appleBusy}
              />
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => { setAppleModal(false); setAppleCreds({ username: '', password: '' }) }}
                disabled={appleBusy}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary btn-sm"
                onClick={connectApple}
                disabled={appleBusy}
              >
                {appleBusy ? 'Verifying…' : 'Connect'}
              </button>
            </div>
          </div>
        </div>
      )}
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
