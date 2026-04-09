// src/pages/SustainabilityPage.jsx
import { useState, useEffect } from 'react'
import { sustainability, wardrobe as wardrobeApi } from '../api/index.js'

const ACTION_ICONS = {
  wear_again:    '🔄',
  carry_on_only: '🧳',
  weight_saved:  '⚖',
  rental:        '♻',
  secondhand:    '🛍',
}

const ACTION_LABELS = {
  wear_again:    'Re-wore an item',
  carry_on_only: 'Carry-on only',
  weight_saved:  'Reduced luggage',
  rental:        'Chose rental',
  secondhand:    'Bought secondhand',
}

export default function SustainabilityPage() {
  const [profile,  setProfile]  = useState(null)
  const [logs,     setLogs]     = useState([])
  const [loading,  setLoading]  = useState(true)
  const [items,    setItems]    = useState([])
  const [selected, setSelected] = useState([])
  const [airline,  setAirline]  = useState('default')
  const [weightResult, setWeightResult] = useState(null)
  const [calculating,  setCalculating]  = useState(false)
  const [error,    setError]    = useState('')

  useEffect(() => {
    Promise.all([
      sustainability.tracker().then(setProfile),
      sustainability.logs().then(d => setLogs(d?.results || [])),
      wardrobeApi.list({ season: 'all' }).then(d => setItems(d?.results || [])),
    ]).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const toggleItem = (id) => {
    setSelected(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id])
  }

  const calcWeight = async () => {
    if (selected.length === 0) return
    setCalculating(true)
    setError('')
    try {
      const result = await wardrobeApi.luggageWeight(selected, airline)
      setWeightResult(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setCalculating(false)
    }
  }

  if (loading) return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '40px' }}>
      {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 80, borderRadius: 'var(--radius-lg)' }} />)}
    </div>
  )

  const co2 = parseFloat(profile?.total_co2_saved_kg || 0).toFixed(2)
  const pts = profile?.total_points || 0

  // Streak level
  const level = pts < 50 ? 'Seedling 🌱' : pts < 200 ? 'Sapling 🌿' : pts < 500 ? 'Tree 🌳' : 'Forest 🌲'

  return (
    <div>
      <div className="page-header fade-up">
        <div className="date-line">Sustainability</div>
        <h1>Your Impact</h1>
        <p>Track CO₂ saved, wear-again streaks, and luggage weight.</p>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: '20px' }}>⚠ {error}</div>}

      {/* Stat pills */}
      <div className="grid-3 fade-up fade-up-delay-1" style={{ marginBottom: '24px' }}>
        <div className="stat-pill">
          <div className="stat-value">{co2}<span style={{ fontSize: '1rem', color: 'var(--cream-dim)' }}>kg</span></div>
          <div className="stat-label">CO₂ saved</div>
        </div>
        <div className="stat-pill">
          <div className="stat-value">{pts}</div>
          <div className="stat-label">Eco points</div>
        </div>
        <div className="stat-pill">
          <div className="stat-value">{level.split(' ')[0]}<span style={{ fontSize: '1.25rem', marginLeft: '4px' }}>{level.split(' ')[1]}</span></div>
          <div className="stat-label">Your level</div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="card fade-up fade-up-delay-2" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
          <div className="card-label">Level progress</div>
          <span style={{ fontSize: '0.8rem', color: 'var(--sage)' }}>{level}</span>
        </div>
        <div style={{ height: '6px', background: 'var(--surface-3)', borderRadius: '3px', overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: `${Math.min(100, (pts % 200) / 2)}%`,
            background: 'linear-gradient(90deg, var(--sage), var(--terra))',
            borderRadius: '3px',
            transition: 'width 1s cubic-bezier(0.16,1,0.3,1)',
          }} />
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', marginTop: '8px' }}>
          Each accepted outfit earns 10 points per item worn again.
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }} className="fade-up fade-up-delay-3">
        {/* Luggage weight calculator */}
        <div className="card">
          <div className="card-label" style={{ marginBottom: '16px' }}>Luggage weight calculator</div>
          <div className="input-group" style={{ marginBottom: '14px' }}>
            <label className="input-label">Airline</label>
            <select className="input" value={airline} onChange={e => setAirline(e.target.value)}>
              {['default','easyjet','ryanair','swiss','lufthansa','ba'].map(a => (
                <option key={a} value={a}>{a === 'default' ? 'Generic (10 kg)' : a.charAt(0).toUpperCase() + a.slice(1)}</option>
              ))}
            </select>
          </div>

          <div style={{ fontSize: '0.8rem', color: 'var(--cream-dim)', marginBottom: '10px' }}>
            Select items to include:
          </div>
          <div style={{ maxHeight: '200px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '14px' }}>
            {items.map(item => (
              <label key={item.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', padding: '6px 8px', borderRadius: 'var(--radius-sm)', background: selected.includes(item.id) ? 'var(--sage-dim)' : 'transparent' }}>
                <input type="checkbox" checked={selected.includes(item.id)} onChange={() => toggleItem(item.id)} style={{ accentColor: 'var(--sage)' }} />
                <span style={{ fontSize: '0.8rem', color: 'var(--cream)', flex: 1 }}>{item.name}</span>
                <span style={{ fontSize: '0.7rem', color: 'var(--cream-dim)' }}>{item.weight_grams || '?'}g</span>
              </label>
            ))}
            {items.length === 0 && <span style={{ fontSize: '0.8rem', color: 'var(--cream-dim)' }}>Add wardrobe items first</span>}
          </div>

          <button className="btn btn-secondary" style={{ width: '100%' }} onClick={calcWeight} disabled={calculating || selected.length === 0}>
            {calculating ? 'Calculating…' : `⚖ Calculate (${selected.length} items)`}
          </button>

          {weightResult && (
            <div style={{ marginTop: '14px', padding: '14px', background: 'var(--surface-2)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--cream-dim)' }}>Total weight</span>
                <span style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: 'var(--cream)' }}>
                  {weightResult.total_kg} kg
                </span>
              </div>
              <div style={{ fontSize: '0.8rem', color: weightResult.fits_carry_on ? 'var(--sage)' : 'var(--terra)', marginBottom: '8px' }}>
                {weightResult.fits_carry_on ? '✓ Fits carry-on' : '✗ Over carry-on limit'}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', lineHeight: 1.4 }}>
                🌱 CO₂ saved vs. checked bag: {weightResult.co2_saved_vs_checked_kg} kg
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', marginTop: '6px', fontStyle: 'italic' }}>
                {weightResult.tip}
              </div>
            </div>
          )}
        </div>

        {/* Activity log */}
        <div className="card">
          <div className="card-label" style={{ marginBottom: '16px' }}>Recent activity</div>
          {logs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '24px 0' }}>
              <div style={{ fontSize: '2rem', marginBottom: '8px' }}>🌱</div>
              <p style={{ fontSize: '0.875rem', color: 'var(--cream-dim)' }}>
                Accept outfit recommendations to earn eco points.
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '360px', overflowY: 'auto' }}>
              {logs.map(log => (
                <div key={log.id} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                  <span style={{ fontSize: '1.1rem' }}>{ACTION_ICONS[log.action] || '✦'}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--cream)' }}>{ACTION_LABELS[log.action] || log.action}</div>
                    {log.notes && <div style={{ fontSize: '0.7rem', color: 'var(--cream-dim)' }}>{log.notes}</div>}
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--sage)', fontWeight: 500 }}>+{log.points}</div>
                    <div style={{ fontSize: '0.65rem', color: 'var(--cream-dim)' }}>{parseFloat(log.co2_saved_kg).toFixed(3)} kg CO₂</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
