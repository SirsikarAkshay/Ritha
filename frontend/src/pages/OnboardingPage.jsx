// src/pages/OnboardingPage.jsx
//
// Three-step starter-pack onboarding:
//   1. Pick demographic (gender) + region
//   2. Optional: opt-in to traditional / modest / observant items
//   3. Review the proposed pack — remove anything that doesn't fit, add custom
//
// Each item card carries a "?" tooltip showing the prevalence stat and source
// citation (e.g. "Owned by 89% of urban Indian women — NSS Round 75, 2018").
// This transparency is the trust mechanism: users accept defaults more readily
// when they see why those defaults were chosen.

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { wardrobe } from '../api/index.js'
import { useAuth } from '../hooks/useAuth.jsx'

const GENDER_OPTIONS = [
  { value: 'women',     label: 'Women',     hint: 'Adult' },
  { value: 'men',       label: 'Men',       hint: 'Adult' },
  { value: 'girls',     label: 'Girls',     hint: 'Teen / young adult' },
  { value: 'boys',      label: 'Boys',      hint: 'Teen / young adult' },
  { value: 'kid_girls', label: 'Kid girls', hint: 'Child (3–12)' },
  { value: 'kid_boys',  label: 'Kid boys',  hint: 'Child (3–12)' },
]

// Hint shown next to each region in the picker. Keyed by RegionCluster.code.
// Falls back to the climate_zone string if a region isn't here yet.
const REGION_HINTS = {
  na_temperate:         'US, Canada',
  nw_temperate:         'UK, EU, Switzerland',
  south_asian_tropical: 'India, Bangladesh, Sri Lanka',
  mena_arid:            'Gulf, Egypt, Morocco',
  east_asian_subtropical:'Thailand, Vietnam, Philippines',
  latam_tropical:       'Brazil, Mexico (coast), Colombia',
}

const OPT_IN_LABELS = {
  traditional: { title: 'Traditional / cultural attire',
                 detail: 'Adds region-specific traditional items (saree, lehenga, sherwani, dhoti…)' },
  modest_dress: { title: 'Modest dress',
                  detail: 'Adds long tunics, abaya-friendly layers, modest swim/activewear' },
  observant_jewish: { title: 'Observant religious dress (Jewish)',
                      detail: 'Adds kippah, tzitzit, modest options' },
  observant_muslim: { title: 'Observant religious dress (Muslim)',
                      detail: 'Adds hijab, abaya, prayer cap' },
}

const CAT_ICON = {
  top: '👕', bottom: '👖', dress: '👗', outerwear: '🧥',
  footwear: '👟', accessory: '👜', activewear: '🏃',
  formal: '🤵', other: '📦',
}

// Categories with a bundled default SVG at /wardrobe-defaults/<cat>.svg.
// Anything outside this set falls back to /wardrobe-defaults/other.svg.
const SVG_CATEGORIES = new Set([
  'top', 'bottom', 'dress', 'outerwear', 'footwear',
  'accessory', 'activewear', 'formal', 'other',
])

function categoryDefaultImage(category) {
  return `/wardrobe-defaults/${SVG_CATEGORIES.has(category) ? category : 'other'}.svg`
}

export default function OnboardingPage() {
  const navigate = useNavigate()
  const { user, reload } = useAuth()

  const [step, setStep]       = useState(1)        // 1=demographic, 2=opt-ins, 3=review
  const [gender, setGender]   = useState(user?.gender || '')
  const [region, setRegion]   = useState('')
  const [regions, setRegions] = useState([])       // [{code, display_name, ...}]
  const [optIns, setOptIns]   = useState([])

  // Load the region catalogue + server's suggestion (timezone-derived) on mount.
  useEffect(() => {
    wardrobe.starterPack.regions()
      .then(({ regions, suggested_region }) => {
        setRegions(regions || [])
        if (suggested_region && !region) setRegion(suggested_region)
      })
      .catch(() => { /* fall back to empty picker; user can still skip */ })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const [preview, setPreview] = useState(null)     // { region, gender, items, opt_in_groups }
  const [removedIds, setRemovedIds] = useState(new Set())
  const [customAdded, setCustomAdded] = useState([])
  const [customDraft, setCustomDraft] = useState({ name: '', category: 'top' })

  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Already onboarded? Bounce to dashboard.
  useEffect(() => {
    if (user?.has_completed_onboarding) navigate('/', { replace: true })
  }, [user, navigate])

  // Load preview when entering step 3
  useEffect(() => {
    if (step !== 3 || !region || !gender) return
    setLoading(true); setError('')
    wardrobe.starterPack.preview({ region, gender })
      .then(data => {
        setPreview(data)
        setRemovedIds(new Set())
      })
      .catch(e => setError(e?.message || 'Could not load starter pack'))
      .finally(() => setLoading(false))
  }, [step, region, gender])

  const visibleItems = preview?.items?.filter(it => {
    if (it.is_default) return true
    if (it.is_opt_in && optIns.includes(it.opt_in_group)) return true
    return false
  }) || []
  const keptItems = visibleItems.filter(it => !removedIds.has(it.id))

  function toggleRemove(id) {
    setRemovedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  function addCustom() {
    if (!customDraft.name.trim()) return
    setCustomAdded(prev => [...prev, { ...customDraft, name: customDraft.name.trim() }])
    setCustomDraft({ name: '', category: customDraft.category })
  }

  function removeCustom(idx) {
    setCustomAdded(prev => prev.filter((_, i) => i !== idx))
  }

  async function submit() {
    setSubmitting(true); setError('')
    try {
      const accepted_ids = keptItems.map(it => it.id)
      const rejected_ids = visibleItems.filter(it => removedIds.has(it.id)).map(it => it.id)
      await wardrobe.starterPack.apply({
        region_code: region, gender,
        accepted_ids, rejected_ids,
        opt_ins: optIns,
        custom_added: customAdded,
      })
      await reload?.()
      navigate('/wardrobe', { replace: true })
    } catch (e) {
      setError(e?.message || 'Could not save your wardrobe')
      setSubmitting(false)
    }
  }

  const stepHeader = (
    <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginBottom: 32 }}>
      {[1, 2, 3].map(n => (
        <div key={n} style={{
          width: 32, height: 4, borderRadius: 2,
          background: n <= step ? 'var(--terra)' : 'var(--midnight-700)',
        }} />
      ))}
    </div>
  )

  // ── Step 1: demographic + region ─────────────────────────────────────────
  if (step === 1) {
    return (
      <div style={pageWrap}>
        {stepHeader}
        <h1 style={h1}>Let's set up your wardrobe</h1>
        <p style={subtitle}>We'll start with a few items most people in your demographic own — based on real survey data, not guesses. You'll review and remove anything that doesn't fit.</p>

        <h2 style={h2}>I'm shopping for…</h2>
        <div style={grid}>
          {GENDER_OPTIONS.map(opt => (
            <button key={opt.value}
              onClick={() => setGender(opt.value)}
              style={{ ...optionBtn, ...(gender === opt.value ? optionBtnActive : {}) }}>
              <div style={{ fontSize: 16, fontWeight: 600 }}>{opt.label}</div>
              <div style={{ fontSize: 12, color: 'var(--cream-700)', marginTop: 4 }}>{opt.hint}</div>
            </button>
          ))}
        </div>

        <h2 style={{ ...h2, marginTop: 32 }}>I mostly live in…</h2>
        <div style={grid}>
          {regions.length === 0 && (
            <div style={{ gridColumn: '1 / -1', color: 'var(--cream-700)', fontSize: 13 }}>
              Loading regions…
            </div>
          )}
          {regions.map(r => (
            <button key={r.code}
              onClick={() => setRegion(r.code)}
              style={{ ...optionBtn, ...(region === r.code ? optionBtnActive : {}) }}>
              <div style={{ fontSize: 16, fontWeight: 600 }}>{r.display_name}</div>
              <div style={{ fontSize: 12, color: 'var(--cream-700)', marginTop: 4 }}>
                {REGION_HINTS[r.code] || r.climate_zone}
              </div>
            </button>
          ))}
        </div>

        <div style={footerBar}>
          <button onClick={() => {
                    // Skip path: stash a localStorage flag so ProtectedRoute lets
                    // them through. They can return via /onboarding any time.
                    localStorage.setItem('ritha_onboarding_skipped', '1')
                    navigate('/')
                  }}
                  style={skipBtn}>Skip — I'll add manually</button>
          <button disabled={!gender || !region}
                  onClick={() => setStep(2)}
                  style={primaryBtn}>Continue</button>
        </div>
      </div>
    )
  }

  // ── Step 2: opt-ins (traditional / modest / religious) ───────────────────
  if (step === 2) {
    return (
      <div style={pageWrap}>
        {stepHeader}
        <h1 style={h1}>Anything to add?</h1>
        <p style={subtitle}>These are <strong>off by default</strong>. Tick only what applies — your wardrobe is private and these never appear unless you opt in here.</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {Object.entries(OPT_IN_LABELS).map(([key, meta]) => (
            <label key={key} style={{
              ...optionBtn,
              display: 'flex', flexDirection: 'row', alignItems: 'flex-start', gap: 12,
              cursor: 'pointer', textAlign: 'left',
              ...(optIns.includes(key) ? optionBtnActive : {}),
            }}>
              <input type="checkbox"
                     checked={optIns.includes(key)}
                     onChange={(e) => setOptIns(prev =>
                       e.target.checked ? [...prev, key] : prev.filter(x => x !== key))}
                     style={{ marginTop: 4 }} />
              <div>
                <div style={{ fontWeight: 600 }}>{meta.title}</div>
                <div style={{ fontSize: 13, color: 'var(--cream-700)', marginTop: 2 }}>{meta.detail}</div>
              </div>
            </label>
          ))}
        </div>

        <div style={footerBar}>
          <button onClick={() => setStep(1)} style={skipBtn}>Back</button>
          <button onClick={() => setStep(3)} style={primaryBtn}>See my starter pack →</button>
        </div>
      </div>
    )
  }

  // ── Step 3: review ───────────────────────────────────────────────────────
  return (
    <div style={pageWrap}>
      {stepHeader}
      <h1 style={h1}>Your starter wardrobe</h1>
      <p style={subtitle}>
        {keptItems.length} item{keptItems.length === 1 ? '' : 's'} selected
        {customAdded.length > 0 && ` + ${customAdded.length} custom`}.
        Tap any card's <strong>×</strong> to remove. Tap <strong>?</strong> to see why we suggested it.
      </p>

      {loading && <div style={{ textAlign: 'center', padding: 40 }}>Loading…</div>}
      {error && <div style={errorBox}>{error}</div>}

      {!loading && preview && (
        <>
          <div style={cardGrid}>
            {visibleItems.map(it => {
              const removed = removedIds.has(it.id)
              return (
                <div key={it.id} style={{ ...itemCard, ...(removed ? itemCardRemoved : {}) }}>
                  <div style={imageWrap}>
                    <img
                      src={it.preview_image_url || categoryDefaultImage(it.category)}
                      alt={it.display_name}
                      loading="lazy"
                      style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 16 }}
                      onError={(e) => {
                        // Bad/dead URL — fall back to the bundled category SVG.
                        const fallback = categoryDefaultImage(it.category)
                        if (e.currentTarget.src.endsWith(fallback)) return
                        e.currentTarget.src = fallback
                      }}
                    />
                    <button onClick={() => toggleRemove(it.id)}
                            title={removed ? 'Add back' : 'Remove'}
                            style={removeBtn}>
                      {removed ? '↩' : '×'}
                    </button>
                  </div>
                  <div style={{ padding: '10px 12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                      <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--cream)' }}>{it.display_name}</div>
                      <SourceTooltip item={it} />
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--cream-700)', marginTop: 4, textTransform: 'capitalize' }}>
                      {(it.default_colors || []).join(', ')} · {it.seasonality === 'all' ? 'all season' : it.seasonality}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Custom add */}
          <div style={customSection}>
            <div style={{ fontSize: 13, color: 'var(--cream-700)', marginBottom: 8 }}>Anything we missed?</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <input value={customDraft.name}
                     onChange={(e) => setCustomDraft(d => ({ ...d, name: e.target.value }))}
                     placeholder="e.g. Saree, running shorts, gym shoes"
                     onKeyDown={(e) => e.key === 'Enter' && addCustom()}
                     style={input} />
              <select value={customDraft.category}
                      onChange={(e) => setCustomDraft(d => ({ ...d, category: e.target.value }))}
                      style={{ ...input, maxWidth: 140 }}>
                {Object.keys(CAT_ICON).map(c => (
                  <option key={c} value={c}>{CAT_ICON[c]} {c}</option>
                ))}
              </select>
              <button onClick={addCustom} disabled={!customDraft.name.trim()} style={addBtn}>+ Add</button>
            </div>
            {customAdded.length > 0 && (
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 12 }}>
                {customAdded.map((c, i) => (
                  <span key={i} style={chip}>
                    {CAT_ICON[c.category]} {c.name}
                    <button onClick={() => removeCustom(i)} style={chipRemove}>×</button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      <div style={footerBar}>
        <button onClick={() => setStep(2)} style={skipBtn}>Back</button>
        <button onClick={submit} disabled={submitting || loading}
                style={primaryBtn}>
          {submitting ? 'Adding to wardrobe…' : `Add ${keptItems.length + customAdded.length} items to my wardrobe`}
        </button>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Tooltip — the transparency mechanism. Shows the prevalence stat + source.
// ─────────────────────────────────────────────────────────────────────────────
function SourceTooltip({ item }) {
  const [open, setOpen] = useState(false)
  const stat = item.prevalence_pct ? `${item.prevalence_pct}% own this` : 'Common item'
  const conf = item.confidence === 'high' ? '✓ High-confidence data'
            : item.confidence === 'medium' ? '~ Medium confidence'
            : '! Low confidence — limited data for this demographic'
  return (
    <div style={{ position: 'relative' }}>
      <button onClick={() => setOpen(o => !o)} onBlur={() => setTimeout(() => setOpen(false), 150)}
              style={infoBtn} title="Why is this in my pack?">?</button>
      {open && (
        <div style={tooltip} onClick={(e) => e.stopPropagation()}>
          <div style={{ fontWeight: 700, fontSize: 13 }}>{stat}</div>
          <div style={{ fontSize: 11, marginTop: 6, color: 'var(--cream-700)' }}>
            Source: {item.source_label}{item.source_year ? `, ${item.source_year}` : ''}
          </div>
          <div style={{ fontSize: 11, marginTop: 4, color: 'var(--cream-700)' }}>{conf}</div>
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Inline styles — matches the rest of the app's dark/cream/terra palette.
// ─────────────────────────────────────────────────────────────────────────────
const pageWrap = {
  maxWidth: 920, margin: '0 auto', padding: '40px 20px',
  color: 'var(--cream)', minHeight: '100vh',
}
const h1 = { fontFamily: 'var(--font-display)', fontSize: 32, fontWeight: 700, textAlign: 'center', marginBottom: 8 }
const h2 = { fontSize: 16, fontWeight: 600, marginTop: 0, marginBottom: 16, color: 'var(--cream-700)' }
const subtitle = { textAlign: 'center', color: 'var(--cream-700)', marginBottom: 32, lineHeight: 1.5 }
const grid = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12 }
const optionBtn = {
  padding: '16px 14px', borderRadius: 12, background: 'var(--midnight-800)',
  border: '1px solid var(--midnight-600)', cursor: 'pointer', textAlign: 'center',
  color: 'var(--cream)', transition: 'all 0.15s ease',
}
const optionBtnActive = { borderColor: 'var(--terra)', background: 'rgba(220,90,60,0.12)' }
const footerBar = {
  display: 'flex', justifyContent: 'space-between', gap: 12, marginTop: 40,
  borderTop: '1px solid var(--midnight-700)', paddingTop: 24,
}
const primaryBtn = {
  padding: '12px 24px', background: 'var(--terra)', color: 'white',
  border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600,
}
const skipBtn = {
  padding: '12px 16px', background: 'transparent', color: 'var(--cream-700)',
  border: '1px solid var(--midnight-600)', borderRadius: 8, cursor: 'pointer',
}
const cardGrid = {
  display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12, marginTop: 16,
}
const itemCard = {
  background: 'var(--midnight-800)', borderRadius: 12, overflow: 'hidden',
  border: '1px solid var(--midnight-600)', position: 'relative',
}
const itemCardRemoved = { opacity: 0.4, borderStyle: 'dashed' }
const imageWrap = {
  position: 'relative', width: '100%', aspectRatio: '1 / 1', background: 'var(--midnight-700)',
  display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
}
const iconFallback = { fontSize: 56 }
const removeBtn = {
  position: 'absolute', top: 8, right: 8, width: 28, height: 28,
  background: 'rgba(0,0,0,0.7)', color: 'white',
  border: 'none', borderRadius: '50%', cursor: 'pointer',
  fontSize: 16, fontWeight: 700, lineHeight: 1,
}
const infoBtn = {
  width: 22, height: 22, borderRadius: '50%', background: 'var(--midnight-700)',
  color: 'var(--cream-700)', border: '1px solid var(--midnight-600)',
  cursor: 'pointer', fontSize: 12, fontWeight: 700,
}
const tooltip = {
  position: 'absolute', right: 0, top: 28, width: 240, padding: 12,
  background: 'var(--midnight-900)', border: '1px solid var(--terra)', borderRadius: 8,
  zIndex: 10, color: 'var(--cream)',
  boxShadow: '0 4px 16px rgba(0,0,0,0.6)',
}
const customSection = {
  marginTop: 32, padding: 16, background: 'var(--midnight-800)',
  border: '1px solid var(--midnight-600)', borderRadius: 12,
}
const input = {
  flex: 1, minWidth: 200, padding: '10px 12px', background: 'var(--midnight-900)',
  border: '1px solid var(--midnight-600)', borderRadius: 6, color: 'var(--cream)',
}
const addBtn = {
  padding: '10px 16px', background: 'var(--midnight-700)', color: 'var(--cream)',
  border: '1px solid var(--midnight-600)', borderRadius: 6, cursor: 'pointer', fontWeight: 600,
}
const chip = {
  display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 10px',
  background: 'var(--midnight-700)', borderRadius: 999, fontSize: 13,
}
const chipRemove = {
  background: 'transparent', border: 'none', color: 'var(--cream-700)',
  cursor: 'pointer', fontSize: 14, lineHeight: 1, padding: 0,
}
const errorBox = {
  background: 'rgba(220,70,60,0.12)', color: '#ff8a80',
  border: '1px solid rgba(220,70,60,0.3)', borderRadius: 8,
  padding: 12, marginBottom: 16,
}
