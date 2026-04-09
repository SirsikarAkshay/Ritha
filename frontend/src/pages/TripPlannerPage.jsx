// src/pages/TripPlannerPage.jsx
import { useState, useEffect } from 'react'
import { itinerary as itineraryApi, agents } from '../api/index.js'

export default function TripPlannerPage() {
  const [trips,    setTrips]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [showNew,  setShowNew]  = useState(false)
  const [planning, setPlanning] = useState(null)  // trip id being planned
  const [plan,     setPlan]     = useState(null)  // { trip_id, output }
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

  const deleteTrip = async (id) => {
    if (!confirm('Delete this trip?')) return
    await itineraryApi.trips.delete(id)
    setTrips(prev => prev.filter(t => t.id !== id))
    if (plan?.trip_id === id) setPlan(null)
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
                        🌱 Estimated bag weight: {(plan.output.estimated_weight_grams / 1000).toFixed(1)} kg
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
