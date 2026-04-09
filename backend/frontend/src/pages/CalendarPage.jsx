// src/pages/CalendarPage.jsx
import React, { useState, useEffect } from 'react'
import { auth as authApi } from '../api/index.js'

const api = {
  calendarStatus:       () => fetch('/api/calendar/status/', { headers: authHeader() }).then(r => r.json()),
  googleConnectUrl:     () => fetch('/api/calendar/google/connect/', { headers: authHeader() }).then(r => r.json()),
  googleSync:           () => fetch('/api/calendar/google/sync/', { method: 'POST', headers: authHeader() }).then(r => r.json()),
  googleDisconnect:     () => fetch('/api/calendar/google/disconnect/', { method: 'POST', headers: authHeader() }).then(r => r.json()),
  appleConnect: (body) => fetch('/api/calendar/apple/connect/', { method:'POST', headers:{...authHeader(),'Content-Type':'application/json'}, body: JSON.stringify(body) }).then(r => r.json()),
  appleSync:            () => fetch('/api/calendar/apple/sync/', { method: 'POST', headers: authHeader() }).then(r => r.json()),
  appleDisconnect:      () => fetch('/api/calendar/apple/disconnect/', { method: 'POST', headers: authHeader() }).then(r => r.json()),
  outlookConnectUrl:    () => fetch('/api/calendar/outlook/connect/', { headers: authHeader() }).then(r => r.json()),
  outlookSync:          () => fetch('/api/calendar/outlook/sync/', { method: 'POST', headers: authHeader() }).then(r => r.json()),
  outlookDisconnect:    () => fetch('/api/calendar/outlook/disconnect/', { method: 'POST', headers: authHeader() }).then(r => r.json()),
}

function authHeader() {
  const token = localStorage.getItem('gg_access')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function fmt(dateStr) {
  if (!dateStr) return 'Never'
  return new Date(dateStr).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
}

export default function CalendarPage() {
  const [status,   setStatus]   = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [msg,      setMsg]      = useState({ text: '', type: '' })
  const [syncing,  setSyncing]  = useState({ google: false, apple: false, outlook: false })

  useEffect(() => { loadStatus() }, [])

  // Handle OAuth callback params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const calendar = params.get('calendar')
    const calStatus = params.get('status')
    if (calendar === 'google') {
      if (calStatus === 'connected') flash('Google Calendar connected successfully!', 'success')
      else if (calStatus === 'denied') flash('Google Calendar access was denied.', 'error')
      else if (calStatus === 'error') flash(`Google Calendar connection failed (${params.get('reason') || 'unknown error'}).`, 'error')
      window.history.replaceState({}, '', '/calendar')
      loadStatus()
    }
    if (calendar === 'outlook') {
      if (calStatus === 'connected') flash('Outlook Calendar connected successfully!', 'success')
      else if (calStatus === 'denied') flash('Outlook Calendar access was denied.', 'error')
      else if (calStatus === 'error') flash(`Outlook Calendar connection failed (${params.get('reason') || 'unknown error'}).`, 'error')
      window.history.replaceState({}, '', '/calendar')
      loadStatus()
    }
  }, [])

  const loadStatus = async () => {
    setLoading(true)
    try {
      const data = await api.calendarStatus()
      if (data.error) throw new Error(data.error.message)
      setStatus(data)
    } catch (e) { flash(e.message, 'error') }
    finally { setLoading(false) }
  }

  const flash = (text, type = 'success') => {
    setMsg({ text, type })
    setTimeout(() => setMsg({ text: '', type: '' }), 4000)
  }

  // ── Google ────────────────────────────────────────────────────────────
  const connectGoogle = async () => {
    try {
      const data = await api.googleConnectUrl()
      if (data.error) { flash(data.error.message, 'error'); return }
      // Open OAuth in same tab — Google requires a real browser redirect
      window.location.href = data.auth_url
    } catch (e) { flash(e.message, 'error') }
  }

  const syncGoogle = async () => {
    setSyncing(s => ({ ...s, google: true }))
    try {
      const data = await api.googleSync()
      if (data.error) flash(data.error.message, 'error')
      else {
        flash(`Synced — ${data.created} new, ${data.updated} updated events.`)
        loadStatus()
      }
    } catch (e) { flash(e.message, 'error') }
    finally { setSyncing(s => ({ ...s, google: false })) }
  }

  const disconnectGoogle = async () => {
    if (!window.confirm('Disconnect Google Calendar? Synced events will be kept.')) return
    await api.googleDisconnect()
    flash('Google Calendar disconnected.')
    loadStatus()
  }

  // ── Apple ─────────────────────────────────────────────────────────────
  const syncApple = async () => {
    setSyncing(s => ({ ...s, apple: true }))
    try {
      const data = await api.appleSync()
      if (data.error) flash(data.error.message, 'error')
      else {
        flash(`Synced — ${data.created} new, ${data.updated} updated events.`)
        loadStatus()
      }
    } catch (e) { flash(e.message, 'error') }
    finally { setSyncing(s => ({ ...s, apple: false })) }
  }

  // ── Outlook ───────────────────────────────────────────────────────────
  const connectOutlook = async () => {
    try {
      const data = await api.outlookConnectUrl()
      if (data.error) { flash(data.error.message, 'error'); return }
      window.location.href = data.auth_url
    } catch (e) { flash(e.message, 'error') }
  }

  const syncOutlook = async () => {
    setSyncing(s => ({ ...s, outlook: true }))
    try {
      const data = await api.outlookSync()
      if (data.error) flash(data.error.message, 'error')
      else { flash(`Synced — ${data.created} new, ${data.updated} updated events.`); loadStatus() }
    } catch (e) { flash(e.message, 'error') }
    finally { setSyncing(s => ({ ...s, outlook: false })) }
  }

  const disconnectOutlook = async () => {
    if (!window.confirm('Disconnect Outlook Calendar?')) return
    await api.outlookDisconnect()
    flash('Outlook Calendar disconnected.')
    loadStatus()
  }

  const disconnectApple = async () => {
    if (!window.confirm('Disconnect Apple Calendar? Credentials will be removed.')) return
    await api.appleDisconnect()
    flash('Apple Calendar disconnected.')
    loadStatus()
  }

  return (
    <div>
      <div className="page-header fade-up">
        <div className="date-line">Calendar</div>
        <h1>Connect Your Calendar</h1>
        <p>Arokah reads your schedule to suggest the right outfit for every event.</p>
      </div>

      {msg.text && (
        <div className={`alert alert-${msg.type === 'error' ? 'error' : 'success'} fade-up`}
             style={{ marginBottom: 20 }}>
          {msg.type === 'error' ? '⚠' : '✓'} {msg.text}
        </div>
      )}

      {loading ? (
        <div style={{ display:'flex', gap:16 }}>
          {[1,2].map(i => <div key={i} className="skeleton" style={{ height:220, flex:1, borderRadius:'var(--radius-lg)' }} />)}
        </div>
      ) : (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(300px,1fr))", gap:24 }} className="fade-up fade-up-delay-1">

          {/* ── Google Calendar ──────────────────────────────────────── */}
          <div className="card">
            <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:20 }}>
              <GoogleIcon />
              <div>
                <div style={{ fontWeight:500, color:'var(--cream)', fontSize:'1rem' }}>Google Calendar</div>
                <div style={{ fontSize:'0.75rem', color:'var(--cream-dim)' }}>OAuth 2.0 — read-only access</div>
              </div>
              <div style={{ marginLeft:'auto' }}>
                {status?.google?.connected
                  ? <span className="badge badge-sage">✓ Connected</span>
                  : <span className="badge" style={{ background:'var(--surface-3)', color:'var(--cream-dim)' }}>Not connected</span>
                }
              </div>
            </div>

            {status?.google?.connected ? (
              <>
                <div style={{ display:'flex', flexDirection:'column', gap:8, marginBottom:20, padding:'12px 14px', background:'var(--surface-2)', borderRadius:'var(--radius-md)', border:'1px solid var(--border)' }}>
                  <Row label="Account" value={status.google.email} />
                  <Row label="Last synced" value={fmt(status.google.synced_at)} />
                </div>
                <div style={{ display:'flex', gap:8 }}>
                  <button className="btn btn-secondary" style={{ flex:1 }} onClick={syncGoogle} disabled={syncing.google}>
                    {syncing.google ? <><span className="spinner" style={{width:14,height:14}}/> Syncing…</> : '↻ Sync now'}
                  </button>
                  <button className="btn btn-ghost btn-sm" onClick={disconnectGoogle} style={{ color:'var(--cream-dim)' }}>
                    Disconnect
                  </button>
                </div>
              </>
            ) : (
              <>
                <p style={{ fontSize:'0.875rem', color:'var(--cream-dim)', lineHeight:1.6, marginBottom:20 }}>
                  Connect your Google account to automatically import events from Google Calendar.
                  Arokah only requests <strong style={{color:'var(--cream)'}}>read-only</strong> access — it can never modify your calendar.
                </p>
                <HowToSteps steps={[
                  'Click Connect Google Calendar below',
                  'Sign in with your Google account',
                  'Grant read-only calendar access',
                  'Events sync automatically',
                ]} />
                <button className="btn btn-primary btn-full" style={{ marginTop:16 }} onClick={connectGoogle}>
                  Connect Google Calendar
                </button>
              </>
            )}
          </div>

          {/* ── Apple Calendar ───────────────────────────────────────── */}
          <div className="card">
            <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:20 }}>
              <AppleIcon />
              <div>
                <div style={{ fontWeight:500, color:'var(--cream)', fontSize:'1rem' }}>Apple Calendar</div>
                <div style={{ fontSize:'0.75rem', color:'var(--cream-dim)' }}>CalDAV — App-Specific Password</div>
              </div>
              <div style={{ marginLeft:'auto' }}>
                {status?.apple?.connected
                  ? <span className="badge badge-sage">✓ Connected</span>
                  : <span className="badge" style={{ background:'var(--surface-3)', color:'var(--cream-dim)' }}>Not connected</span>
                }
              </div>
            </div>

            {status?.apple?.connected ? (
              <>
                <div style={{ display:'flex', flexDirection:'column', gap:8, marginBottom:20, padding:'12px 14px', background:'var(--surface-2)', borderRadius:'var(--radius-md)', border:'1px solid var(--border)' }}>
                  <Row label="Apple ID" value={status.apple.username} />
                  <Row label="Last synced" value={fmt(status.apple.synced_at)} />
                </div>
                <div style={{ display:'flex', gap:8 }}>
                  <button className="btn btn-secondary" style={{ flex:1 }} onClick={syncApple} disabled={syncing.apple}>
                    {syncing.apple ? <><span className="spinner" style={{width:14,height:14}}/> Syncing…</> : '↻ Sync now'}
                  </button>
                  <button className="btn btn-ghost btn-sm" onClick={disconnectApple} style={{ color:'var(--cream-dim)' }}>
                    Disconnect
                  </button>
                </div>
              </>
            ) : (
              <>
                <p style={{ fontSize:'0.875rem', color:'var(--cream-dim)', lineHeight:1.6, marginBottom:16 }}>
                  Connect iCloud Calendar using your Apple ID and an{' '}
                  <strong style={{color:'var(--cream)'}}>App-Specific Password</strong>
                  {' '}— your regular Apple ID password will not work.
                </p>
                <div className="alert alert-info" style={{ marginBottom:16, fontSize:'0.8rem' }}>
                  ℹ Generate an App-Specific Password at{' '}
                  <a href="https://appleid.apple.com/account/manage" target="_blank" rel="noopener noreferrer"
                     style={{ color:'var(--sky)' }}>
                    appleid.apple.com
                  </a>
                  {' '}→ Security → App-Specific Passwords
                </div>
                <AppleConnectForm onConnect={loadStatus} onFlash={flash} />
              </>
            )}
          </div>
        </div>
      )}

      {/* How events work */}
      <div className="card fade-up fade-up-delay-2" style={{ marginTop:24 }}>
        <div className="card-label" style={{ marginBottom:12 }}>How calendar sync works</div>
        <div className="grid-3" style={{ gap:16 }}>
          {[
            { icon:'📅', title:'Events imported',   body:'Arokah syncs events from the last 7 days and next 60 days.' },
            { icon:'🏷',  title:'Auto-classified',   body:'Events are classified automatically: standup → casual, client meeting → smart, gym → activewear.' },
            { icon:'👗',  title:'Outfit suggested',  body:'The daily look engine picks the highest-formality outfit needed for your whole day.' },
          ].map(({ icon, title, body }) => (
            <div key={title} style={{ display:'flex', flexDirection:'column', gap:6 }}>
              <span style={{ fontSize:'1.5rem' }}>{icon}</span>
              <div style={{ fontSize:'0.875rem', fontWeight:500, color:'var(--cream)' }}>{title}</div>
              <div style={{ fontSize:'0.8rem', color:'var(--cream-dim)', lineHeight:1.5 }}>{body}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────

function Row({ label, value }) {
  return (
    <div style={{ display:'flex', justifyContent:'space-between', fontSize:'0.8rem' }}>
      <span style={{ color:'var(--cream-dim)' }}>{label}</span>
      <span style={{ color:'var(--cream)' }}>{value}</span>
    </div>
  )
}

function HowToSteps({ steps }) {
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
      {steps.map((step, i) => (
        <div key={i} style={{ display:'flex', alignItems:'center', gap:10, fontSize:'0.8rem', color:'var(--cream-dim)' }}>
          <span style={{ width:20, height:20, borderRadius:'50%', background:'var(--surface-3)', border:'1px solid var(--border)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'0.65rem', color:'var(--terra)', flexShrink:0, fontWeight:600 }}>
            {i+1}
          </span>
          {step}
        </div>
      ))}
    </div>
  )
}

function AppleConnectForm({ onConnect, onFlash }) {
  const [form, setForm]       = useState({ username:'', password:'' })
  const [loading, setLoading] = useState(false)
  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const res  = await fetch('/api/calendar/apple/connect/', {
        method:  'POST',
        headers: { 'Content-Type':'application/json', ...{ Authorization:`Bearer ${localStorage.getItem('gg_access')}` } },
        body:    JSON.stringify(form),
      })
      const data = await res.json()
      if (data.error) onFlash(data.error.message, 'error')
      else { onFlash(`Apple Calendar connected — ${data.message}`); onConnect() }
    } catch (e) { onFlash(e.message, 'error') }
    finally { setLoading(false) }
  }

  return (
    <form onSubmit={submit} style={{ display:'flex', flexDirection:'column', gap:12 }}>
      <div className="input-group">
        <label className="input-label">Apple ID (email)</label>
        <input className="input" type="email" value={form.username} onChange={set('username')}
               placeholder="you@icloud.com" required />
      </div>
      <div className="input-group">
        <label className="input-label">App-Specific Password</label>
        <input className="input" type="password" value={form.password} onChange={set('password')}
               placeholder="xxxx-xxxx-xxxx-xxxx" required />
        <span className="input-hint">Not your Apple ID password — generate one at appleid.apple.com</span>
      </div>
      <button type="submit" className="btn btn-primary" disabled={loading}>
        {loading ? 'Connecting…' : 'Connect Apple Calendar'}
      </button>
    </form>
  )
}

function GoogleIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  )
}

function OutlookIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
      <rect width="24" height="24" rx="4" fill="#0078D4"/>
      <path d="M13 6h7v3h-7V6zm0 4h7v3h-7v-3zm0 4h7v3h-7v-3zM4 6h8v12H4z" fill="white" opacity="0.9"/>
      <path d="M5 9a3 3 0 1 1 6 0 3 3 0 0 1-6 0z" fill="#0078D4"/>
    </svg>
  )
}

function AppleIcon() {
  return (
    <svg width="24" height="28" viewBox="0 0 24 28" fill="var(--cream)">
      <path d="M17.05 14.53c-.02-2.16 1.75-3.2 1.83-3.25-1-1.47-2.56-1.67-3.11-1.69-1.33-.13-2.6.78-3.27.78-.68 0-1.72-.77-2.83-.74-1.45.02-2.8.84-3.54 2.13-1.51 2.63-.39 6.53 1.08 8.67.72 1.04 1.57 2.21 2.69 2.17 1.08-.04 1.49-.7 2.8-.7 1.3 0 1.67.7 2.81.68 1.16-.02 1.9-1.06 2.61-2.11.82-1.2 1.16-2.37 1.18-2.43-.03-.01-2.25-.86-2.25-3.51zM14.9 7.6c.6-.73 1-1.74.89-2.75-.86.04-1.9.57-2.51 1.29-.55.64-1.03 1.67-.9 2.65.96.07 1.93-.48 2.52-1.19z"/>
    </svg>
  )
}
