// Cookie/analytics consent banner. Shows once (until the user chooses) when
// analytics is configured and no choice is stored. "Accept" opts the user into
// PostHog; "Decline" keeps it off. Sentry error monitoring is unaffected.
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import {
  analyticsConfigured, getAnalyticsConsent,
  grantAnalyticsConsent, denyAnalyticsConsent, analytics,
} from '../observability.js'

export default function ConsentBanner() {
  const { user } = useAuth()
  const [visible, setVisible] = useState(
    () => analyticsConfigured && getAnalyticsConsent() === null
  )
  if (!visible) return null

  const accept = () => {
    grantAnalyticsConsent()
    if (user) analytics.identify(user)   // user may already be signed in
    setVisible(false)
  }
  const decline = () => {
    denyAnalyticsConsent()
    setVisible(false)
  }

  return (
    <div role="dialog" aria-label="Analytics consent" style={{
      position: 'fixed', left: 16, right: 16, bottom: 16, zIndex: 1000,
      maxWidth: 720, margin: '0 auto', padding: '16px 20px',
      background: 'var(--midnight-light, #1d2433)', color: 'var(--cream)',
      border: '1px solid var(--terra)', borderRadius: 12,
      boxShadow: '0 8px 30px rgba(0,0,0,0.35)',
      display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 12,
    }}>
      <p style={{ flex: '1 1 280px', margin: 0, fontSize: '0.9rem', lineHeight: 1.5 }}>
        We use privacy-friendly analytics to understand how Ritha is used and improve it.
        You can decline without affecting the app. See our{' '}
        <Link to="/privacy" style={{ color: 'var(--terra-light)' }}>Privacy Policy</Link>.
      </p>
      <div style={{ display: 'flex', gap: 8 }}>
        <button onClick={decline} className="btn" style={{
          background: 'transparent', color: 'var(--cream)',
          border: '1px solid var(--cream-dim)', padding: '8px 16px', borderRadius: 8, cursor: 'pointer',
        }}>Decline</button>
        <button onClick={accept} className="btn btn-primary" style={{ padding: '8px 16px' }}>
          Accept
        </button>
      </div>
    </div>
  )
}
