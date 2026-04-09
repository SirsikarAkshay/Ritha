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
  const [activeTab,setActiveTab]= useState('etiquette')

  const search = async (e) => {
    e?.preventDefault()
    if (!country.trim()) return
    setLoading(true)
    setError('')
    setAdvice(null)
    setActiveTab('etiquette')
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
        const out = result.output || {}
        setAdvice(out)
        // The agent returns the full ruleset (DB + AI-generated). Replace the
        // existing state so the UI shows everything the AI produced, not just
        // whatever the DB-only endpoint returned earlier.
        if (Array.isArray(out.rules))        setRules(out.rules)
        if (Array.isArray(out.local_events)) setEvents(out.local_events)
      } else {
        setError(result.error || 'AI advisor failed')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setAiLoading(false)
    }
  }

  const CAT_ICON = {
    top: '👕', bottom: '👖', dress: '👗', outerwear: '🧥',
    footwear: '👟', accessory: '💍', activewear: '🏃', formal: '🤵', other: '📦',
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
            <div style={{ flex: 1 }}>
              <div className="card-label">
                AI Cultural Advisor
                {advice.source === 'ai' && (
                  <span style={{ marginLeft: 8, fontSize: '0.65rem', color: 'var(--terra-light)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    · AI-generated
                  </span>
                )}
              </div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.125rem', color: 'var(--cream)', marginBottom: '12px' }}>
                Clothing guide for {advice.country}{advice.city ? `, ${advice.city}` : ''}
              </div>
              {advice.summary && (
                <p style={{ color: 'var(--cream-dim)', fontSize: '0.9rem', lineHeight: 1.5, margin: 0 }}>
                  {advice.summary}
                </p>
              )}
            </div>
          </div>
          {!advice.summary && advice.rules?.length === 0 && advice.local_events?.length === 0 && (
            <p style={{ color: 'var(--cream-dim)', fontSize: '0.875rem' }}>
              The advisor couldn't generate guidance for this destination. Try a different country or check that your Mistral API key is configured.
            </p>
          )}
        </div>
      )}

      {/* Tabbed content */}
      {rules !== null && (() => {
        const highlights = advice?.highlights || []
        const placeHighlights = highlights.filter(h => h.type !== 'event')
        const eventHighlights = highlights.filter(h => h.type === 'event')
        const wardrobeCount = (advice?.wardrobe_matches?.length || 0) + (advice?.gaps?.length || 0)
        const eventsCount = eventHighlights.length + (events?.length || 0)

        const TABS = [
          { id: 'etiquette', label: 'Etiquette',     icon: '📜', count: rules.length },
          { id: 'places',    label: 'Places to Visit', icon: '📍', count: placeHighlights.length },
          { id: 'events',    label: 'Events',        icon: '🎊', count: eventsCount },
          { id: 'wardrobe',  label: 'Your Wardrobe', icon: '👔', count: wardrobeCount },
        ]

        return (
        <div className="fade-up">
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: 'var(--cream)', marginBottom: '16px' }}>
            Cultural guide
            {country && <span style={{ color: 'var(--cream-dim)', fontSize: '1rem', fontFamily: 'var(--font-body)', fontWeight: 400 }}> for {country}{city ? `, ${city}` : ''}</span>}
          </div>

          {/* Tab navigation */}
          <div
            role="tablist"
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 8,
              marginBottom: 24,
              borderBottom: '1px solid var(--border)',
              paddingBottom: 2,
            }}
          >
            {TABS.map(t => {
              const isActive = activeTab === t.id
              return (
                <button
                  key={t.id}
                  role="tab"
                  aria-selected={isActive}
                  onClick={() => setActiveTab(t.id)}
                  className="btn btn-ghost btn-sm"
                  style={{
                    borderRadius: 0,
                    border: 'none',
                    borderBottom: isActive ? '2px solid var(--terra-light)' : '2px solid transparent',
                    color: isActive ? 'var(--cream)' : 'var(--cream-dim)',
                    fontWeight: isActive ? 500 : 400,
                    padding: '10px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                >
                  <span>{t.icon}</span>
                  <span>{t.label}</span>
                  <span
                    className="badge"
                    style={{
                      background: 'var(--surface-3)',
                      color: 'var(--cream-dim)',
                      fontSize: '0.65rem',
                      padding: '2px 8px',
                    }}
                  >
                    {t.count}
                  </span>
                </button>
              )
            })}
          </div>

          {/* Etiquette tab */}
          {activeTab === 'etiquette' && (
          <div role="tabpanel">
          {rules.length === 0 && (
            <div className="empty-state card">
              <div className="empty-icon">📜</div>
              <div className="empty-title">No etiquette rules found</div>
              <div className="empty-body">Try searching a different destination or request AI advice above.</div>
            </div>
          )}
          {rules.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
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
          </div>
          )}

          {/* Places tab */}
          {activeTab === 'places' && (
          <div role="tabpanel">
            {placeHighlights.length === 0 ? (
              <div className="empty-state card">
                <div className="empty-icon">📍</div>
                <div className="empty-title">No places yet</div>
                <div className="empty-body">Tap ✦ AI Advice above to get popular destinations with clothing guidance.</div>
              </div>
            ) : (
            <>
              <div style={{ color: 'var(--cream-dim)', fontSize: '0.85rem', marginBottom: 16 }}>
                Popular spots to dress for, with specific clothing guidance for each.
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
                {placeHighlights.map((h, i) => {
                  const isEvent = h.type === 'event'
                  return (
                    <div key={i} className="card" style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '1.25rem', lineHeight: 1 }}>{isEvent ? '🎊' : '📍'}</span>
                        <div style={{ flex: 1, minWidth: 0, fontWeight: 500, color: 'var(--cream)', fontSize: '0.95rem' }}>
                          {h.name}
                        </div>
                        <span className={`badge ${isEvent ? 'badge-gold' : 'badge-sky'}`} style={{ fontSize: '0.65rem' }}>
                          {isEvent ? 'EVENT' : 'PLACE'}
                        </span>
                      </div>
                      {h.when && h.when !== 'year-round' && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--terra-light)', fontWeight: 500 }}>
                          📅 {h.when}
                        </div>
                      )}
                      {h.description && (
                        <div style={{ fontSize: '0.8rem', color: 'var(--cream-dim)', lineHeight: 1.4 }}>
                          {h.description}
                        </div>
                      )}
                      {h.clothing && (
                        <div style={{
                          marginTop: 'auto',
                          paddingTop: 10,
                          borderTop: '1px solid var(--border)',
                          fontSize: '0.8rem',
                          color: 'var(--cream)',
                          lineHeight: 1.4,
                        }}>
                          <span style={{ color: 'var(--terra-light)', fontWeight: 500 }}>👔 What to wear: </span>
                          {h.clothing}
                        </div>
                      )}
                      {h.formality && (
                        <span className="badge" style={{ background: 'var(--surface-3)', color: 'var(--cream-dim)', fontSize: '0.65rem', alignSelf: 'flex-start' }}>
                          {h.formality.replace('_', ' ')}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            </>
            )}
          </div>
          )}

          {/* Wardrobe tab */}
          {activeTab === 'wardrobe' && (
          <div role="tabpanel">
            {wardrobeCount === 0 && (
              <div className="empty-state card">
                <div className="empty-icon">👔</div>
                <div className="empty-title">No wardrobe advice yet</div>
                <div className="empty-body">Tap ✦ AI Advice above to see which of your items work and what's missing.</div>
              </div>
            )}
          {advice?.wardrobe_matches?.length > 0 && (
            <div style={{ marginBottom: 32 }}>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: 'var(--cream)', marginBottom: 16 }}>
                From your wardrobe
                <span style={{ color: 'var(--cream-dim)', fontSize: '0.9rem', fontFamily: 'var(--font-body)', fontWeight: 400, marginLeft: 8 }}>
                  · items you already own that work for this destination
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
                {advice.wardrobe_matches.map(m => (
                  <div key={m.item_id} className="card" style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: 16 }}>
                    <span style={{ fontSize: '1.75rem', lineHeight: 1 }}>{CAT_ICON[m.category] || '📦'}</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 500, color: 'var(--cream)', fontSize: '0.9rem', marginBottom: 4 }}>
                        {m.name}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--cream-dim)', lineHeight: 1.4 }}>
                        {m.reason}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Gaps — shop the look */}
          {advice?.gaps?.length > 0 && (
            <div style={{ marginBottom: 32 }}>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: 'var(--cream)', marginBottom: 6 }}>
                Missing from your wardrobe
              </div>
              <div style={{ color: 'var(--cream-dim)', fontSize: '0.85rem', marginBottom: 16 }}>
                Things you should bring but don't own yet. Tap a link to shop.
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {advice.gaps.map((g, i) => (
                  <div key={i} className="card" style={{ padding: 16 }}>
                    <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 10 }}>
                      <span style={{ fontSize: '1.5rem', lineHeight: 1 }}>{CAT_ICON[g.category] || '🛍'}</span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 500, color: 'var(--cream)', fontSize: '0.95rem', marginBottom: 4 }}>
                          {g.description}
                        </div>
                        {g.why && (
                          <div style={{ fontSize: '0.8rem', color: 'var(--cream-dim)', lineHeight: 1.4 }}>
                            {g.why}
                          </div>
                        )}
                      </div>
                    </div>
                    {g.search_links?.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, paddingTop: 10, borderTop: '1px solid var(--border)' }}>
                        {g.search_links.map((link, li) => (
                          <a
                            key={li}
                            href={link.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-ghost btn-sm"
                            style={{
                              fontSize: '0.75rem',
                              border: '1px solid var(--border)',
                              borderRadius: 100,
                              textDecoration: 'none',
                            }}
                          >
                            🔗 {link.label}
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          </div>
          )}

          {/* Events tab */}
          {activeTab === 'events' && (
          <div role="tabpanel">
            {eventsCount === 0 ? (
              <div className="empty-state card">
                <div className="empty-icon">🎊</div>
                <div className="empty-title">No events found</div>
                <div className="empty-body">We couldn't find upcoming events for this destination. Try ✦ AI Advice for suggestions.</div>
              </div>
            ) : (
            <>
              {eventHighlights.length > 0 && (
                <div style={{ marginBottom: 32 }}>
                  <div style={{ color: 'var(--cream-dim)', fontSize: '0.85rem', marginBottom: 16 }}>
                    Upcoming events in the next two weeks, with specific clothing for each.
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
                    {eventHighlights.map((h, i) => (
                      <div key={i} className="card" style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                          <span style={{ fontSize: '1.25rem', lineHeight: 1 }}>🎊</span>
                          <div style={{ flex: 1, minWidth: 0, fontWeight: 500, color: 'var(--cream)', fontSize: '0.95rem' }}>
                            {h.name}
                          </div>
                          <span className="badge badge-gold" style={{ fontSize: '0.65rem' }}>EVENT</span>
                        </div>
                        {h.when && h.when !== 'year-round' && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--terra-light)', fontWeight: 500 }}>
                            📅 {h.when}
                          </div>
                        )}
                        {h.description && (
                          <div style={{ fontSize: '0.8rem', color: 'var(--cream-dim)', lineHeight: 1.4 }}>
                            {h.description}
                          </div>
                        )}
                        {h.clothing && (
                          <div style={{
                            marginTop: 'auto',
                            paddingTop: 10,
                            borderTop: '1px solid var(--border)',
                            fontSize: '0.8rem',
                            color: 'var(--cream)',
                            lineHeight: 1.4,
                          }}>
                            <span style={{ color: 'var(--terra-light)', fontWeight: 500 }}>👔 What to wear: </span>
                            {h.clothing}
                          </div>
                        )}
                        {h.formality && (
                          <span className="badge" style={{ background: 'var(--surface-3)', color: 'var(--cream-dim)', fontSize: '0.65rem', alignSelf: 'flex-start' }}>
                            {h.formality.replace('_', ' ')}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {events?.length > 0 && (
                <div>
                  <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.125rem', color: 'var(--cream)', marginBottom: '16px' }}>
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
            </>
            )}
          </div>
          )}
        </div>
        )
      })()}

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
