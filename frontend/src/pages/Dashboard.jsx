import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth.jsx'
import { outfits, agents, weather, itinerary } from '../api/index.js'
import { format } from 'date-fns'
import styles from './Dashboard.module.css'

export default function Dashboard() {
  const { user }                 = useAuth()
  const [outfit,   setOutfit]    = useState(null)
  const [wx,       setWx]        = useState(null)
  const [events,   setEvents]    = useState([])
  const [loading,  setLoading]   = useState(true)
  const [generating, setGenerating] = useState(false)
  const [feedback, setFeedback]  = useState(null) // 'accepted' | 'rejected'

  const today = format(new Date(), 'yyyy-MM-dd')
  const greeting = () => {
    const h = new Date().getHours()
    if (h < 12) return 'Good morning'
    if (h < 17) return 'Good afternoon'
    return 'Good evening'
  }

  useEffect(() => {
    Promise.all([
      loadOutfit(),
      loadEvents(),
      loadWeather(),
    ]).finally(() => setLoading(false))
  }, [])

  const loadOutfit = async () => {
    try {
      const data = await outfits.daily(today)
      setOutfit(data)
      setFeedback(data.accepted === true ? 'accepted' : data.accepted === false ? 'rejected' : null)
    } catch { setOutfit(null) }
  }

  const loadEvents = async () => {
    try {
      const data = await itinerary.events.list({ date: today })
      setEvents(data.results || [])
    } catch { setEvents([]) }
  }

  const loadWeather = async () => {
    try {
      const data = await weather.byLocation('Zurich')
      setWx(data)
    } catch { setWx(null) }
  }

  const generateLook = async () => {
    setGenerating(true)
    try {
      await agents.dailyLook({ weather: wx || {} })
      await loadOutfit()
    } finally {
      setGenerating(false)
    }
  }

  const sendFeedback = async (accepted) => {
    if (!outfit?.id) return
    await outfits.feedback(outfit.id, accepted)
    setFeedback(accepted ? 'accepted' : 'rejected')
  }

  if (loading) return <div className={styles.loading}><span className="spinner" /></div>

  return (
    <div className="page-enter">
      {/* Header */}
      <div className={styles.header}>
        <div>
          <p className="text-label">{format(new Date(), 'EEEE, MMMM d')}</p>
          <h1 className={styles.greeting}>
            {greeting()}{user?.first_name ? `, ${user.first_name}` : ''}.
          </h1>
        </div>
        {wx && (
          <div className={styles.weatherChip}>
            <span className={styles.weatherTemp}>{wx.temp_c}°C</span>
            <span className={styles.weatherDesc}>{wx.condition}</span>
          </div>
        )}
      </div>

      <div className={styles.grid}>
        {/* Today's Look */}
        <div className={`${styles.outfitCard} card`}>
          <div className={styles.cardHeader}>
            <p className="text-label">Today's Look</p>
            {outfit && !feedback && (
              <div className={styles.feedbackRow}>
                <button className="btn btn-sm btn-ghost" onClick={() => sendFeedback(false)}>✕ Skip</button>
                <button className="btn btn-sm btn-primary" onClick={() => sendFeedback(true)}>✓ Wearing this</button>
              </div>
            )}
          </div>

          {outfit ? (
            <>
              {feedback === 'accepted' && (
                <div className={styles.feedbackBadge}>
                  <span className="badge badge-sage">✓ Wearing this today</span>
                </div>
              )}
              {feedback === 'rejected' && (
                <div className={styles.feedbackBadge}>
                  <span className="badge badge-muted">Skipped</span>
                </div>
              )}

              <p className={styles.outfitNotes}>{outfit.notes || 'Your outfit for today is ready.'}</p>

              {outfit.outfit_items?.length > 0 && (
                <div className={styles.itemList}>
                  {outfit.outfit_items.map((oi, i) => (
                    <div key={i} className={styles.itemChip}>
                      <span className={styles.itemRole}>{oi.role}</span>
                      <span>Item #{oi.clothing_item}</span>
                    </div>
                  ))}
                </div>
              )}

              {outfit.weather_snapshot?.condition && (
                <p className={styles.weatherNote}>
                  ⛅ {outfit.weather_snapshot.condition}
                  {outfit.weather_snapshot.temp_c && ` · ${outfit.weather_snapshot.temp_c}°C`}
                </p>
              )}
            </>
          ) : (
            <div className={styles.noOutfit}>
              <p>No outfit generated yet for today.</p>
              <button className="btn btn-primary" onClick={generateLook} disabled={generating}>
                {generating ? <><span className="spinner" /> Generating…</> : '✦ Generate today\'s look'}
              </button>
            </div>
          )}
        </div>

        {/* Today's Schedule */}
        <div className={`${styles.scheduleCard} card`}>
          <p className="text-label" style={{marginBottom:'1rem'}}>Today's Schedule</p>
          {events.length > 0 ? (
            <div className={styles.eventList}>
              {events.map(ev => (
                <div key={ev.id} className={styles.eventItem}>
                  <div className={styles.eventTime}>
                    {ev.start_time ? format(new Date(ev.start_time), 'HH:mm') : 'All day'}
                  </div>
                  <div className={styles.eventBody}>
                    <div className={styles.eventTitle}>{ev.title}</div>
                    <div className={styles.eventMeta}>
                      <EventTypeBadge type={ev.event_type} />
                      {ev.formality && <span className="badge badge-muted">{ev.formality}</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state" style={{padding:'2rem 0'}}>
              <span className="icon">◷</span>
              <p>Nothing scheduled today.</p>
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className={`${styles.actionsCard} card`}>
          <p className="text-label" style={{marginBottom:'1rem'}}>Quick Actions</p>
          <div className={styles.actions}>
            <QuickAction icon="◈" label="Add wardrobe item" href="/wardrobe/new" />
            <QuickAction icon="◷" label="Add schedule event" href="/itinerary/new" />
            <QuickAction icon="◎" label="Plan a trip" href="/trips/new" />
            <QuickAction icon="◉" label="Check destination" href="/cultural" />
          </div>
        </div>
      </div>
    </div>
  )
}

function EventTypeBadge({ type }) {
  const map = {
    external_meeting: ['badge-amber', 'Client'],
    internal_meeting: ['badge-muted', 'Meeting'],
    workout:          ['badge-sage',  'Workout'],
    social:           ['badge-rose',  'Social'],
    travel:           ['badge-amber', 'Travel'],
    wedding:          ['badge-rose',  'Wedding'],
    interview:        ['badge-amber', 'Interview'],
  }
  const [cls, label] = map[type] || ['badge-muted', type || 'Event']
  return <span className={`badge ${cls}`}>{label}</span>
}

function QuickAction({ icon, label, href }) {
  return (
    <a href={href} className={styles.quickAction}>
      <span className={styles.qaIcon}>{icon}</span>
      <span>{label}</span>
    </a>
  )
}
