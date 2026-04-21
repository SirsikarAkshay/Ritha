// src/pages/SharedWardrobeDetailPage.jsx
// Detail view: items grid + members panel + invite + add item. Live updates via WebSocket.
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { sharedWardrobes as api, social, wardrobe as wardrobeApi } from '../api/index.js'
import { connectWebSocket } from '../api/ws.js'
import { useAuth } from '../hooks/useAuth.jsx'

export default function SharedWardrobeDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [wardrobe, setWardrobe] = useState(null)
  const [items, setItems]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')
  const [showAddItem, setShowAddItem] = useState(false)
  const [showInvite, setShowInvite]   = useState(false)
  const [confirmDialog, setConfirmDialog] = useState(null)
  const wsRef = useRef(null)

  const loadAll = async () => {
    setLoading(true)
    setError('')
    try {
      const [w, its] = await Promise.all([api.get(id), api.items.list(id)])
      setWardrobe(w)
      setItems(Array.isArray(its) ? its : [])
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Could not load wardrobe.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadAll() }, [id])

  // WebSocket for live updates
  useEffect(() => {
    if (!id) return
    const ws = connectWebSocket(`/ws/shared-wardrobe/${id}/`)
    wsRef.current = ws
    ws.on('message', (data) => {
      if (data?.type !== 'wardrobe.event') return
      const { event_type, payload } = data
      if (event_type === 'item_added') {
        setItems(prev => prev.some(i => i.id === payload.id) ? prev : [...prev, payload])
      } else if (event_type === 'item_removed') {
        setItems(prev => prev.filter(i => i.id !== payload.item_id))
      } else if (event_type === 'member_added') {
        setWardrobe(prev => prev ? { ...prev, members: [...(prev.members || []), payload] } : prev)
      } else if (event_type === 'member_removed') {
        setWardrobe(prev => prev ? { ...prev, members: (prev.members || []).filter(m => m.user?.id !== payload.user_id) } : prev)
      } else if (event_type === 'wardrobe_deleted') {
        window.__toast?.('This wardrobe was deleted.', 'info')
        navigate('/shared-wardrobes')
      }
    })
    return () => ws.close()
  }, [id, navigate])

  const askConfirm = (message, onConfirm, danger = false) => {
    setConfirmDialog({ message, onConfirm, danger })
  }

  const deleteItem = (itemId) => {
    askConfirm('Remove this item from the wardrobe?', async () => {
      try {
        await api.items.delete(id, itemId)
        setItems(prev => prev.filter(i => i.id !== itemId))
      } catch (err) {
        window.__toast?.(err.response?.data?.error?.message || 'Could not remove item.', 'error')
      }
    })
  }

  const deleteWardrobe = () => {
    askConfirm(`Delete "${wardrobe.name}"? This cannot be undone.`, async () => {
      try {
        await api.delete(id)
        navigate('/shared-wardrobes')
      } catch (err) {
        window.__toast?.(err.response?.data?.error?.message || 'Could not delete.', 'error')
      }
    }, true)
  }

  const leaveWardrobe = () => {
    askConfirm('Leave this wardrobe?', async () => {
      try {
        await api.members.remove(id, user.id)
        navigate('/shared-wardrobes')
      } catch (err) {
        window.__toast?.(err.response?.data?.error?.message || 'Could not leave.', 'error')
      }
    })
  }

  const removeMember = (userId) => {
    askConfirm('Remove this member?', async () => {
      try {
        await api.members.remove(id, userId)
        setWardrobe(prev => ({ ...prev, members: prev.members.filter(m => m.user?.id !== userId) }))
      } catch (err) {
        window.__toast?.(err.response?.data?.error?.message || 'Could not remove member.', 'error')
      }
    })
  }

  if (loading) return <div style={{ color: 'var(--cream-dim)' }}>Loading…</div>
  if (error)   return <div className="alert alert-error">⚠ {error}</div>
  if (!wardrobe) return null

  const isOwner = wardrobe.my_role === 'owner'

  return (
    <div>
      <div className="page-header fade-up">
        <button
          onClick={() => navigate('/shared-wardrobes')}
          className="btn btn-ghost btn-sm"
          style={{ marginBottom: 12 }}
        >
          ← Back
        </button>
        <div className="date-line">Shared Wardrobe</div>
        <h1>{wardrobe.name}</h1>
        {wardrobe.description && <p>{wardrobe.description}</p>}
      </div>

      <div className="fade-up fade-up-delay-1" style={{
        display: 'grid',
        gridTemplateColumns: '1fr 300px',
        gap: 20,
      }}>
        {/* ── Items ───────────────────────────────────────── */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <h2 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--cream)' }}>Items ({items.length})</h2>
            <button className="btn btn-primary btn-sm" onClick={() => setShowAddItem(true)}>+ Add item</button>
          </div>

          {showAddItem && (
            <AddItemForm
              wardrobeId={id}
              onDone={(newItem) => {
                setShowAddItem(false)
                if (newItem) setItems(prev => prev.some(i => i.id === newItem.id) ? prev : [...prev, newItem])
              }}
            />
          )}

          {items.length === 0 ? (
            <div className="card" style={{ padding: 32, textAlign: 'center', color: 'var(--cream-dim)' }}>
              No items yet. Add the first one.
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
              {items.map(item => (
                <div key={item.id} className="card" style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {item.image_url && (
                    <img src={item.image_url} alt={item.name} style={{
                      width: '100%', height: 140, objectFit: 'cover', borderRadius: 8,
                    }} />
                  )}
                  <div style={{ fontWeight: 500, color: 'var(--cream)', fontSize: '0.9rem' }}>{item.name}</div>
                  {item.brand && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)' }}>{item.brand}</div>
                  )}
                  <div style={{ fontSize: '0.7rem', color: 'var(--terra-light)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {item.category}
                  </div>
                  {item.notes && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', fontStyle: 'italic' }}>{item.notes}</div>
                  )}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'auto', paddingTop: 8, borderTop: '1px solid var(--border)' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--cream-dim)' }}>
                      by @{item.added_by?.handle}
                    </span>
                    {(isOwner || item.added_by?.id === user?.id) && (
                      <button
                        onClick={() => deleteItem(item.id)}
                        className="btn btn-ghost btn-icon btn-sm"
                        title="Remove"
                        style={{ fontSize: '0.85rem' }}
                      >
                        ✕
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Members panel ───────────────────────────────── */}
        <div className="card" style={{ padding: 16, height: 'fit-content' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div className="card-label">Members</div>
            {isOwner && (
              <button className="btn btn-ghost btn-sm" onClick={() => setShowInvite(true)}>+ Invite</button>
            )}
          </div>

          {showInvite && (
            <InviteMemberForm
              wardrobeId={id}
              existingIds={wardrobe.members?.map(m => m.user?.id) || []}
              pendingIds={wardrobe.pending_invitee_ids || []}
              onDone={() => setShowInvite(false)}
            />
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {wardrobe.members?.map(m => (
              <div key={m.id} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: '50%',
                  background: 'var(--terra-dim)', color: 'var(--terra-light)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '0.8rem', fontWeight: 500, flexShrink: 0,
                }}>
                  {(m.user?.display_name || m.user?.handle || '?').charAt(0).toUpperCase()}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '0.8125rem', color: 'var(--cream)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {m.user?.display_name || '@' + m.user?.handle}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--cream-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {m.role}
                  </div>
                </div>
                {isOwner && m.role !== 'owner' && (
                  <button
                    onClick={() => removeMember(m.user?.id)}
                    className="btn btn-ghost btn-icon btn-sm"
                    title="Remove member"
                    style={{ fontSize: '0.8rem' }}
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>

          <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
            {isOwner ? (
              <button className="btn btn-ghost btn-sm" onClick={deleteWardrobe} style={{ width: '100%', color: 'var(--danger, #c66)' }}>
                Delete wardrobe
              </button>
            ) : (
              <button className="btn btn-ghost btn-sm" onClick={leaveWardrobe} style={{ width: '100%' }}>
                Leave wardrobe
              </button>
            )}
          </div>
        </div>
      </div>

      {confirmDialog && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 1000,
          background: 'rgba(0,0,0,.55)', display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} onClick={() => setConfirmDialog(null)}>
          <div className="card" style={{
            padding: 24, minWidth: 320, maxWidth: 400, textAlign: 'center',
          }} onClick={e => e.stopPropagation()}>
            <p style={{ color: 'var(--cream)', fontSize: '0.95rem', marginBottom: 20 }}>
              {confirmDialog.message}
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
              <button className="btn btn-ghost btn-sm" onClick={() => setConfirmDialog(null)}>Cancel</button>
              <button
                className="btn btn-sm"
                style={confirmDialog.danger
                  ? { background: 'var(--danger, #c66)', color: '#fff' }
                  : { background: 'var(--terra)', color: '#fff' }}
                onClick={() => { confirmDialog.onConfirm(); setConfirmDialog(null) }}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


// ── Add item form ──────────────────────────────────────────────────────────
// Shared wardrobe items only track a subset of fields, so we ignore the extra
// ones (formality/season/material) that analyze-image returns.
const SHARED_CATEGORIES = ['top', 'bottom', 'outerwear', 'footwear', 'accessory', 'other']

function AddItemForm({ wardrobeId, onDone }) {
  const [name, setName]         = useState('')
  const [category, setCategory] = useState('top')
  const [brand, setBrand]       = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [notes, setNotes]       = useState('')
  const [saving, setSaving]     = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [preview, setPreview]   = useState(null)

  const handleFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setPreview(URL.createObjectURL(file))
    setAnalyzing(true)
    try {
      const res = await wardrobeApi.analyzeImage(file)
      if (res.name)  setName(res.name)
      // Normalize categories onto the shared wardrobe's smaller set
      if (res.category) {
        const c = SHARED_CATEGORIES.includes(res.category) ? res.category : 'other'
        setCategory(c)
      }
      if (res.brand) setBrand(res.brand)
      // Bundle colors + material into notes so the info isn't lost
      const extras = []
      if (Array.isArray(res.colors) && res.colors.length) extras.push(res.colors.join(', '))
      if (res.material) extras.push(res.material)
      if (extras.length) setNotes(extras.join(' · '))
      window.__toast?.('Filled in from photo. Edit anything as needed.', 'success')
    } catch (err) {
      window.__toast?.(err.response?.data?.error?.message || 'Could not analyze photo.', 'error')
    } finally {
      setAnalyzing(false)
    }
  }

  const submit = async (e) => {
    e?.preventDefault()
    if (!name.trim() || saving) return
    setSaving(true)
    try {
      const item = await api.items.add(wardrobeId, {
        name: name.trim(), category, brand: brand.trim(), image_url: imageUrl.trim(), notes: notes.trim(),
      })
      onDone(item)
    } catch (err) {
      window.__toast?.(err.response?.data?.error?.message || 'Could not add item.', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="card" style={{ padding: 16, marginBottom: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Photo-based auto-fill */}
      <div style={{
        padding: 12,
        border: '1px dashed var(--border)',
        borderRadius: 10,
        background: 'var(--surface-2)',
        display: 'flex',
        gap: 12,
        alignItems: 'center',
      }}>
        {preview ? (
          <img src={preview} alt="preview" style={{ width: 56, height: 56, objectFit: 'cover', borderRadius: 6, flexShrink: 0 }} />
        ) : (
          <div style={{
            width: 56, height: 56, borderRadius: 6, background: 'var(--surface-3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1.25rem', color: 'var(--cream-dim)', flexShrink: 0,
          }}>📷</div>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: '0.8125rem', color: 'var(--cream)', fontWeight: 500 }}>
            {analyzing ? 'Analyzing photo…' : 'Add from a photo'}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--cream-dim)', marginBottom: 6 }}>
            We'll auto-fill the details.
          </div>
          <label className="btn btn-ghost btn-sm" style={{ cursor: analyzing ? 'wait' : 'pointer' }}>
            {analyzing ? 'Analyzing…' : (preview ? 'Try another' : 'Choose photo')}
            <input type="file" accept="image/*" capture="environment" onChange={handleFile} disabled={analyzing} style={{ display: 'none' }} />
          </label>
        </div>
      </div>

      <input className="input" placeholder="Item name (required)" value={name} onChange={e => setName(e.target.value)} autoFocus />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <select className="input" value={category} onChange={e => setCategory(e.target.value)}>
          {SHARED_CATEGORIES.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
        </select>
        <input className="input" placeholder="Brand" value={brand} onChange={e => setBrand(e.target.value)} />
      </div>
      <input className="input" placeholder="Image URL (optional)" value={imageUrl} onChange={e => setImageUrl(e.target.value)} />
      <input className="input" placeholder="Notes (optional)" value={notes} onChange={e => setNotes(e.target.value)} />
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => onDone(null)}>Cancel</button>
        <button type="submit" className="btn btn-primary btn-sm" disabled={saving || !name.trim()}>
          {saving ? 'Adding…' : 'Add item'}
        </button>
      </div>
    </form>
  )
}


// ── Invite member form ────────────────────────────────────────────────────
function InviteMemberForm({ wardrobeId, existingIds, pendingIds = [], onDone }) {
  const [connections, setConnections] = useState([])
  const [loading, setLoading]         = useState(true)
  const [inviting, setInviting]       = useState(null)
  const [invited, setInvited]         = useState(() => new Set(pendingIds))

  useEffect(() => {
    social.connections.list('accepted').then(res => {
      setConnections(res.results || [])
    }).finally(() => setLoading(false))
  }, [])

  const invite = async (userId) => {
    setInviting(userId)
    try {
      await api.members.add(wardrobeId, userId)
      setInvited(prev => new Set([...prev, userId]))
      window.__toast?.('Invitation sent.', 'success')
    } catch (err) {
      window.__toast?.(err.response?.data?.error?.message || 'Could not invite.', 'error')
    } finally {
      setInviting(null)
    }
  }

  const available = connections.filter(c => !existingIds.includes(c.other_user?.id))

  return (
    <div style={{ background: 'var(--surface-2)', borderRadius: 8, padding: 12, marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div style={{ fontSize: '0.8rem', color: 'var(--cream)', fontWeight: 500 }}>Invite a connection</div>
        <button className="btn btn-ghost btn-icon btn-sm" onClick={onDone} title="Close">✕</button>
      </div>
      {loading ? (
        <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)' }}>Loading…</div>
      ) : available.length === 0 ? (
        <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)' }}>
          {connections.length === 0 ? 'You have no connections yet.' : 'All your connections are already members.'}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 240, overflowY: 'auto' }}>
          {available.map(c => (
            <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ flex: 1, fontSize: '0.8rem', color: 'var(--cream)' }}>
                {c.other_user?.display_name || '@' + c.other_user?.handle}
              </div>
              <button
                className={`btn btn-sm ${invited.has(c.other_user?.id) ? 'btn-ghost' : 'btn-primary'}`}
                onClick={() => invite(c.other_user?.id)}
                disabled={inviting === c.other_user?.id || invited.has(c.other_user?.id)}
              >
                {inviting === c.other_user?.id ? '…' : invited.has(c.other_user?.id) ? 'Invited' : 'Invite'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
