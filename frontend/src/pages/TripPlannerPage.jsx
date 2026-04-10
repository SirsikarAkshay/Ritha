// src/pages/TripPlannerPage.jsx
import { useState, useEffect } from 'react'
import { itinerary as itineraryApi, agents } from '../api/index.js'

export default function TripPlannerPage() {
  const [trips,    setTrips]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [showNew,  setShowNew]  = useState(false)
  const [planning, setPlanning] = useState(null)  // trip id being planned
  const [plan,     setPlan]     = useState(null)  // { trip_id, output }
  const [recommending, setRecommending] = useState(null) // trip id being recommended
  const [recs,     setRecs]     = useState(null)  // { trip_id, output }
  const [error,    setError]    = useState('')

  const [form, setForm] = useState({
    name: '', destination: '', start_date: '', end_date: '', activities: '',
  })

  useEffect(() => {
    itineraryApi.trips.list()
      .then(d => setTrips(d?.results || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const createTrip = async (e) => {
    e.preventDefault()
    try {
      const trip = await itineraryApi.trips.create({
        name: form.name,
        destination: form.destination,
        start_date: form.start_date,
        end_date: form.end_date,
        notes: form.activities,
      })
      setTrips(prev => [trip, ...prev])
      setForm({ name: '', destination: '', start_date: '', end_date: '', activities: '' })
      setShowNew(false)
    } catch (err) {
      setError(err.message)
    }
  }

  const planOutfits = async (trip) => {
    setPlanning(trip.id)
    setError('')
    try {
      const result = await agents.outfitPlanner({ trip_id: trip.id })
      if (result.status === 'completed') {
        setPlan({ trip_id: trip.id, output: result.output })
      } else {
        setError(result.error || 'Planning failed')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setPlanning(null)
    }
  }

  const getRecommendations = async (trip) => {
    setRecommending(trip.id)
    setError('')
    try {
      const result = await agents.smartRecommend({
        destination: trip.destination,
        date: trip.start_date,
        occasion: 'travel',
      })
      const output = result?.output || result
      setRecs({ trip_id: trip.id, output })
    } catch (err) {
      const msg = err.response?.data?.error?.message || err.response?.data?.error || err.message || 'Recommendation failed.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setRecommending(null)
    }
  }

  const deleteTrip = async (id) => {
    if (!confirm('Delete this trip?')) return
    await itineraryApi.trips.delete(id)
    setTrips(prev => prev.filter(t => t.id !== id))
    if (plan?.trip_id === id) setPlan(null)
    if (recs?.trip_id === id) setRecs(null)
  }

  const daysUntil = (date) => {
    const d = Math.ceil((new Date(date) - new Date()) / 86400000)
    if (d < 0) return 'Past'
    if (d === 0) return 'Today'
    return `In ${d} day${d !== 1 ? 's' : ''}`
  }

  return (
    <div>
      <div className="page-header fade-up">
        <div className="date-line">Trip Planner</div>
        <h1>Your Travels</h1>
        <p>Plan outfits for every day of your trip.</p>
      </div>

      {error && <div className="alert alert-error fade-up" style={{ marginBottom: '20px' }}>⚠ {error}</div>}

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '24px' }} className="fade-up fade-up-delay-1">
        <button className="btn btn-primary" onClick={() => setShowNew(!showNew)}>
          {showNew ? '✕ Cancel' : '+ New Trip'}
        </button>
      </div>

      {showNew && (
        <div className="card fade-up" style={{ marginBottom: '24px' }}>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.125rem', color: 'var(--cream)', marginBottom: '20px' }}>
            Plan a new trip
          </h3>
          <form onSubmit={createTrip} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div className="input-group" style={{ gridColumn: 'span 2' }}>
              <label className="input-label">Trip name *</label>
              <input className="input" required placeholder="e.g. Tokyo Adventure" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
            </div>
            <div className="input-group" style={{ gridColumn: 'span 2' }}>
              <label className="input-label">Destination *</label>
              <input className="input" required placeholder="e.g. Tokyo, Japan" value={form.destination} onChange={e => setForm(f => ({ ...f, destination: e.target.value }))} />
            </div>
            <div className="input-group">
              <label className="input-label">Departure *</label>
              <input className="input" type="date" required value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))} />
            </div>
            <div className="input-group">
              <label className="input-label">Return *</label>
              <input className="input" type="date" required value={form.end_date} onChange={e => setForm(f => ({ ...f, end_date: e.target.value }))} />
            </div>
            <div className="input-group" style={{ gridColumn: 'span 2' }}>
              <label className="input-label">Activities <span style={{ color: 'var(--cream-dim)', fontWeight: 400 }}>(optional)</span></label>
              <input className="input" placeholder="e.g. hiking, beach, business meetings" value={form.activities} onChange={e => setForm(f => ({ ...f, activities: e.target.value }))} />
            </div>
            <div style={{ gridColumn: 'span 2', display: 'flex', justifyContent: 'flex-end' }}>
              <button type="submit" className="btn btn-primary">Save trip</button>
            </div>
          </form>
        </div>
      )}

      {/* Trips list */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: 100, borderRadius: 'var(--radius-lg)' }} />)}
        </div>
      ) : trips.length === 0 ? (
        <div className="empty-state card fade-up">
          <div className="empty-icon">✈</div>
          <div className="empty-title">No trips planned</div>
          <div className="empty-body">Add a trip and let the AI plan your outfits day by day.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {trips.map(trip => {
            const days = Math.max(1, Math.ceil((new Date(trip.end_date) - new Date(trip.start_date)) / 86400000) + 1)
            const isPast = new Date(trip.end_date) < new Date()
            return (
              <div key={trip.id} className="card fade-up">
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
                  <span style={{ fontSize: '2rem', lineHeight: 1 }}>✈</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 500, color: 'var(--cream)', fontSize: '1rem' }}>{trip.name}</span>
                      {!isPast && (
                        <span className={`badge ${daysUntil(trip.start_date) === 'Today' ? 'badge-terra' : 'badge-sky'}`}>
                          {daysUntil(trip.start_date)}
                        </span>
                      )}
                      {isPast && <span className="badge" style={{ background: 'var(--surface-3)', color: 'var(--cream-dim)' }}>Past</span>}
                    </div>
                    <div style={{ fontSize: '0.875rem', color: 'var(--cream-dim)' }}>
                      📍 {trip.destination} · {days} day{days !== 1 ? 's' : ''} · {trip.start_date} → {trip.end_date}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => getRecommendations(trip)}
                      disabled={recommending === trip.id}
                    >
                      {recommending === trip.id
                        ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Recommending…</>
                        : '✧ Recommend clothes'
                      }
                    </button>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => planOutfits(trip)}
                      disabled={planning === trip.id}
                    >
                      {planning === trip.id
                        ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Planning…</>
                        : '✦ Plan outfits'
                      }
                    </button>
                    <button className="btn btn-ghost btn-icon btn-sm" onClick={() => deleteTrip(trip.id)}>✕</button>
                  </div>
                </div>

                {/* Day plan output */}
                {plan?.trip_id === trip.id && plan.output && (
                  <div style={{ marginTop: '20px', borderTop: '1px solid var(--border)', paddingTop: '20px' }}>
                    <div className="card-label" style={{ marginBottom: '12px' }}>
                      AI outfit plan · {plan.output.days} days · {plan.output.destination}
                    </div>
                    {plan.output.notes && (
                      <p style={{ fontSize: '0.875rem', color: 'var(--cream-dim)', marginBottom: '16px', fontStyle: 'italic' }}>
                        "{plan.output.notes}"
                      </p>
                    )}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {plan.output.day_plans?.map(day => (
                        <div key={day.day} style={{
                          display: 'flex', alignItems: 'center', gap: '12px',
                          padding: '10px 14px', background: 'var(--surface-2)',
                          borderRadius: 'var(--radius-md)', border: '1px solid var(--border)',
                        }}>
                          <span style={{ fontFamily: 'var(--font-display)', fontSize: '1.125rem', color: 'var(--terra)', minWidth: '32px' }}>
                            {day.day}
                          </span>
                          <span style={{ fontSize: '0.8rem', color: 'var(--cream-dim)' }}>{day.date}</span>
                          <span style={{ fontSize: '0.8rem', color: 'var(--cream)', flex: 1 }}>{day.notes}</span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--cream-dim)' }}>
                            {day.item_ids?.length || 0} items
                          </span>
                        </div>
                      ))}
                    </div>
                    {plan.output.estimated_weight_grams > 0 && (
                      <div style={{ marginTop: '12px', fontSize: '0.8rem', color: 'var(--sage)' }}>
                        Estimated bag weight: {(plan.output.estimated_weight_grams / 1000).toFixed(1)} kg
                      </div>
                    )}
                  </div>
                )}

                {/* Smart recommendations */}
                {recs?.trip_id === trip.id && recs.output && (
                  <TripRecommendations output={recs.output} onClose={() => setRecs(null)} />
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}


/* ── Trip Recommendations sub-component ───────────────────────────────── */

function TripRecommendations({ output, onClose }) {
  const weather = output.weather
  const cultural = output.cultural
  const matches = output.wardrobe_matches || []
  const shopping = output.shopping_suggestions || []
  const outfit = output.outfit || {}

  const weatherIcon = weather?.is_raining ? '\u{1F327}' : weather?.is_cold ? '\u{1F9E5}' : weather?.is_hot ? '\u2600' : '\u26C5'

  return (
    <div style={{ marginTop: '20px', borderTop: '1px solid var(--border)', paddingTop: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div className="card-label">AI Clothing Recommendations</div>
        <button className="btn btn-ghost btn-icon btn-sm" onClick={onClose} title="Close">✕</button>
      </div>

      {/* Weather + Cultural summary row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
        {weather && (
          <div style={{ padding: '12px', background: 'var(--surface-2)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span style={{ fontSize: '1.5rem' }}>{weatherIcon}</span>
              <span style={{ fontFamily: 'var(--font-display)', fontSize: '1.125rem', color: 'var(--cream)' }}>
                {weather.temp_c != null ? `${Math.round(weather.temp_c)}\u00b0C` : '?'}
              </span>
              <span style={{ fontSize: '0.8125rem', color: 'var(--cream-dim)' }}>{weather.condition}</span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', display: 'flex', gap: '12px' }}>
              {weather.precipitation_probability != null && <span>Rain: {weather.precipitation_probability}%</span>}
              {weather.wind_kmh != null && <span>Wind: {weather.wind_kmh} km/h</span>}
            </div>
          </div>
        )}
        {cultural?.overall_dress_code && (
          <div style={{ padding: '12px', background: 'var(--surface-2)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Local dress code
            </div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--cream)', lineHeight: 1.4 }}>
              {cultural.overall_dress_code}
            </div>
          </div>
        )}
      </div>

      {/* Cultural rules */}
      {cultural?.rules?.length > 0 && (
        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Cultural rules
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {cultural.rules.map((r, i) => (
              <span key={i} style={{
                fontSize: '0.75rem', padding: '4px 10px', borderRadius: '999px',
                background: r.severity === 'required' ? 'rgba(212,114,74,0.15)' : 'var(--surface-3)',
                color: r.severity === 'required' ? 'var(--terra-light)' : 'var(--cream-dim)',
                border: `1px solid ${r.severity === 'required' ? 'rgba(212,114,74,0.3)' : 'var(--border)'}`,
              }}>
                {r.description}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Outfit notes */}
      {outfit.notes && (
        <div style={{
          padding: '12px 14px', marginBottom: '16px', borderLeft: '3px solid var(--terra)',
          background: 'var(--surface-2)', borderRadius: 'var(--radius-md)',
          fontSize: '0.875rem', color: 'var(--cream)', lineHeight: 1.5,
        }}>
          {outfit.notes}
        </div>
      )}

      {/* Wardrobe matches */}
      {matches.length > 0 && (
        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            From your wardrobe
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '10px' }}>
            {matches.map((m, i) => (
              <div key={i} style={{
                padding: '12px', background: 'var(--surface-2)', borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border)',
              }}>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '0.875rem', color: 'var(--cream)', marginBottom: '4px' }}>
                  {m.item.name}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', marginBottom: '6px' }}>
                  {m.item.category} / {m.item.formality}
                </div>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <span className="badge badge-sage" style={{ fontSize: '0.65rem' }}>{m.role}</span>
                  <span className="badge badge-terra" style={{ fontSize: '0.65rem' }}>owned</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Shopping suggestions */}
      {shopping.length > 0 && (
        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {matches.length > 0 ? 'You might also need' : 'Recommended products'}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '10px' }}>
            {shopping.map((s, i) => (
              <div key={i} style={{
                padding: '12px', background: 'var(--surface-2)', borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border)', borderLeft: '3px solid #e0a458',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                  <span style={{ fontFamily: 'var(--font-display)', fontSize: '0.875rem', color: 'var(--cream)' }}>
                    {s.name || s.description}
                  </span>
                  {s.price_range && (
                    <span style={{ fontSize: '0.7rem', color: 'var(--terra-light)', whiteSpace: 'nowrap', marginLeft: '6px' }}>
                      {s.price_range}
                    </span>
                  )}
                </div>
                {s.brand && (
                  <div style={{ fontSize: '0.7rem', color: 'var(--cream-dim)', marginBottom: '4px' }}>{s.brand}</div>
                )}
                {s.description && s.name && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', marginBottom: '8px', lineHeight: 1.3 }}>
                    {s.description}
                  </div>
                )}
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {s.links?.google_shopping && (
                    <a href={s.links.google_shopping} target="_blank" rel="noreferrer"
                      style={{ fontSize: '0.7rem', color: 'var(--terra-light)', textDecoration: 'underline' }}>
                      Google
                    </a>
                  )}
                  {s.links?.amazon && (
                    <a href={s.links.amazon} target="_blank" rel="noreferrer"
                      style={{ fontSize: '0.7rem', color: 'var(--terra-light)', textDecoration: 'underline' }}>
                      Amazon
                    </a>
                  )}
                  {s.links?.asos && (
                    <a href={s.links.asos} target="_blank" rel="noreferrer"
                      style={{ fontSize: '0.7rem', color: 'var(--terra-light)', textDecoration: 'underline' }}>
                      ASOS
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Highlights */}
      {cultural?.highlights?.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Places to visit & what to wear
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '10px' }}>
            {cultural.highlights.map((h, i) => (
              <div key={i} style={{
                padding: '10px 12px', background: 'var(--surface-2)', borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border)',
              }}>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '0.8125rem', color: 'var(--cream)', marginBottom: '4px' }}>
                  {h.name}
                </div>
                {h.clothing_tip && (
                  <div style={{ fontSize: '0.7rem', color: 'var(--terra-light)' }}>
                    {h.clothing_tip}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
