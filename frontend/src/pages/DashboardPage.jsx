// src/pages/DashboardPage.jsx
import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth.jsx'
import { agents, outfits, itinerary, weather as weatherApi } from '../api/index.js'

const FORMALITY_COLOR = {
  formal:       'badge-gold',
  smart:        'badge-sky',
  casual_smart: 'badge-terra',
  casual:       'badge-sage',
  activewear:   'badge-sage',
}

const EVENT_ICONS = {
  external_meeting: '💼',
  internal_meeting: '💬',
  workout:          '🏃',
  social:           '🍽',
  travel:           '✈',
  wedding:          '💍',
  interview:        '🎯',
  date:             '❤',
  free:             '☀',
  other:            '📌',
}

function WeatherCard({ data }) {
  if (!data) return (
    <div className="card skeleton" style={{ height: 120 }} />
  )
  const icon = data.is_raining ? '🌧' : data.is_cold ? '🧥' : data.is_hot ? '☀' : '⛅'
  return (
    <div className="card" style={{ background: 'var(--surface-2)' }}>
      <div className="card-label">Weather today</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <span style={{ fontSize: '2.5rem' }}>{icon}</span>
        <div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '2.25rem', lineHeight: 1, color: 'var(--cream)' }}>
            {data.temp_c}°C
          </div>
          <div style={{ fontSize: '0.875rem', color: 'var(--cream-dim)', marginTop: '4px' }}>
            {data.condition} · {data.precipitation_probability}% rain
          </div>
        </div>
        <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)' }}>H: {data.temp_max_c}° / L: {data.temp_min_c}°</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', marginTop: '4px' }}>💨 {data.wind_kmh} km/h</div>
        </div>
      </div>
    </div>
  )
}

function EventsCard({ events }) {
  const today = new Date().toISOString().split('T')[0]
  const todayEvents = events.filter(e => e.start_time?.startsWith(today))

  return (
    <div className="card">
      <div className="card-label">Today's schedule</div>
      {todayEvents.length === 0 ? (
        <div style={{ color: 'var(--cream-dim)', fontSize: '0.875rem', padding: '8px 0' }}>
          Nothing scheduled — free day ☀
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {todayEvents.map(ev => (
            <div key={ev.id} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '1.1rem', width: '24px', textAlign: 'center' }}>
                {EVENT_ICONS[ev.event_type] || '📌'}
              </span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '0.875rem', color: 'var(--cream)' }}>{ev.title}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)' }}>
                  {new Date(ev.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  {ev.location ? ` · ${ev.location}` : ''}
                </div>
              </div>
              {ev.formality && (
                <span className={`badge ${FORMALITY_COLOR[ev.formality] || 'badge-sky'}`}>
                  {ev.formality.replace('_', ' ')}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function OutfitCard({ recommendation, onAccept, onReject, onGenerate, generating }) {
  if (!recommendation) return (
    <div className="card" style={{ textAlign: 'center', padding: '40px 24px' }}>
      <div style={{ fontSize: '3rem', marginBottom: '16px' }}>👗</div>
      <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: 'var(--cream)', marginBottom: '8px' }}>
        No outfit yet
      </div>
      <p style={{ color: 'var(--cream-dim)', fontSize: '0.875rem', marginBottom: '24px' }}>
        Generate your daily look based on today's calendar and weather.
      </p>
      <button
        className="btn btn-primary"
        onClick={onGenerate}
        disabled={generating}
      >
        {generating
          ? <><span className="spinner" style={{ width: 16, height: 16 }} /> Generating…</>
          : '✦ Generate Today\'s Look'
        }
      </button>
    </div>
  )

  const items = recommendation.outfit_items || []
  const accepted = recommendation.accepted

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
        <div className="card-label">Today's outfit</div>
        {accepted === true && <span className="badge badge-sage">✓ Accepted</span>}
        {accepted === false && <span className="badge" style={{ background: 'rgba(220,70,60,0.1)', color: '#f87171' }}>✗ Rejected</span>}
      </div>

      {recommendation.notes && (
        <p style={{ fontSize: '0.9375rem', color: 'var(--cream-dim)', marginBottom: '20px', lineHeight: 1.5, fontStyle: 'italic' }}>
          "{recommendation.notes}"
        </p>
      )}

      {items.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '20px' }}>
          {items.map((oi, i) => (
            <div key={i} style={{
              background: 'var(--surface-2)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              padding: '8px 14px',
              fontSize: '0.8rem',
              color: 'var(--cream)',
            }}>
              <span style={{ color: 'var(--cream-dim)', marginRight: '6px', textTransform: 'capitalize' }}>{oi.role}</span>
              Item #{oi.clothing_item}
            </div>
          ))}
        </div>
      )}

      {recommendation.weather_snapshot?.temp_c && (
        <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', marginBottom: '20px' }}>
          ⛅ {recommendation.weather_snapshot.condition} · {recommendation.weather_snapshot.temp_c}°C
        </div>
      )}

      {accepted === null || accepted === undefined ? (
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-secondary" style={{ flex: 1 }} onClick={onReject}>
            ✕ Skip
          </button>
          <button className="btn btn-primary" style={{ flex: 1 }} onClick={onAccept}>
            ✓ Wearing this
          </button>
        </div>
      ) : (
        <button className="btn btn-ghost btn-sm" onClick={onGenerate} disabled={generating}>
          {generating ? 'Regenerating…' : '↻ Regenerate'}
        </button>
      )}
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [wx,           setWx]           = useState(null)
  const [events,       setEvents]       = useState([])
  const [rec,          setRec]          = useState(null)
  const [generating,   setGenerating]   = useState(false)
  const [error,        setError]        = useState('')
  const [loadingRec,   setLoadingRec]   = useState(true)

  const today = new Date()
  const dateStr = today.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

  // Load today's events
  useEffect(() => {
    const date = new Date().toISOString().split('T')[0]
    itinerary.events.list({ date }).then(d => setEvents(d?.results || [])).catch(() => {})
  }, [])

  // Load weather (Zurich as default if no location)
  useEffect(() => {
    weatherApi.byLocation('Zurich').then(setWx).catch(() => {})
  }, [])

  // Load today's recommendation
  useEffect(() => {
    outfits.daily().then(setRec).catch(() => {}).finally(() => setLoadingRec(false))
  }, [])

  const generate = async () => {
    setGenerating(true)
    setError('')
    try {
      const result = await agents.dailyLook({ location: 'Zurich' })
      if (result.status === 'completed') {
        // Re-fetch the persisted recommendation
        const fresh = await outfits.daily()
        setRec(fresh)
      } else {
        setError(result.error || 'Generation failed')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  const handleFeedback = async (accepted) => {
    if (!rec?.id) return
    try {
      const updated = await outfits.feedback(rec.id, accepted)
      setRec(r => ({ ...r, accepted: updated.accepted }))
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <div className="page-header fade-up">
        <div className="date-line">{dateStr}</div>
        <h1>
          {user?.first_name ? `Good morning, ${user.first_name}.` : 'Good morning.'}
        </h1>
        <p>Here's what to wear today.</p>
      </div>

      {error && (
        <div className="alert alert-error fade-up" style={{ marginBottom: '24px' }}>
          ⚠ {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }} className="fade-up fade-up-delay-1">
        <WeatherCard data={wx} />
        <EventsCard events={events} />
      </div>

      <div className="fade-up fade-up-delay-2">
        {loadingRec
          ? <div className="card skeleton" style={{ height: 200 }} />
          : (
            <OutfitCard
              recommendation={rec}
              onGenerate={generate}
              onAccept={() => handleFeedback(true)}
              onReject={() => handleFeedback(false)}
              generating={generating}
            />
          )
        }
      </div>

      {/* Quick actions */}
      <div className="grid-3 fade-up fade-up-delay-3" style={{ marginTop: '24px' }}>
        {[
          { icon: '👔', label: 'Add wardrobe item', href: '/wardrobe' },
          { icon: '✈',  label: 'Plan a trip',       href: '/trips' },
          { icon: '🌍', label: 'Cultural guide',     href: '/cultural' },
        ].map(({ icon, label, href }) => (
          <a key={href} href={href} className="card" style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', textDecoration: 'none' }}>
            <span style={{ fontSize: '1.5rem' }}>{icon}</span>
            <span style={{ fontSize: '0.875rem', color: 'var(--cream)' }}>{label}</span>
            <span style={{ marginLeft: 'auto', color: 'var(--cream-dim)' }}>→</span>
          </a>
        ))}
      </div>
    </div>
  )
}
