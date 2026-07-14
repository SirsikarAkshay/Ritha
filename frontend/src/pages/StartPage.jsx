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
  const [form, setForm] = useState({ destination: '', place: null, date: '', gender: 'women' })
  const [insights, setInsights] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [signupFor, setSignupFor] = useState(null) // persistence-trigger label, or null

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
        <h1 style={{ fontSize: 'clamp(1.9rem,5vw,3rem)', lineHeight: 1.05, letterSpacing: '-.03em', fontWeight: 680, margin: 0, textWrap: 'balance' }}>
          Where are you <span style={{ color: 'var(--terra, #d4724a)' }}>headed?</span>
        </h1>
        <p style={{ color: 'var(--dim, #9a97a0)', fontSize: '1.05rem', margin: '14px 0 24px', maxWidth: '48ch', lineHeight: 1.55 }}>
          Type a destination — get the weather, the local dress code, must-see places, and exactly what to pack (and buy). No sign-up needed.
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
            <input type="date" value={form.date} onChange={set('date')} aria-label="Trip date"
              style={{ flex: '1 1 150px', padding: '12px 14px', borderRadius: 12, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--cream)', colorScheme: 'dark' }} />
            <select value={form.gender} onChange={set('gender')} aria-label="Style"
              style={{ flex: '1 1 120px', padding: '12px 14px', borderRadius: 12, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--cream)' }}>
              <option value="women">Women's</option><option value="men">Men's</option><option value="kids">Kids'</option>
            </select>
          </div>
          <button type="submit" disabled={loading || !form.destination.trim()} className="btn btn-primary"
            style={{ padding: 15, fontSize: '1.05rem', fontWeight: 600, borderRadius: 13, border: 'none', cursor: 'pointer', background: 'var(--terra, #d4724a)', color: '#fff', opacity: loading ? 0.7 : 1 }}>
            {loading ? 'Reading the forecast…' : '✦ See my instant plan'}
          </button>
          {error && <div style={{ color: 'var(--danger, #e0745c)', fontSize: '.9rem' }}>{error}</div>}
        </form>

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
              <div style={{ color: 'var(--gold, #c9a84c)', fontSize: '.8rem', marginBottom: 12, fontStyle: 'italic' }}>{insights.capsule_note}</div>
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
              <div style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: 6 }}>Make it yours</div>
              <div style={{ color: 'var(--dim)', fontSize: '.9rem', marginBottom: 14 }}>Save this trip, personalise the capsule with your own wardrobe, or invite friends to pack it together.</div>
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
              {signupFor === 'personalize' ? 'Personalise it in one tap' : 'Save your trip'}
            </h2>
            <p style={{ color: 'var(--dim)', fontSize: '.92rem', margin: '0 0 18px', lineHeight: 1.5 }}>
              Create a free account and we'll keep <b style={{ color: 'var(--cream)' }}>{form.destination}</b> ready for you — your plan is already saved.
            </p>
            <button onClick={() => navigate('/register')} className="btn btn-primary" style={{ width: '100%', padding: 14, borderRadius: 12, border: 'none', background: 'var(--terra)', color: '#fff', fontWeight: 600, cursor: 'pointer', marginBottom: 10 }}>Create free account →</button>
            <button onClick={() => navigate('/login')} className="btn" style={{ width: '100%', padding: 12, borderRadius: 12, border: '1px solid var(--border)', background: 'transparent', color: 'var(--dim)', cursor: 'pointer' }}>I already have an account</button>
          </div>
        </div>
      )}
    </div>
  )
}
