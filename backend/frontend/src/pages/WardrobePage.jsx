// src/pages/WardrobePage.jsx
import { useState, useEffect, useCallback } from 'react'
import { wardrobe as wardrobeApi } from '../api/index.js'

const CATEGORIES = ['', 'top', 'bottom', 'dress', 'outerwear', 'footwear', 'accessory', 'activewear', 'formal', 'other']
const FORMALITIES = ['', 'casual', 'casual_smart', 'smart', 'formal', 'activewear']
const SEASONS     = ['', 'spring', 'summer', 'autumn', 'winter', 'all']

const CAT_ICONS = {
  top: '👕', bottom: '👖', dress: '👗', outerwear: '🧥',
  footwear: '👟', accessory: '💍', activewear: '🏃', formal: '🤵', other: '📦',
}
const CAT_COLORS = {
  top: 'badge-terra', bottom: 'badge-sky', dress: 'badge-gold',
  outerwear: 'badge-sage', footwear: 'badge-terra', activewear: 'badge-sage',
  formal: 'badge-gold', accessory: 'badge-sky', other: '',
}

function WardrobeItemCard({ item, onDelete }) {
  const [deleting, setDeleting] = useState(false)

  const handleDelete = async () => {
    if (!confirm(`Remove "${item.name}" from your wardrobe?`)) return
    setDeleting(true)
    try { await onDelete(item.id) } finally { setDeleting(false) }
  }

  return (
    <div className="card" style={{ position: 'relative', transition: 'all 0.2s', opacity: deleting ? 0.4 : 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
        <span style={{ fontSize: '2rem' }}>{CAT_ICONS[item.category] || '📦'}</span>
        <button
          onClick={handleDelete}
          className="btn btn-ghost btn-icon btn-sm"
          style={{ fontSize: '0.75rem', color: 'var(--cream-dim)' }}
          disabled={deleting}
        >
          ✕
        </button>
      </div>

      <div style={{ fontWeight: 500, color: 'var(--cream)', fontSize: '0.9375rem', marginBottom: '6px' }}>
        {item.name}
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' }}>
        <span className={`badge ${CAT_COLORS[item.category] || 'badge-sky'}`}>
          {item.category}
        </span>
        {item.formality && (
          <span className="badge" style={{ background: 'var(--surface-3)', color: 'var(--cream-dim)' }}>
            {item.formality.replace('_', ' ')}
          </span>
        )}
        {item.season && item.season !== 'all' && (
          <span className="badge" style={{ background: 'var(--surface-3)', color: 'var(--cream-dim)' }}>
            {item.season}
          </span>
        )}
      </div>

      {item.brand && (
        <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)' }}>{item.brand}</div>
      )}
      {item.colors?.length > 0 && (
        <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', marginTop: '4px' }}>
          {item.colors.join(', ')}
        </div>
      )}

      <div style={{
        marginTop: '12px',
        paddingTop: '12px',
        borderTop: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '0.7rem',
        color: 'var(--cream-dim)',
      }}>
        <span>Worn {item.times_worn}×</span>
        {item.weight_grams && <span>{item.weight_grams}g</span>}
      </div>
    </div>
  )
}

function AddItemModal({ onClose, onAdd }) {
  const [form, setForm] = useState({
    name: '', category: 'top', formality: 'casual', season: 'all',
    colors: '', brand: '', material: '', weight_grams: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const payload = {
        ...form,
        colors: form.colors ? form.colors.split(',').map(c => c.trim()).filter(Boolean) : [],
        weight_grams: form.weight_grams ? parseInt(form.weight_grams) : null,
      }
      const item = await wardrobeApi.create(payload)
      onAdd(item)
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '20px',
    }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="card fade-up" style={{ width: '100%', maxWidth: '480px', maxHeight: '90vh', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: 'var(--cream)' }}>
            Add wardrobe item
          </h3>
          <button className="btn btn-ghost btn-icon" onClick={onClose}>✕</button>
        </div>

        {error && <div className="alert alert-error" style={{ marginBottom: '16px' }}>⚠ {error}</div>}

        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div className="input-group">
            <label className="input-label">Name *</label>
            <input className="input" required value={form.name} onChange={e => set('name', e.target.value)} placeholder="e.g. Navy Blazer" />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div className="input-group">
              <label className="input-label">Category *</label>
              <select className="input" value={form.category} onChange={e => set('category', e.target.value)}>
                {CATEGORIES.filter(Boolean).map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="input-group">
              <label className="input-label">Formality</label>
              <select className="input" value={form.formality} onChange={e => set('formality', e.target.value)}>
                {FORMALITIES.filter(Boolean).map(f => <option key={f} value={f}>{f.replace('_', ' ')}</option>)}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div className="input-group">
              <label className="input-label">Season</label>
              <select className="input" value={form.season} onChange={e => set('season', e.target.value)}>
                {SEASONS.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="input-group">
              <label className="input-label">Weight (grams)</label>
              <input className="input" type="number" min="0" value={form.weight_grams} onChange={e => set('weight_grams', e.target.value)} placeholder="e.g. 400" />
            </div>
          </div>

          <div className="input-group">
            <label className="input-label">Colors <span style={{ color: 'var(--cream-dim)', fontWeight: 400 }}>(comma separated)</span></label>
            <input className="input" value={form.colors} onChange={e => set('colors', e.target.value)} placeholder="e.g. navy, white" />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div className="input-group">
              <label className="input-label">Brand</label>
              <input className="input" value={form.brand} onChange={e => set('brand', e.target.value)} placeholder="e.g. Zara" />
            </div>
            <div className="input-group">
              <label className="input-label">Material</label>
              <input className="input" value={form.material} onChange={e => set('material', e.target.value)} placeholder="e.g. cotton" />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', marginTop: '8px' }}>
            <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" style={{ flex: 1 }} disabled={loading}>
              {loading ? 'Adding…' : 'Add item'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function WardrobePage() {
  const [items,    setItems]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [showAdd,  setShowAdd]  = useState(false)
  const [filters,  setFilters]  = useState({ category: '', formality: '', season: '', q: '' })

  const loadItems = useCallback(async () => {
    setLoading(true)
    try {
      const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v))
      params.page      = page
      params.page_size = PAGE_SIZE
      const data   = await wardrobeApi.list(params)
      setItems(data?.results || [])
      setHasNext(!!data?.next)
      setHasPrev(!!data?.previous)
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [filters, page])

  useEffect(() => { loadItems() }, [loadItems])

  const handleDelete = async (id) => {
    await wardrobeApi.delete(id)
    setItems(prev => prev.filter(i => i.id !== id))
  }

  const setFilter = (key, val) => { setPage(1); setFilters(f => ({ ...f, [key]: val })) }

  return (
    <div>
      <div className="page-header fade-up">
        <div className="date-line">My Wardrobe</div>
        <h1>Digital Closet</h1>
        <p>{items.length} item{items.length !== 1 ? 's' : ''} in your wardrobe</p>
      </div>

      {/* Filters + Add */}
      <div className="fade-up fade-up-delay-1" style={{ display: 'flex', gap: '10px', marginBottom: '24px', flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          className="input"
          placeholder="Search name, brand, material…"
          value={filters.q}
          onChange={e => setFilter('q', e.target.value)}
          style={{ maxWidth: '220px' }}
        />
        <select className="input" value={filters.category} onChange={e => setFilter('category', e.target.value)} style={{ maxWidth: '140px' }}>
          <option value="">All categories</option>
          {CATEGORIES.filter(Boolean).map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select className="input" value={filters.formality} onChange={e => setFilter('formality', e.target.value)} style={{ maxWidth: '140px' }}>
          <option value="">All formality</option>
          {FORMALITIES.filter(Boolean).map(f => <option key={f} value={f}>{f.replace('_', ' ')}</option>)}
        </select>
        <select className="input" value={filters.season} onChange={e => setFilter('season', e.target.value)} style={{ maxWidth: '120px' }}>
          <option value="">All seasons</option>
          {SEASONS.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <button className="btn btn-primary" style={{ marginLeft: 'auto' }} onClick={() => setShowAdd(true)}>
          + Add item
        </button>
      </div>

      {/* Items grid */}
      {loading ? (
        <div className="grid-auto">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 180, borderRadius: 'var(--radius-lg)' }} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state card fade-up">
          <div className="empty-icon">👗</div>
          <div className="empty-title">Your wardrobe is empty</div>
          <div className="empty-body">Add your first item to start getting outfit recommendations.</div>
          <button className="btn btn-primary" onClick={() => setShowAdd(true)}>+ Add first item</button>
        </div>
      ) : (
        <div className="grid-auto fade-up fade-up-delay-2">
          {items.map(item => (
            <WardrobeItemCard key={item.id} item={item} onDelete={handleDelete} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {(hasNext || hasPrev) && (
        <div style={{ display:'flex', justifyContent:'center', alignItems:'center', gap:16, marginTop:32 }}>
          <button
            className="btn btn-secondary btn-sm"
            disabled={!hasPrev}
            onClick={() => setPage(p => p - 1)}
          >
            ← Previous
          </button>
          <span style={{ fontSize:'0.8rem', color:'var(--cream-dim)' }}>Page {page}</span>
          <button
            className="btn btn-secondary btn-sm"
            disabled={!hasNext}
            onClick={() => setPage(p => p + 1)}
          >
            Next →
          </button>
        </div>
      )}

      {showAdd && (
        <AddItemModal
          onClose={() => setShowAdd(false)}
          onAdd={item => setItems(prev => [item, ...prev])}
        />
      )}
    </div>
  )
}
