// src/pages/PeoplePage.jsx
// Stage 1 social feature: profile editor, user search by handle, connection requests.
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { social } from '../api/index.js'

const TABS = [
  { id: 'find',     label: 'Find people' },
  { id: 'accepted', label: 'Connected' },
  { id: 'pending',  label: 'Requests' },
]

export default function PeoplePage() {
  const [tab, setTab] = useState('find')

  return (
    <div style={{ maxWidth: 840, margin: '0 auto', padding: '32px 24px 80px' }}>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', color: 'var(--cream)', letterSpacing: '-0.02em', margin: 0 }}>
          People
        </h1>
        <p style={{ color: 'var(--cream-dim)', marginTop: 6, fontSize: '0.95rem' }}>
          Find friends by their handle and connect with them. Once connected, you can chat and plan trips together.
        </p>
      </header>

      <ProfilePanel />

      <div style={{ display: 'flex', gap: 4, marginTop: 32, borderBottom: '1px solid var(--border)' }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              background: 'none',
              border: 'none',
              padding: '12px 16px',
              color: tab === t.id ? 'var(--cream)' : 'var(--cream-dim)',
              borderBottom: tab === t.id ? '2px solid var(--terra)' : '2px solid transparent',
              cursor: 'pointer',
              fontSize: '0.9rem',
              fontWeight: tab === t.id ? 500 : 400,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ marginTop: 24 }}>
        {tab === 'find'     && <FindTab />}
        {tab === 'accepted' && <ConnectionsTab status="accepted" emptyLabel="No connections yet. Find people on the first tab." />}
        {tab === 'pending'  && <ConnectionsTab status="pending"  emptyLabel="No pending requests." withActions />}
      </div>
    </div>
  )
}


// ── Profile panel ─────────────────────────────────────────────────────────

function ProfilePanel() {
  const [profile, setProfile] = useState(null)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft]     = useState({ display_name: '', bio: '', visibility: 'public' })
  const [newHandle, setNewHandle] = useState('')
  const [saving, setSaving]   = useState(false)
  const [error, setError]     = useState('')

  const load = useCallback(async () => {
    try {
      const p = await social.profile.get()
      setProfile(p)
      setDraft({ display_name: p.display_name || '', bio: p.bio || '', visibility: p.visibility || 'public' })
    } catch (err) {
      setError('Could not load your profile.')
    }
  }, [])

  useEffect(() => { load() }, [load])

  const save = async () => {
    setSaving(true)
    setError('')
    try {
      const updated = await social.profile.update(draft)
      setProfile(updated)
      if (newHandle && newHandle !== profile.handle) {
        try {
          const afterHandle = await social.profile.updateHandle(newHandle.trim().toLowerCase())
          setProfile(afterHandle)
          setNewHandle('')
        } catch (e) {
          setError(e.response?.data?.error?.message || 'Could not change your handle.')
          return  // Leave edit mode open so user can correct
        }
      }
      setEditing(false)
    } catch (e) {
      setError(e.response?.data?.error?.message || 'Could not save.')
    } finally {
      setSaving(false)
    }
  }

  if (!profile) {
    return (
      <div style={cardStyle}>
        <div style={{ color: 'var(--cream-dim)' }}>Loading your profile…</div>
      </div>
    )
  }

  if (!editing) {
    return (
      <div style={cardStyle}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
          <Avatar handle={profile.handle} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ color: 'var(--cream)', fontSize: '1.1rem', fontWeight: 500 }}>
              {profile.display_name || profile.handle}
            </div>
            <div style={{ color: 'var(--terra-light)', fontSize: '0.85rem' }}>@{profile.handle}</div>
            {profile.bio && (
              <div style={{ color: 'var(--cream-dim)', marginTop: 8, fontSize: '0.9rem' }}>
                {profile.bio}
              </div>
            )}
            <div style={{ color: 'var(--cream-dim)', marginTop: 8, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {profile.visibility === 'connections_only' ? 'Visible to connections' : 'Public profile'}
            </div>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={() => setEditing(true)}>Edit</button>
        </div>
      </div>
    )
  }

  return (
    <div style={cardStyle}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div>
          <label style={labelStyle}>Handle</label>
          <input
            className="input"
            value={newHandle || profile.handle}
            onChange={e => setNewHandle(e.target.value)}
            placeholder={profile.handle}
          />
          <div style={{ fontSize: '0.7rem', color: 'var(--cream-dim)', marginTop: 4 }}>
            3–30 chars, lowercase letters, numbers, underscores. Changeable once every 30 days.
          </div>
        </div>
        <div>
          <label style={labelStyle}>Display name</label>
          <input
            className="input"
            value={draft.display_name}
            onChange={e => setDraft({ ...draft, display_name: e.target.value })}
            maxLength={80}
          />
        </div>
        <div>
          <label style={labelStyle}>Bio</label>
          <textarea
            className="input"
            value={draft.bio}
            onChange={e => setDraft({ ...draft, bio: e.target.value })}
            maxLength={280}
            rows={3}
          />
        </div>
        <div>
          <label style={labelStyle}>Visibility</label>
          <select
            className="input"
            value={draft.visibility}
            onChange={e => setDraft({ ...draft, visibility: e.target.value })}
          >
            <option value="public">Public — anyone can see your profile</option>
            <option value="connections_only">Connections only — bio hidden from strangers</option>
          </select>
        </div>

        {error && <div className="alert alert-error">⚠ {error}</div>}

        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button className="btn btn-ghost btn-sm" onClick={() => { setEditing(false); setError(''); setNewHandle('') }}>Cancel</button>
          <button className="btn btn-primary btn-sm" onClick={save} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}


// ── Find tab ──────────────────────────────────────────────────────────────

function FindTab() {
  const [handle, setHandle] = useState('')
  const [result, setResult] = useState(null)   // null = no search yet, {found, user, is_self}
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState('')
  const [requesting, setRequesting] = useState(false)

  const search = async (e) => {
    e?.preventDefault()
    setError('')
    setResult(null)
    if (!handle.trim()) return
    setLoading(true)
    try {
      const res = await social.users.search(handle.trim().toLowerCase().replace(/^@/, ''))
      setResult(res)
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Search failed.')
    } finally {
      setLoading(false)
    }
  }

  const sendRequest = async () => {
    setRequesting(true)
    setError('')
    try {
      await social.connections.request(result.user.handle)
      // Re-fetch to reflect new connection state
      const res = await social.users.search(result.user.handle)
      setResult(res)
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Could not send request.')
    } finally {
      setRequesting(false)
    }
  }

  return (
    <div>
      <form onSubmit={search} style={{ display: 'flex', gap: 8 }}>
        <input
          className="input"
          placeholder="Enter a handle, e.g. jane"
          value={handle}
          onChange={e => setHandle(e.target.value)}
          autoFocus
          style={{ flex: 1 }}
        />
        <button className="btn btn-primary" type="submit" disabled={loading || !handle.trim()}>
          {loading ? 'Searching…' : 'Search'}
        </button>
      </form>

      {error && <div className="alert alert-error" style={{ marginTop: 16 }}>⚠ {error}</div>}

      {result && !result.found && (
        <div style={{ ...cardStyle, marginTop: 16, color: 'var(--cream-dim)' }}>
          No user found with that handle.
        </div>
      )}

      {result?.found && (
        <div style={{ ...cardStyle, marginTop: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Avatar handle={result.user.handle} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ color: 'var(--cream)', fontSize: '1.05rem', fontWeight: 500 }}>
                {result.user.display_name || result.user.handle}
              </div>
              <div style={{ color: 'var(--terra-light)', fontSize: '0.85rem' }}>@{result.user.handle}</div>
              {result.user.bio && (
                <div style={{ color: 'var(--cream-dim)', marginTop: 6, fontSize: '0.85rem' }}>{result.user.bio}</div>
              )}
            </div>
            <div>
              {result.is_self ? (
                <span style={{ color: 'var(--cream-dim)', fontSize: '0.85rem' }}>This is you</span>
              ) : (
                <ConnectionCTA
                  connection={result.user.connection}
                  onConnect={sendRequest}
                  busy={requesting}
                />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ConnectionCTA({ connection, onConnect, busy }) {
  if (!connection) {
    return <button className="btn btn-primary btn-sm" onClick={onConnect} disabled={busy}>
      {busy ? 'Sending…' : 'Connect'}
    </button>
  }
  if (connection.status === 'accepted') {
    return <span style={{ color: 'var(--success, #7aae7a)', fontSize: '0.85rem' }}>Connected ✓</span>
  }
  if (connection.status === 'pending' && connection.direction === 'outgoing') {
    return <span style={{ color: 'var(--cream-dim)', fontSize: '0.85rem' }}>Request sent</span>
  }
  if (connection.status === 'pending' && connection.direction === 'incoming') {
    return <span style={{ color: 'var(--terra-light)', fontSize: '0.85rem' }}>Awaiting your reply — see Requests tab</span>
  }
  return <button className="btn btn-primary btn-sm" onClick={onConnect} disabled={busy}>Connect</button>
}


// ── Connections tab (accepted OR pending) ───────────────────────────────

function ConnectionsTab({ status, emptyLabel, withActions }) {
  const navigate = useNavigate()
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const res = await social.connections.list(status)
      setItems(res.results || [])
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Could not load connections.')
    }
  }, [status])

  useEffect(() => { load() }, [load])

  const act = async (fn, id) => {
    try {
      await fn(id)
      load()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Action failed.')
    }
  }

  if (items === null) return <div style={{ color: 'var(--cream-dim)' }}>Loading…</div>
  if (error)           return <div className="alert alert-error">⚠ {error}</div>
  if (items.length === 0) return <div style={{ ...cardStyle, color: 'var(--cream-dim)' }}>{emptyLabel}</div>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {items.map(conn => (
        <div key={conn.id} style={cardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <Avatar handle={conn.other_user.handle} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ color: 'var(--cream)', fontSize: '0.95rem', fontWeight: 500 }}>
                {conn.other_user.display_name || conn.other_user.handle}
              </div>
              <div style={{ color: 'var(--terra-light)', fontSize: '0.8rem' }}>@{conn.other_user.handle}</div>
              {conn.other_user.bio && (
                <div style={{ color: 'var(--cream-dim)', marginTop: 4, fontSize: '0.8rem' }}>{conn.other_user.bio}</div>
              )}
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              {withActions && conn.direction === 'incoming' && (
                <>
                  <button className="btn btn-primary btn-sm" onClick={() => act(social.connections.accept, conn.id)}>
                    Accept
                  </button>
                  <button className="btn btn-ghost btn-sm" onClick={() => act(social.connections.reject, conn.id)}>
                    Reject
                  </button>
                </>
              )}
              {withActions && conn.direction === 'outgoing' && (
                <>
                  <span style={{ color: 'var(--cream-dim)', fontSize: '0.8rem', alignSelf: 'center' }}>Sent</span>
                  <button className="btn btn-ghost btn-sm" onClick={() => act(social.connections.remove, conn.id)}>
                    Cancel
                  </button>
                </>
              )}
              {!withActions && status === 'accepted' && (
                <>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => navigate('/messages', { state: { openUserId: conn.other_user.id } })}
                  >
                    Message
                  </button>
                  <button className="btn btn-ghost btn-sm" onClick={() => {
                    if (confirm(`Remove connection with @${conn.other_user.handle}?`)) {
                      act(social.connections.remove, conn.id)
                    }
                  }}>
                    Remove
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}


// ── Small presentational bits ─────────────────────────────────────────────

function Avatar({ handle }) {
  const initial = (handle?.[0] || '?').toUpperCase()
  return (
    <div style={{
      width: 48,
      height: 48,
      borderRadius: '50%',
      background: 'var(--terra)',
      color: '#fff',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '1.2rem',
      fontWeight: 500,
      flexShrink: 0,
    }}>
      {initial}
    </div>
  )
}

const cardStyle = {
  background: 'var(--surface-1)',
  border: '1px solid var(--border)',
  borderRadius: 16,
  padding: 20,
}

const labelStyle = {
  display: 'block',
  fontSize: '0.75rem',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  color: 'var(--cream-dim)',
  marginBottom: 6,
}
