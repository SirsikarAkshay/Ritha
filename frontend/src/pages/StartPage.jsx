// Destination-first, fully-unauthenticated "instant insight" landing.
// Prove intelligence before asking for a single piece of personal data — the
// visitor types a destination, sees weather + dress code + places + a standard
// packing capsule + gap analysis, and is only prompted to sign up when they hit
// a persistence trigger (save the trip / personalise with their own wardrobe).
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { agents } from '../api/index.js'
import { useAuth } from '../hooks/useAuth.jsx'
import PlaceAutocomplete from '../components/PlaceAutocomplete.jsx'

const IMG_CATS = new Set(['top', 'bottom', 'dress', 'outerwear', 'footwear', 'accessory', 'activewear', 'formal', 'other'])
const catImg = (c) => `/wardrobe-defaults/${IMG_CATS.has(c) ? c : 'other'}.svg`

// Stash the previewed trip so it survives sign-up + email verification and
// re-attaches to the brand-new account on first authenticated load.
const PENDING_KEY = 'ritha_pending_trip'
function stashPendingTrip(payload) {
  try { localStorage.setItem(PENDING_KEY, JSON.stringify(payload)) } catch { /* ignore */ }
}

export default function StartPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [form, setForm] = useState({ destination: '', place: null, date: '', endDate: '', gender: 'women' })
  const [insights, setInsights] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [signupFor, setSignupFor] = useState(null) // persistence-trigger label, or null
  const [crewHint, setCrewHint] = useState(false)  // soft-prompt when a guest tries to add friends

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const run = async (e) => {
    e?.preventDefault()
    if (!form.destination.trim()) return
    setLoading(true); setError('')
    try {
      const body = { destination: form.destination.trim(), gender: form.gender }
      if (form.date) body.date = form.date
      const res = await agents.publicTripInsights(body)
      setInsights(res?.output || res)
    } catch (err) {
      setError('Could not reach the forecast just now — try again in a moment.')
    } finally {
      setLoading(false)
    }
  }

  // Persistence trigger → stash + prompt sign-up (or, if already signed in, go straight in).
  const persist = (trigger) => {
    stashPendingTrip({ ...form, insights, trigger, at: Date.now() })
    if (user) { navigate('/trips') } else { setSignupFor(trigger) }
  }

  const w = insights?.weather || {}
  const tempC = w.temp_c != null ? Math.round(w.temp_c) : null

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg, #0d0f14)', color: 'var(--cream, #f5f0e8)' }}>
      <div style={{ maxWidth: 760, margin: '0 auto', padding: 'clamp(28px,6vw,64px) 20px 80px' }}>
        {/* Brand + login */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 30 }}>
          <span style={{ fontFamily: 'var(--mono, monospace)', letterSpacing: '.28em', textTransform: 'uppercase', fontSize: '.8rem', color: 'var(--terra-light, #e8956e)' }}>Ritha</span>
          <button onClick={() => navigate('/login')} className="btn" style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--dim)', fontSize: '.85rem', padding: '8px 14px', borderRadius: 10, cursor: 'pointer' }}>Log in</button>
        </div>

        {/* Hook */}
        <div style={{ fontFamily: 'var(--mono, monospace)', fontSize: '.76rem', letterSpacing: '.2em', textTransform: 'uppercase', color: 'var(--sakura, #e79ab0)', marginBottom: 12 }}>
          Ritha · Your travel stylist
        </div>
        <h1 style={{ fontSize: 'clamp(1.9rem,5vw,3rem)', lineHeight: 1.05, letterSpacing: '-.03em', fontWeight: 680, margin: 0, textWrap: 'balance' }}>
          Where are you <span style={{ color: 'var(--terra, #d4724a)' }}>going?</span>
        </h1>
        <p style={{ color: 'var(--dim, #9a97a0)', fontSize: '1.05rem', margin: '14px 0 14px', maxWidth: '48ch', lineHeight: 1.55 }}>
          No sign-up. No closet setup. Tell us the destination — see the whole trip before you commit.
        </p>
        {/* 3-step promise — mirrors the product tour: preview → save → pack together */}
        <p style={{ fontFamily: 'var(--mono, monospace)', fontSize: '.78rem', letterSpacing: '.02em', color: 'var(--faint, #6b6a73)', margin: '0 0 24px', lineHeight: 1.7 }}>
          <b style={{ color: 'var(--terra-light, #e8956e)', fontWeight: 600 }}>①</b> See it &nbsp;·&nbsp;
          <b style={{ color: 'var(--terra-light, #e8956e)', fontWeight: 600 }}>②</b> Save it &nbsp;·&nbsp;
          <b style={{ color: 'var(--terra-light, #e8956e)', fontWeight: 600 }}>③</b> Pack it together
        </p>

        {/* Form */}
        <form onSubmit={run} className="card" style={{ padding: 18, display: 'grid', gap: 12, gridTemplateColumns: '1fr', marginBottom: 26 }}>
          {/* Structured city pick (free Open-Meteo geocoding, no auth) → carries
              straight into the trip planner after sign-up, no re-entry. */}
          <PlaceAutocomplete
            mode="city"
            value={form.destination}
            onChange={(v) => setForm((f) => ({ ...f, destination: v, place: null }))}
            onSelect={(p) => setForm((f) => ({ ...f, destination: `${p.name}, ${p.country}`, place: { city: p.name, country: p.country, countryCode: p.country_code } }))}
            placeholder="e.g. Tokyo"
            className="input"
            autoFocus
          />
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <input type="date" value={form.date} onChange={set('date')} aria-label="Trip start date"
              style={{ flex: '1 1 130px', padding: '12px 14px', borderRadius: 12, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--cream)', colorScheme: 'dark' }} />
            <input type="date" value={form.endDate} onChange={set('endDate')} aria-label="Trip end date" min={form.date || undefined}
              style={{ flex: '1 1 130px', padding: '12px 14px', borderRadius: 12, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--cream)', colorScheme: 'dark' }} />
            <select value={form.gender} onChange={set('gender')} aria-label="Style"
              style={{ flex: '1 1 120px', padding: '12px 14px', borderRadius: 12, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--cream)' }}>
              <option value="women">Women's</option><option value="men">Men's</option><option value="kids">Kids'</option>
            </select>
          </div>
          {/* Travelling with — collab affordance. Adding friends before an account
              soft-prompts them forward instead of dead-ending into a sign-up wall. */}
          <div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontFamily: 'var(--mono, monospace)', fontSize: '.7rem', letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--faint, #6b6a73)', marginRight: 2 }}>Travelling with</span>
              <span style={{ padding: '6px 12px', borderRadius: 20, fontSize: '.82rem', background: 'var(--terra, #d4724a)', color: '#fff' }}>Just me</span>
              <button type="button" onClick={() => setCrewHint(true)} aria-expanded={crewHint}
                style={{ padding: '6px 12px', borderRadius: 20, fontSize: '.82rem', background: 'transparent', border: '1px solid var(--border)', color: 'var(--dim)', cursor: 'pointer' }}>
                + Add friends
              </button>
            </div>
            {crewHint && (
              <div role="status" style={{ marginTop: 10, padding: '10px 12px', borderRadius: 12, border: '1px solid rgba(111,168,199,.35)', background: 'rgba(111,168,199,.08)', fontSize: '.85rem', color: 'var(--cream)', lineHeight: 1.45 }}>
                ✨ We'll spin up a <b style={{ color: 'var(--sky, #6fa8c7)' }}>share link for your crew</b> once your trip's created — hit <b style={{ color: 'var(--sky, #6fa8c7)' }}>See my trip</b> first.
              </div>
            )}
          </div>
          <button type="submit" disabled={loading || !form.destination.trim()} className="btn btn-primary"
            style={{ padding: 15, fontSize: '1.05rem', fontWeight: 600, borderRadius: 13, border: 'none', cursor: 'pointer', background: 'var(--terra, #d4724a)', color: '#fff', opacity: loading ? 0.7 : 1 }}>
            {loading ? 'Reading the forecast…' : 'See my trip →'}
          </button>
          {error && <div style={{ color: 'var(--danger, #e0745c)', fontSize: '.9rem' }}>{error}</div>}
        </form>

        {/* ── Collaborative Packing — prominent value prop on the landing ─── */}
        {!insights && (
          <div className="card" style={{ padding: 20, marginBottom: 8, border: '1px solid rgba(111,168,199,.35)', background: 'linear-gradient(180deg, rgba(111,168,199,.09), var(--surface, #161921))' }}>
            <div style={{ fontFamily: 'var(--mono, monospace)', fontSize: '.72rem', letterSpacing: '.12em', textTransform: 'uppercase', color: 'var(--sky, #6fa8c7)', marginBottom: 8 }}>
              👥 Not travelling solo?
            </div>
            <div style={{ fontSize: '1.4rem', fontWeight: 680, letterSpacing: '-.02em', lineHeight: 1.12, marginBottom: 8 }}>
              Collaborative Packing
            </div>
            <div style={{ color: 'var(--dim, #9a97a0)', fontSize: '.96rem', lineHeight: 1.5, marginBottom: 16, maxWidth: '52ch' }}>
              Share one closet with your crew. The moment someone packs a shared item, it drops off{' '}
              <em style={{ fontStyle: 'normal', color: 'var(--cream)' }}>everyone else's</em> bag — live, in the group chat. Nothing gets carried three times.
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '9px 13px', background: 'var(--surface-2, #1c2029)', border: '1px solid var(--border)', borderRadius: 12 }}>
                <span style={{ fontSize: '1.15rem' }}>🔌</span>
                <span style={{ fontSize: '.86rem', color: 'var(--cream)' }}>Aditi packs the adapter</span>
                <span style={{ fontFamily: 'var(--mono, monospace)', fontSize: '.62rem', color: '#9fce9f', background: 'rgba(123,166,126,.16)', padding: '3px 8px', borderRadius: 12, whiteSpace: 'nowrap' }}>shared ×1</span>
              </div>
              <span style={{ color: 'var(--sky, #6fa8c7)', fontFamily: 'var(--mono, monospace)', fontSize: '.82rem', fontWeight: 600 }}>→ 2 bags lighter</span>
            </div>
          </div>
        )}

        {/* ── Instant insight dashboard ─────────────────────────────── */}
        {insights && (
          <div style={{ display: 'grid', gap: 16 }}>
            {/* Weather */}
            <div className="card" style={{ padding: 16, display: 'flex', alignItems: 'center', gap: 14 }}>
              <span style={{ fontSize: '2.2rem' }}>{w.is_raining ? '🌧️' : w.is_cold ? '🧥' : w.is_hot ? '☀️' : '⛅'}</span>
              <div>
                <div style={{ fontSize: '1.15rem', fontWeight: 600 }}>{form.destination}{tempC != null ? ` · ${tempC}°C` : ''}</div>
                <div style={{ color: 'var(--dim)', fontSize: '.9rem' }}>{w.condition || 'Forecast'}{w.feels_like_c != null ? ` · feels ${Math.round(w.feels_like_c)}°` : ''}</div>
              </div>
            </div>

            {/* Dress code alerts */}
            {insights.dress_code?.length > 0 && (
              <div className="card" style={{ padding: 16 }}>
                <div style={{ fontFamily: 'var(--mono)', fontSize: '.72rem', letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--sky, #6fa8c7)', marginBottom: 10 }}>🕌 Local dress code</div>
                {insights.dress_code.map((d, i) => (
                  <div key={i} style={{ fontSize: '.92rem', color: 'var(--cream)', lineHeight: 1.45, padding: '6px 0', borderTop: i ? '1px solid var(--border)' : 'none' }}>{d}</div>
                ))}
              </div>
            )}

            {/* Capsule — clearly labelled as generic */}
            <div className="card" style={{ padding: 16 }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: '.72rem', letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--terra-light)', marginBottom: 4 }}>🎒 Starter packing capsule</div>
              <div style={{ color: 'var(--gold, #c9a84c)', fontSize: '.8rem', marginBottom: 4, fontStyle: 'italic' }}>{insights.capsule_note}</div>
              {/* Reassure that the generic capsule is a temporary placeholder, not a mistake. */}
              <div style={{ color: 'var(--dim, #9a97a0)', fontSize: '.76rem', marginBottom: 12, lineHeight: 1.4 }}>
                We assumed a standard capsule to start — change your home city and swap in your own wardrobe next. This is just a placeholder, not a guess about you.
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(150px,1fr))', gap: 8 }}>
                {insights.capsule.map((it, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 9, padding: 8, background: 'var(--surface-3, #252833)', borderRadius: 10 }}>
                    <img src={catImg(it.category)} alt="" width={30} height={30} style={{ borderRadius: 7, background: 'var(--surface-2,#1c2029)' }} />
                    <span style={{ fontSize: '.82rem' }}>{it.name}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Gap analysis */}
            {insights.gaps?.length > 0 && (
              <div className="card" style={{ padding: 16 }}>
                <div style={{ fontFamily: 'var(--mono)', fontSize: '.72rem', letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--sage, #7ba67e)', marginBottom: 12 }}>🛒 You'll likely need to buy or borrow</div>
                {/* Count-bound teaser — mirrors the tour's "N layers missing for X° nights". */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', marginBottom: 12, background: 'rgba(111,168,199,.1)', border: '1px solid rgba(111,168,199,.3)', borderRadius: 14 }}>
                  <span style={{ fontSize: '1.7rem', fontWeight: 700, color: 'var(--sky, #6fa8c7)', fontFamily: 'var(--mono, monospace)', lineHeight: 1 }}>{insights.gaps.length}</span>
                  <span style={{ fontSize: '.9rem', color: 'var(--cream)', lineHeight: 1.35 }}>
                    piece{insights.gaps.length !== 1 ? 's' : ''} your closet's missing{tempC != null ? ` for ${tempC}° days` : ''} — here's exactly what to add ↓
                  </span>
                </div>
                {insights.gaps.map((g, i) => (
                  <div key={i} style={{ padding: '8px 0', borderTop: i ? '1px solid var(--border)' : 'none' }}>
                    <div style={{ fontWeight: 550 }}>{g.name}</div>
                    <div style={{ color: 'var(--dim)', fontSize: '.82rem', lineHeight: 1.4 }}>{g.why}</div>
                  </div>
                ))}
              </div>
            )}

            {/* Places */}
            {insights.places?.length > 0 && (
              <div className="card" style={{ padding: 16 }}>
                <div style={{ fontFamily: 'var(--mono)', fontSize: '.72rem', letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--sakura, #e79ab0)', marginBottom: 12 }}>📍 While you're there</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {insights.places.map((p, i) => (
                    <span key={i} className="badge" style={{ background: 'var(--surface-3)', color: 'var(--cream)', padding: '6px 12px', borderRadius: 20, fontSize: '.82rem' }}>{p.name}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Persistence triggers → sign-up */}
            <div className="card" style={{ padding: 18, textAlign: 'center', background: 'var(--surface-2, #1c2029)' }}>
              <div style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: 6 }}>Like what you see? Save this trip to make it yours.</div>
              <div style={{ color: 'var(--dim)', fontSize: '.9rem', marginBottom: 14 }}>Save {form.destination || 'this trip'}, personalise the capsule with your own wardrobe, and pack with friends.</div>
              <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
                <button onClick={() => persist('save_trip')} className="btn btn-primary" style={{ padding: '12px 18px', borderRadius: 12, border: 'none', background: 'var(--terra)', color: '#fff', fontWeight: 600, cursor: 'pointer' }}>💾 Save this trip</button>
                <button onClick={() => persist('personalize')} className="btn" style={{ padding: '12px 18px', borderRadius: 12, border: '1px solid var(--terra)', background: 'transparent', color: 'var(--terra-light)', fontWeight: 600, cursor: 'pointer' }}>👗 Personalise with my wardrobe</button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Sign-up modal (persistence trigger) ─────────────────────── */}
      {signupFor && (
        <div role="dialog" aria-modal="true" onClick={() => setSignupFor(null)}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.6)', display: 'grid', placeItems: 'center', padding: 20, zIndex: 50 }}>
          <div className="card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 380, padding: 26, textAlign: 'center', background: 'var(--surface, #161921)', borderRadius: 18 }}>
            <div style={{ fontSize: '1.8rem', marginBottom: 8 }}>{signupFor === 'personalize' ? '👗' : '💾'}</div>
            <h2 style={{ fontSize: '1.3rem', margin: '0 0 8px', fontWeight: 650 }}>
              {signupFor === 'personalize' ? 'Personalise it in one tap' : 'Keep this trip'}
            </h2>
            <p style={{ color: 'var(--dim)', fontSize: '.92rem', margin: '0 0 16px', lineHeight: 1.5 }}>
              Create a free account to save <b style={{ color: 'var(--cream)' }}>{form.destination || 'your trip'}</b>, tune it to your real closet, and pack with friends.
            </p>
            <button onClick={() => navigate('/login?mode=register')} className="btn btn-primary" style={{ width: '100%', padding: 14, borderRadius: 12, border: 'none', background: 'var(--terra)', color: '#fff', fontWeight: 600, cursor: 'pointer', marginBottom: 10 }}>Save my trip</button>
            <button onClick={() => navigate('/login')} className="btn" style={{ width: '100%', padding: 12, borderRadius: 12, border: '1px solid var(--border)', background: 'transparent', color: 'var(--dim)', cursor: 'pointer', marginBottom: 12 }}>I already have an account</button>
            <div style={{ fontFamily: 'var(--mono, monospace)', fontSize: '.72rem', color: 'var(--faint, #6b6a73)' }}>
              Your {form.destination || 'trip'} attaches automatically · free · no card
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
