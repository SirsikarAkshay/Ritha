import { useState } from 'react'
import { agents } from '../api/index.js'

// Preset bag sizes (mirrors PackingListInputSerializer.BAG_TYPE_LITERS on the backend).
const BAG_PRESETS = [
  { key: 'personal_item', label: 'Personal item', liters: 20 },
  { key: 'backpack',      label: 'Backpack',       liters: 30 },
  { key: 'carry_on',      label: 'Carry-on',       liters: 40 },
  { key: 'checked',       label: 'Checked',        liters: 70 },
]

function gaugeColor(util) {
  if (util == null) return 'var(--terra)'
  if (util > 100) return '#c0392b'   // over capacity
  if (util >= 90) return '#e08a1e'   // nearly full
  return 'var(--terra)'
}

/**
 * Bag-capacity-aware packing: pick the most versatile capsule from the user's
 * wardrobe that fits a chosen bag volume, and show what got left behind.
 */
export default function PackingByBag() {
  const [days, setDays]         = useState(7)
  const [liters, setLiters]     = useState(30)
  const [location, setLocation] = useState('')
  const [activities, setActs]   = useState('')
  const [loading, setLoading]   = useState(false)
  const [result, setResult]     = useState(null)
  const [error, setError]       = useState('')

  const pack = async () => {
    setLoading(true); setError(''); setResult(null)
    try {
      const payload = { days: Number(days) || 1 }
      if (Number(liters) > 0) payload.bag_capacity_liters = Number(liters)
      if (location.trim()) payload.location = location.trim()
      const acts = activities.split(',').map(s => s.trim()).filter(Boolean)
      if (acts.length) payload.activities = acts

      const res = await agents.packingList(payload)
      const out = res?.output || res
      if (out?.status === 'no_wardrobe') {
        setError(out.message || 'Add items to your wardrobe first.')
        return
      }
      setResult(out)
    } catch (err) {
      const msg = err.response?.data?.error?.message || err.response?.data?.error || err.message || 'Packing failed.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setLoading(false)
    }
  }

  const util = result?.capacity_utilization_pct
  const fillPct = util == null ? 0 : Math.min(100, util)

  return (
    <div className="card fade-up" style={{ marginBottom: '24px' }}>
      <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.125rem', color: 'var(--cream)', marginBottom: '6px' }}>
        🎒 Pack for a bag size
      </h3>
      <p style={{ color: 'var(--cream-dim)', fontSize: '0.9rem', marginBottom: '18px' }}>
        Tell us your trip length and bag — we’ll fit the most versatile capsule from your wardrobe and flag what won’t fit.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
        <div className="input-group">
          <label className="input-label">Trip length (days)</label>
          <input className="input" type="number" min="1" max="30" value={days}
                 onChange={e => setDays(e.target.value)} />
        </div>
        <div className="input-group">
          <label className="input-label">Bag capacity (liters)</label>
          <input className="input" type="number" min="5" max="200" value={liters}
                 onChange={e => setLiters(e.target.value)} />
        </div>
        <div className="input-group" style={{ gridColumn: 'span 2' }}>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {BAG_PRESETS.map(p => (
              <button
                key={p.key}
                type="button"
                onClick={() => setLiters(p.liters)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '999px',
                  border: '1px solid var(--terra)',
                  cursor: 'pointer',
                  fontSize: '0.8rem',
                  background: Number(liters) === p.liters ? 'var(--terra)' : 'transparent',
                  color: Number(liters) === p.liters ? 'var(--cream)' : 'var(--cream-dim)',
                }}
              >
                {p.label} · {p.liters}L
              </button>
            ))}
          </div>
        </div>
        <div className="input-group">
          <label className="input-label">Destination (optional)</label>
          <input className="input" placeholder="e.g. Europe" value={location}
                 onChange={e => setLocation(e.target.value)} />
        </div>
        <div className="input-group">
          <label className="input-label">Activities (comma-separated)</label>
          <input className="input" placeholder="e.g. hiking, dinner" value={activities}
                 onChange={e => setActs(e.target.value)} />
        </div>
      </div>

      <div style={{ marginTop: '16px' }}>
        <button className="btn btn-primary" onClick={pack} disabled={loading}>
          {loading ? 'Packing…' : 'Pack my bag'}
        </button>
      </div>

      {error && <div className="alert alert-error" style={{ marginTop: '16px' }}>⚠ {error}</div>}

      {result && (
        <div style={{ marginTop: '22px' }}>
          <h4 style={{ fontFamily: 'var(--font-display)', color: 'var(--cream)', fontSize: '1.05rem', marginBottom: '12px' }}>
            {result.headline}
          </h4>

          {util != null && (
            <div style={{ marginBottom: '18px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', color: 'var(--cream-dim)', marginBottom: '6px' }}>
                <span>{result.estimated_volume_liters}L packed · {result.item_ids.length} items</span>
                <span style={{ color: gaugeColor(util) }}>{util}% of {result.bag_capacity_liters}L</span>
              </div>
              <div style={{ height: '10px', borderRadius: '999px', background: 'rgba(255,255,255,0.12)', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${fillPct}%`, background: gaugeColor(util), transition: 'width .4s ease' }} />
              </div>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '8px' }}>
            {(result.packing_list || []).map(item => (
              <div key={item.id} style={{
                border: '1px solid rgba(255,255,255,0.1)', borderRadius: '10px', padding: '10px 12px',
              }}>
                <div style={{ color: 'var(--cream)', fontSize: '0.9rem' }}>{item.name}</div>
                <div style={{ color: 'var(--cream-dim)', fontSize: '0.75rem', marginTop: '2px' }}>
                  {item.category} · {item.packed_volume_liters}L
                </div>
              </div>
            ))}
          </div>

          {result.left_behind && result.left_behind.length > 0 && (
            <div style={{ marginTop: '16px' }}>
              <div style={{ color: '#e08a1e', fontSize: '0.85rem', marginBottom: '8px' }}>
                Left behind (won’t fit): {result.left_behind.length}
              </div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {result.left_behind.map(item => (
                  <span key={item.id} style={{
                    fontSize: '0.75rem', color: 'var(--cream-dim)', padding: '4px 10px',
                    border: '1px dashed rgba(255,255,255,0.2)', borderRadius: '999px',
                  }}>
                    {item.name} · {item.packed_volume_liters}L
                  </span>
                ))}
              </div>
            </div>
          )}

          {result.notes && (
            <p style={{ color: 'var(--cream-dim)', fontSize: '0.8rem', marginTop: '16px' }}>{result.notes}</p>
          )}
        </div>
      )}
    </div>
  )
}
