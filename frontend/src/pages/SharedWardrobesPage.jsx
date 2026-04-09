// src/pages/SharedWardrobesPage.jsx
// List of shared wardrobes you're a member of + create new one.
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { sharedWardrobes as api } from '../api/index.js'

export default function SharedWardrobesPage() {
  const navigate = useNavigate()
  const [wardrobes, setWardrobes] = useState([])
  const [loading, setLoading]     = useState(true)
  const [creating, setCreating]   = useState(false)
  const [showForm, setShowForm]   = useState(false)
  const [name, setName]           = useState('')
  const [description, setDescription] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const list = await api.list()
      setWardrobes(Array.isArray(list) ? list : (list.results || []))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const create = async (e) => {
    e?.preventDefault()
    if (!name.trim() || creating) return
    setCreating(true)
    try {
      const w = await api.create({ name: name.trim(), description: description.trim() })
      setName(''); setDescription(''); setShowForm(false)
      load()
      navigate(`/shared-wardrobes/${w.id}`)
    } catch (err) {
      window.__toast?.(err.response?.data?.error?.message || 'Could not create wardrobe.', 'error')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div>
      <div className="page-header fade-up">
        <div className="date-line">Social</div>
        <h1>Shared Wardrobes</h1>
        <p>Collaborate on wardrobes with the people you're connected with. Everyone sees updates live.</p>
      </div>

      <div className="fade-up fade-up-delay-1" style={{ marginBottom: 20 }}>
        {!showForm ? (
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            + Create shared wardrobe
          </button>
        ) : (
          <form onSubmit={create} className="card" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <label style={labelStyle}>Name</label>
              <input
                className="input"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Summer in Portugal"
                autoFocus
                maxLength={120}
              />
            </div>
            <div>
              <label style={labelStyle}>Description (optional)</label>
              <textarea
                className="input"
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="What's this wardrobe for?"
                maxLength={500}
                rows={3}
              />
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setShowForm(false); setName(''); setDescription('') }}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary btn-sm" disabled={creating || !name.trim()}>
                {creating ? 'Creating…' : 'Create'}
              </button>
            </div>
          </form>
        )}
      </div>

      <div className="fade-up fade-up-delay-2">
        {loading ? (
          <div style={{ color: 'var(--cream-dim)' }}>Loading…</div>
        ) : wardrobes.length === 0 ? (
          <div className="card" style={{ padding: 32, textAlign: 'center', color: 'var(--cream-dim)' }}>
            No shared wardrobes yet. Create one above, or ask a friend to add you to theirs.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
            {wardrobes.map(w => (
              <button
                key={w.id}
                onClick={() => navigate(`/shared-wardrobes/${w.id}`)}
                className="card"
                style={{
                  padding: 20,
                  textAlign: 'left',
                  cursor: 'pointer',
                  border: '1px solid var(--border)',
                  background: 'var(--surface-1)',
                  color: 'var(--cream)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 10,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                  <div style={{ fontWeight: 500, fontSize: '1rem' }}>{w.name}</div>
                  {w.my_role === 'owner' && (
                    <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: 'var(--terra-light)', letterSpacing: '0.05em' }}>
                      Owner
                    </span>
                  )}
                </div>
                {w.description && (
                  <div style={{ fontSize: '0.8125rem', color: 'var(--cream-dim)', lineHeight: 1.4 }}>
                    {w.description}
                  </div>
                )}
                <div style={{ display: 'flex', gap: 12, fontSize: '0.75rem', color: 'var(--cream-dim)', marginTop: 'auto' }}>
                  <span>{w.item_count} item{w.item_count === 1 ? '' : 's'}</span>
                  <span>•</span>
                  <span>{w.members?.length || 0} member{w.members?.length === 1 ? '' : 's'}</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

const labelStyle = {
  display: 'block',
  fontSize: '0.75rem',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  color: 'var(--cream-dim)',
  marginBottom: 6,
}
