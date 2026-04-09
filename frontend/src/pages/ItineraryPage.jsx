// src/pages/ItineraryPage.jsx
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { itinerary as itineraryApi, agents } from '../api/index.js'

const EVENT_TYPE_LABELS = {
  external_meeting: 'Client meeting',
  internal_meeting: 'Internal meeting',
  workout:          'Workout',
  social:           'Social',
  travel:           'Travel',
  free:             'Free day',
  wedding:          'Wedding',
  interview:        'Interview',
  date:             'Date',
  other:            'Other',
}

const EVENT_ICONS = {
  external_meeting: '💼', internal_meeting: '💬', workout: '🏃',
  social: '🍽', travel: '✈', wedding: '💍', interview: '🎯',
  date: '❤', free: '☀', other: '📌',
}

const FORMALITY_BADGE = {
  formal: 'badge-gold', smart: 'badge-sky',
  casual_smart: 'badge-terra', casual: 'badge-sage', activewear: 'badge-sage',
}

export default function ItineraryPage() {
  const [events,    setEvents]   = useState([])
  const [loading,   setLoading]  = useState(true)
  const [showAdd,   setShowAdd]  = useState(false)
  const [syncing,   setSyncing]  = useState(false)
  const [checking,  setChecking] = useState(false)
  const [conflicts, setConflicts]= useState(null)
  const [error,     setError]    = useState('')
  const [needsCalendar, setNeedsCalendar] = useState(false)
  const [dateFilter,setDateFilter]= useState(new Date().toISOString().split('T')[0])

  useEffect(() => { loadEvents() }, [dateFilter])

  const loadEvents = async () => {
    setLoading(true)
    try {
      const data = await itineraryApi.events.list({ date: dateFilter })
      setEvents(data?.results || [])
    } catch { setEvents([]) }
    finally { setLoading(false) }
  }

  const deleteEvent = async (id) => {
    await itineraryApi.events.delete(id)
    setEvents(prev => prev.filter(e => e.id !== id))
  }

  const syncCalendar = async () => {
    setSyncing(true)
    setError('')
    setNeedsCalendar(false)
    try {
      const res = await itineraryApi.events.sync?.() || await fetch('/api/itinerary/events/sync/', { method: 'POST', headers: { Authorization: `Bearer ${localStorage.getItem('gg_access')}` } }).then(r => r.json())
      if (res.status === 'no_calendars_connected') {
        setNeedsCalendar(true)
      } else if (res.status === 'synced') {
        setError(`Synced — ${res.created || 0} new, ${res.updated || 0} updated events.`)
        await loadEvents()
      } else {
        setError(res.message || 'Calendar sync initiated.')
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setSyncing(false)
    }
  }

  const checkConflicts = async () => {
    setChecking(true)
    setConflicts(null)
    try {
      const result = await agents.conflictDetector({ date: dateFilter })
      if (result.status === 'completed') setConflicts(result.output)
    } catch (e) {
      setError(e.message)
    } finally {
      setChecking(false)
    }
  }

  return (
    <div>
      <div className="page-header fade-up">
        <div className="date-line">Schedule</div>
        <h1>Your Calendar</h1>
        <p>Events auto-classify to suggest the right outfit formality.</p>
      </div>

      {/* Controls */}
      <div className="fade-up fade-up-delay-1" style={{ display:'flex', gap:'10px', marginBottom:'24px', flexWrap:'wrap', alignItems:'center' }}>
        <input
          type="date"
          className="input"
          value={dateFilter}
          onChange={e => setDateFilter(e.target.value)}
          style={{ maxWidth:'180px' }}
        />
        <button className="btn btn-secondary btn-sm" onClick={checkConflicts} disabled={checking}>
          {checking ? <><span className="spinner" style={{width:14,height:14}}/> Checking…</> : '⚡ Check conflicts'}
        </button>
        <button className="btn btn-ghost btn-sm" onClick={syncCalendar} disabled={syncing}>
          {syncing ? 'Syncing…' : '↻ Sync calendar'}
        </button>
        <button className="btn btn-primary" style={{ marginLeft:'auto' }} onClick={() => setShowAdd(true)}>
          + Add event
        </button>
      </div>

      {error && (
        <div className="alert alert-info fade-up" style={{ marginBottom:'16px' }}>ℹ {error}</div>
      )}

      {needsCalendar && (
        <div className="alert alert-info fade-up" style={{
          marginBottom:'16px',
          display:'flex',
          alignItems:'center',
          justifyContent:'space-between',
          gap:'12px',
          flexWrap:'wrap',
        }}>
          <span>
            ℹ No calendars connected yet. Connect Google, Apple, or Outlook to sync your events automatically.
          </span>
          <Link to="/profile" className="btn btn-primary btn-sm" style={{ textDecoration:'none' }}>
            Connect a calendar →
          </Link>
        </div>
      )}

      {/* Conflicts panel */}
      {conflicts && (
        <div className="card fade-up" style={{ marginBottom:'20px', borderColor: conflicts.conflicts?.length ? 'rgba(201,168,76,0.3)' : 'rgba(123,166,136,0.3)' }}>
          <div className="card-label" style={{ marginBottom:'8px' }}>
            {conflicts.conflicts?.length ? '⚡ Conflicts detected' : '✓ No conflicts'}
          </div>
          {conflicts.conflicts?.length === 0 ? (
            <p style={{ fontSize:'0.875rem', color:'var(--cream-dim)' }}>
              Everything looks good for {dateFilter}. {conflicts.events_checked} event{conflicts.events_checked !== 1 ? 's' : ''} checked.
            </p>
          ) : (
            <div style={{ display:'flex', flexDirection:'column', gap:'8px' }}>
              {conflicts.conflicts.map((c, i) => (
                <div key={i} style={{ fontSize:'0.875rem', color: c.severity === 'warning' ? 'var(--gold)' : 'var(--cream-dim)' }}>
                  {c.severity === 'warning' ? '⚠ ' : 'ℹ '}{c.message}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Events list */}
      {loading ? (
        <div style={{ display:'flex', flexDirection:'column', gap:'10px' }}>
          {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height:80, borderRadius:'var(--radius-lg)' }} />)}
        </div>
      ) : events.length === 0 ? (
        <div className="empty-state card fade-up">
          <div className="empty-icon">📅</div>
          <div className="empty-title">Nothing scheduled</div>
          <div className="empty-body">Add events manually or sync your Google Calendar.</div>
          <button className="btn btn-primary" onClick={() => setShowAdd(true)}>+ Add event</button>
        </div>
      ) : (
        <div style={{ display:'flex', flexDirection:'column', gap:'10px' }} className="fade-up fade-up-delay-2">
          {events.map(ev => (
            <div key={ev.id} className="card" style={{ display:'flex', alignItems:'center', gap:'16px' }}>
              <span style={{ fontSize:'1.75rem', width:'32px', textAlign:'center' }}>
                {EVENT_ICONS[ev.event_type] || '📌'}
              </span>
              <div style={{ flex:1 }}>
                <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom:'4px' }}>
                  <span style={{ fontWeight:500, color:'var(--cream)' }}>{ev.title}</span>
                  {ev.formality && (
                    <span className={`badge ${FORMALITY_BADGE[ev.formality] || 'badge-sky'}`}>
                      {ev.formality.replace('_',' ')}
                    </span>
                  )}
                  <span className="badge" style={{ background:'var(--surface-3)', color:'var(--cream-dim)' }}>
                    {EVENT_TYPE_LABELS[ev.event_type] || ev.event_type}
                  </span>
                </div>
                <div style={{ fontSize:'0.8rem', color:'var(--cream-dim)', display:'flex', gap:'12px' }}>
                  {ev.start_time && (
                    <span>
                      {new Date(ev.start_time).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}
                      {ev.end_time ? ` – ${new Date(ev.end_time).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}` : ''}
                    </span>
                  )}
                  {ev.location && <span>📍 {ev.location}</span>}
                </div>
              </div>
              <button
                className="btn btn-ghost btn-icon btn-sm"
                onClick={() => deleteEvent(ev.id)}
                title="Delete event"
                style={{ color:'var(--cream-dim)', fontSize:'0.9rem' }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {showAdd && (
        <AddEventModal
          defaultDate={dateFilter}
          onClose={() => setShowAdd(false)}
          onAdd={ev => { setEvents(prev => [...prev, ev]); setShowAdd(false) }}
        />
      )}
    </div>
  )
}

function AddEventModal({ defaultDate, onClose, onAdd }) {
  const [form, setForm] = useState({
    title: '', event_type: 'other', start_time: `${defaultDate}T09:00`,
    end_time: `${defaultDate}T10:00`, location: '',
  })
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')
  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const ev = await itineraryApi.events.create({
        ...form,
        start_time: new Date(form.start_time).toISOString(),
        end_time:   new Date(form.end_time).toISOString(),
      })
      onAdd(ev)
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to create event.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.6)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:1000 }}
         onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="card" style={{ width:'100%', maxWidth:'480px', background:'var(--surface-1)' }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'20px' }}>
          <div style={{ fontFamily:'var(--font-display)', fontSize:'1.25rem', color:'var(--cream)' }}>Add event</div>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={submit} style={{ display:'flex', flexDirection:'column', gap:'14px' }}>
          <div className="input-group">
            <label className="input-label">Title</label>
            <input className="input" value={form.title} onChange={set('title')} placeholder='e.g. "Client presentation"' required />
          </div>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'10px' }}>
            <div className="input-group">
              <label className="input-label">Start</label>
              <input type="datetime-local" className="input" value={form.start_time} onChange={set('start_time')} required />
            </div>
            <div className="input-group">
              <label className="input-label">End</label>
              <input type="datetime-local" className="input" value={form.end_time} onChange={set('end_time')} />
            </div>
          </div>
          <div className="input-group">
            <label className="input-label">Event type</label>
            <select className="input" value={form.event_type} onChange={set('event_type')}>
              {Object.entries(EVENT_TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div className="input-group">
            <label className="input-label">Location (optional)</label>
            <input className="input" value={form.location} onChange={set('location')} placeholder="Office, restaurant, gym…" />
          </div>
          {error && <div className="alert alert-error">{error}</div>}
          <div style={{ display:'flex', gap:'10px', marginTop:'4px' }}>
            <button type="button" className="btn btn-ghost" style={{ flex:1 }} onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" style={{ flex:1 }} disabled={loading}>
              {loading ? 'Adding…' : 'Add event'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
