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
  external_meeting: '💼', internal_meeting: '💬', workout: '🏃',
  social: '🍽', travel: '✈', wedding: '💍', interview: '🎯',
  date: '❤', free: '☀', other: '📌',
}

const CAT_ICONS = {
  top: '👕', bottom: '👖', dress: '👗', outerwear: '🧥',
  footwear: '👟', accessory: '💍', activewear: '🏃', formal: '🤵', other: '📦',
}

function isoDate(d) {
  return d.toISOString().split('T')[0]
}

function shortDay(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-US', { weekday: 'short' })
}

function shortDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-US', { day: 'numeric', month: 'short' })
}

function WeatherMini({ data }) {
  if (!data) return null
  const icon = data.is_raining ? '🌧' : data.is_cold ? '🧥' : data.is_hot ? '☀' : '⛅'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: '0.8rem', color: 'var(--cream-dim)' }}>
      <span style={{ fontSize: '1.4rem' }}>{icon}</span>
      <span style={{ fontWeight: 500, color: 'var(--cream)', fontSize: '1.1rem' }}>{data.temp_c}°C</span>
      <span>{data.condition}</span>
      <span>· {data.precipitation_probability ?? 0}% rain</span>
      <span style={{ marginLeft: 'auto' }}>H:{data.temp_max_c}° L:{data.temp_min_c}°</span>
    </div>
  )
}

function DayEvents({ events, date }) {
  const dayEvents = events.filter(e => e.start_time?.startsWith(date))
  if (dayEvents.length === 0) return (
    <div style={{ fontSize: '0.8rem', color: 'var(--cream-dim)', padding: '4px 0' }}>No events — free day ☀</div>
  )
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {dayEvents.map(ev => (
        <div key={ev.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.8rem' }}>
          <span>{EVENT_ICONS[ev.event_type] || '📌'}</span>
          <span style={{ color: 'var(--cream)', flex: 1 }}>{ev.title}</span>
          <span style={{ color: 'var(--cream-dim)' }}>
            {new Date(ev.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
          {ev.formality && (
            <span className={`badge ${FORMALITY_COLOR[ev.formality] || 'badge-sky'}`} style={{ fontSize: '0.6rem' }}>
              {ev.formality.replace('_', ' ')}
            </span>
          )}
        </div>
      ))}
    </div>
  )
}

function OutfitItems({ items }) {
  if (!items || items.length === 0) return null
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
      {items.map((oi, i) => (
        <div key={i} style={{
          display: 'flex', alignItems: 'center', gap: 6,
          background: oi.liked === true ? 'rgba(164,190,123,0.12)' :
                     oi.liked === false ? 'rgba(196,164,132,0.12)' : 'var(--surface-2)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-md)',
          padding: '8px 14px', fontSize: '0.8rem', color: 'var(--cream)',
        }}>
          <span>{CAT_ICONS[oi.item_category] || '📦'}</span>
          <div>
            <div style={{ fontWeight: 500 }}>{oi.item_name || `Item #${oi.clothing_item}`}</div>
            {oi.item_brand && <div style={{ fontSize: '0.65rem', color: 'var(--cream-dim)' }}>{oi.item_brand}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [weekDays, setWeekDays] = useState([])
  const [events, setEvents] = useState([])
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const today = new Date()
  const todayStr = isoDate(today)
  const dateStr = today.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

  const weekStart = todayStr
  const weekEnd = isoDate(new Date(today.getTime() + 6 * 86400000))

  useEffect(() => {
    Promise.all([
      outfits.weekly().catch(() => []),
      itinerary.events.list({ start_date: weekStart, end_date: weekEnd }).then(d => d?.results || []).catch(() => []),
    ]).then(([days, evts]) => {
      setWeekDays(Array.isArray(days) ? days : [])
      setEvents(evts)
    }).finally(() => setLoading(false))
  }, [])

  const generateWeek = async () => {
    setGenerating(true)
    setError('')
    try {
      const result = await agents.weeklyLooks({ location: 'Zurich' })
      if (result.status === 'completed' || result.output?.status === 'ok') {
        const fresh = await outfits.weekly()
        setWeekDays(Array.isArray(fresh) ? fresh : [])
      } else {
        setError(result.error || result.output?.message || 'Generation failed')
      }
    } catch (err) {
      setError(err.response?.data?.error?.message || err.message)
    } finally {
      setGenerating(false)
    }
  }

  const handleFeedback = async (recId, accepted) => {
    try {
      const updated = await outfits.feedback(recId, accepted)
      setWeekDays(prev => prev.map(d =>
        d.recommendation?.id === recId ? { ...d, recommendation: updated } : d
      ))
    } catch (err) {
      setError(err.message)
    }
  }

  const selectedDay = weekDays[selectedIdx] || null
  const selectedRec = selectedDay?.recommendation || null
  const hasAnyRec = weekDays.some(d => d.recommendation)

  return (
    <div>
      <div className="page-header fade-up">
        <div className="date-line">{dateStr}</div>
        <h1>{user?.first_name ? `Good morning, ${user.first_name}.` : 'Good morning.'}</h1>
        <p>Your weekly outfit plan — unique looks for every day.</p>
      </div>

      {error && <div className="alert alert-error fade-up" style={{ marginBottom: 20 }}>⚠ {error}</div>}

      {/* Day selector tabs */}
      <div className="fade-up fade-up-delay-1" style={{
        display: 'flex', gap: 6, marginBottom: 20, overflowX: 'auto', paddingBottom: 4,
      }}>
        {weekDays.map((day, idx) => {
          const isToday = day.date === todayStr
          const hasRec = !!day.recommendation
          const accepted = day.recommendation?.accepted
          return (
            <button
              key={day.date}
              onClick={() => setSelectedIdx(idx)}
              style={{
                minWidth: 72, padding: '10px 12px',
                borderRadius: 'var(--radius-md)',
                border: idx === selectedIdx ? '2px solid var(--terra)' : '1px solid var(--border)',
                background: idx === selectedIdx ? 'var(--surface-2)' : 'var(--surface-1)',
                cursor: 'pointer', textAlign: 'center',
                transition: 'all 0.15s',
              }}
            >
              <div style={{
                fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase',
                color: isToday ? 'var(--terra-light)' : 'var(--cream-dim)',
                letterSpacing: '0.04em',
              }}>
                {isToday ? 'Today' : shortDay(day.date)}
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--cream)', fontWeight: 500, marginTop: 2 }}>
                {shortDate(day.date)}
              </div>
              <div style={{ marginTop: 4, fontSize: '0.6rem' }}>
                {!hasRec ? '—' :
                 accepted === true ? <span style={{ color: 'var(--sage)' }}>✓</span> :
                 accepted === false ? <span style={{ color: '#f87171' }}>✗</span> :
                 <span style={{ color: 'var(--terra-light)' }}>●</span>}
              </div>
            </button>
          )
        })}
      </div>

      {/* Generate button */}
      {!loading && (
        <div className="fade-up fade-up-delay-1" style={{ marginBottom: 20, display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn btn-primary" onClick={generateWeek} disabled={generating}>
            {generating
              ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Generating week…</>
              : hasAnyRec ? '↻ Regenerate week' : '✦ Generate weekly looks'
            }
          </button>
        </div>
      )}

      {/* Selected day detail */}
      {loading ? (
        <div className="card skeleton fade-up" style={{ height: 260 }} />
      ) : !selectedDay ? (
        <div className="card fade-up" style={{ textAlign: 'center', padding: '40px 24px' }}>
          <div style={{ fontSize: '3rem', marginBottom: 16 }}>👗</div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: 'var(--cream)', marginBottom: 8 }}>
            No weekly plan yet
          </div>
          <p style={{ color: 'var(--cream-dim)', fontSize: '0.875rem' }}>
            Generate your weekly looks to get unique outfits for every day.
          </p>
        </div>
      ) : (
        <div className="card fade-up fade-up-delay-2" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div className="card-label">{selectedDay.day_label}'s outfit</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)' }}>{shortDate(selectedDay.date)}</div>
            </div>
            {selectedRec?.accepted === true && <span className="badge badge-sage">✓ Accepted</span>}
            {selectedRec?.accepted === false && <span className="badge" style={{ background: 'rgba(220,70,60,0.1)', color: '#f87171' }}>✗ Skipped</span>}
          </div>

          {/* Weather for this day */}
          <WeatherMini data={selectedRec?.weather_snapshot} />

          {/* Events for this day */}
          <DayEvents events={events} date={selectedDay.date} />

          {selectedRec ? (
            <>
              {selectedRec.notes && (
                <p style={{ fontSize: '0.875rem', color: 'var(--cream-dim)', lineHeight: 1.5, fontStyle: 'italic', margin: 0 }}>
                  "{selectedRec.notes}"
                </p>
              )}

              <OutfitItems items={selectedRec.outfit_items} />

              {(selectedRec.accepted === null || selectedRec.accepted === undefined) ? (
                <div style={{ display: 'flex', gap: 10 }}>
                  <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => handleFeedback(selectedRec.id, false)}>
                    ✕ Skip
                  </button>
                  <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => handleFeedback(selectedRec.id, true)}>
                    ✓ Wearing this
                  </button>
                </div>
              ) : null}
            </>
          ) : (
            <div style={{ color: 'var(--cream-dim)', fontSize: '0.875rem', textAlign: 'center', padding: '20px 0' }}>
              No outfit generated for this day yet. Generate the full week above.
            </div>
          )}
        </div>
      )}

      {/* Quick actions */}
      <div className="grid-3 fade-up fade-up-delay-3" style={{ marginTop: 24 }}>
        {[
          { icon: '👔', label: 'Add wardrobe item', href: '/wardrobe' },
          { icon: '✈',  label: 'Plan a trip',       href: '/trips' },
          { icon: '🌍', label: 'Cultural guide',     href: '/cultural' },
          { icon: '📊', label: 'Outfit history',     href: '/outfit-history' },
        ].map(({ icon, label, href }) => (
          <a key={href} href={href} className="card" style={{ display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer', textDecoration: 'none' }}>
            <span style={{ fontSize: '1.5rem' }}>{icon}</span>
            <span style={{ fontSize: '0.875rem', color: 'var(--cream)' }}>{label}</span>
            <span style={{ marginLeft: 'auto', color: 'var(--cream-dim)' }}>→</span>
          </a>
        ))}
      </div>
    </div>
  )
}
