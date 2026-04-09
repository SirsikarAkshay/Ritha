// src/pages/CulturalPage.jsx
import { useState } from 'react'
import { cultural, agents } from '../api/index.js'

const SEVERITY_STYLE = {
  required: { badge: 'badge-terra',  icon: '⚠' },
  warning:  { badge: 'badge-gold',   icon: '⚡' },
  info:     { badge: 'badge-sky',    icon: 'ℹ' },
}

const RULE_ICONS = {
  cover_head:      '🧕',
  cover_shoulders: '👘',
  cover_knees:     '👖',
  remove_shoes:    '👟',
  modest_dress:    '🎀',
  no_bare_feet:    '🦶',
  festival_wear:   '🎊',
  color_warning:   '🎨',
  general:         '📝',
}

export default function CulturalPage() {
  const [country,  setCountry]  = useState('')
  const [city,     setCity]     = useState('')
  const [rules,    setRules]    = useState(null)
  const [events,   setEvents]   = useState(null)
  const [advice,   setAdvice]   = useState(null)
  const [loading,  setLoading]  = useState(false)
  const [aiLoading,setAiLoading]= useState(false)
  const [error,    setError]    = useState('')

  const search = async (e) => {
    e?.preventDefault()
    if (!country.trim()) return
    setLoading(true)
    setError('')
    setAdvice(null)
    try {
      const [r, ev] = await Promise.all([
        cultural.rules(country, city),
        cultural.events(country, new Date().getMonth() + 1),
      ])
      setRules(r?.results || [])
      setEvents(ev?.results || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const getAiAdvice = async () => {
    setAiLoading(true)
    setError('')
    try {
      const result = await agents.culturalAdvisor({ country, city })
      if (result.status === 'completed') {
        setAdvice(result.output)
      } else {
        setError(result.error || 'AI advisor failed')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setAiLoading(false)
    }
  }

  const POPULAR = ['Japan', 'Turkey', 'India', 'Italy', 'Morocco', 'Thailand', 'Saudi Arabia']

  return (
    <div>
      <div className="page-header fade-up">
        <div className="date-line">Cultural Guide</div>
        <h1>Dress Right, Everywhere</h1>
        <p>Etiquette rules, local events, and clothing advice for your destination.</p>
      </div>

      {/* Search */}
      <form onSubmit={search} style={{ display: 'flex', gap: '10px', marginBottom: '16px' }} className="fade-up fade-up-delay-1">
        <input className="input" placeholder="Country (e.g. Turkey)" value={country} onChange={e => setCountry(e.target.value)} style={{ maxWidth: '200px' }} required />
        <input className="input" placeholder="City (optional)" value={city} onChange={e => setCity(e.target.value)} style={{ maxWidth: '160px' }} />
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? <span className="spinner" style={{ width: 16, height: 16 }} /> : '🔍 Search'}
        </button>
        {rules !== null && country && (
          <button type="button" className="btn btn-secondary" onClick={getAiAdvice} disabled={aiLoading}>
            {aiLoading ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Thinking…</> : '✦ AI Advice'}
          </button>
        )}
      </form>

      {/* Popular countries */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '32px' }} className="fade-up fade-up-delay-1">
        {POPULAR.map(c => (
          <button key={c} className="btn btn-ghost btn-sm"
            style={{ borderRadius: 100, border: '1px solid var(--border)', fontSize: '0.75rem' }}
            onClick={() => { setCountry(c); setTimeout(() => document.querySelector('form')?.requestSubmit(), 50) }}
          >
            {c}
          </button>
        ))}
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: '20px' }}>⚠ {error}</div>}

      {/* AI Advice box */}
      {advice && (
        <div className="card fade-up" style={{ marginBottom: '24px', background: 'linear-gradient(135deg, rgba(212,114,74,0.08), var(--surface-1))' }}>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start', marginBottom: '12px' }}>
            <span style={{ fontSize: '1.5rem' }}>✦</span>
            <div>
              <div className="card-label">AI Cultural Advisor</div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.125rem', color: 'var(--cream)', marginBottom: '12px' }}>
                Clothing guide for {advice.country}{advice.city ? `, ${advice.city}` : ''}
              </div>
            </div>
          </div>
          {advice.rules?.length === 0 && advice.local_events?.length === 0 && (
            <p style={{ color: 'var(--cream-dim)', fontSize: '0.875rem' }}>No specific etiquette rules found in our database for this destination. General travel courtesy applies.</p>
          )}
        </div>
      )}

      {/* Rules */}
      {rules !== null && (
        <div className="fade-up">
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: 'var(--cream)', marginBottom: '16px' }}>
            {rules.length > 0 ? `${rules.length} etiquette rule${rules.length !== 1 ? 's' : ''}` : 'No etiquette rules found'}
            {country && <span style={{ color: 'var(--cream-dim)', fontSize: '1rem', fontFamily: 'var(--font-body)', fontWeight: 400 }}> for {country}{city ? `, ${city}` : ''}</span>}
          </div>

          {rules.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '32px' }}>
              {rules.map((rule, i) => {
                const sev = SEVERITY_STYLE[rule.severity] || SEVERITY_STYLE.info
                return (
                  <div key={i} className="card" style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
                    <span style={{ fontSize: '1.5rem', lineHeight: 1 }}>{RULE_ICONS[rule.rule_type] || '📝'}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                        {rule.place_name && (
                          <span style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--cream)' }}>
                            {rule.place_name}
                          </span>
                        )}
                        <span className={`badge ${sev.badge}`}>{sev.icon} {rule.severity}</span>
                        <span className="badge" style={{ background: 'var(--surface-3)', color: 'var(--cream-dim)' }}>
                          {rule.rule_type.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <p style={{ fontSize: '0.875rem', color: 'var(--cream-dim)', lineHeight: 1.5 }}>{rule.description}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Local events */}
          {events?.length > 0 && (
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: 'var(--cream)', marginBottom: '16px' }}>
                Events this month
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {events.map((ev, i) => (
                  <div key={i} className="card" style={{ display: 'flex', gap: '14px' }}>
                    <span style={{ fontSize: '1.5rem' }}>🎊</span>
                    <div>
                      <div style={{ fontWeight: 500, color: 'var(--cream)', marginBottom: '4px' }}>{ev.name}</div>
                      <p style={{ fontSize: '0.875rem', color: 'var(--cream-dim)', marginBottom: '8px', lineHeight: 1.5 }}>{ev.description}</p>
                      {ev.clothing_note && (
                        <div style={{
                          background: 'var(--gold-dim)', border: '1px solid rgba(201,168,76,0.2)',
                          borderRadius: 'var(--radius-md)', padding: '8px 12px',
                          fontSize: '0.8rem', color: 'var(--gold)', lineHeight: 1.4,
                        }}>
                          👔 {ev.clothing_note}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {rules === null && !loading && (
        <div className="empty-state card fade-up fade-up-delay-2">
          <div className="empty-icon">🌍</div>
          <div className="empty-title">Search a destination</div>
          <div className="empty-body">Enter a country above to see etiquette rules, local events, and clothing advice.</div>
        </div>
      )}
    </div>
  )
}
