// Observability: Sentry (errors/traces) + PostHog (product analytics).
//
// Both are gated on build-time env vars — if a key isn't set (e.g. local dev),
// the tool is a no-op, so nothing breaks and no data is sent. Configure in
// production via the static-site build env (see render.yaml):
//   VITE_SENTRY_DSN, VITE_POSTHOG_KEY, VITE_POSTHOG_HOST, VITE_APP_VERSION
//
// Consent: Sentry (diagnostic, no PII) runs under legitimate interest. PostHog
// identifies users and uses cookies, so it only initialises AFTER the user
// opts in via the consent banner (GDPR/Swiss FADP). Until then, no PostHog
// network call or cookie is made.
import * as Sentry from '@sentry/react'
import posthog from 'posthog-js'

const env = import.meta.env ?? {}
const SENTRY_DSN   = env.VITE_SENTRY_DSN
const POSTHOG_KEY  = env.VITE_POSTHOG_KEY
const POSTHOG_HOST = env.VITE_POSTHOG_HOST || 'https://eu.i.posthog.com'
const RELEASE      = env.VITE_APP_VERSION || undefined
const ENVIRONMENT  = env.MODE || 'production'

const CONSENT_KEY = 'ritha_analytics_consent'   // 'accepted' | 'declined' | null

let posthogReady = false

// True when analytics is configured at all — the banner only shows then.
export const analyticsConfigured = Boolean(POSTHOG_KEY)

export function getAnalyticsConsent() {
  try { return localStorage.getItem(CONSENT_KEY) } catch { return null }
}

function initPosthog() {
  if (posthogReady || !POSTHOG_KEY) return
  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    capture_pageview: true,               // SPA route changes are auto-captured
    autocapture: true,
    person_profiles: 'identified_only',   // no profiles for anonymous visitors
    session_recording: { maskAllInputs: true },
  })
  posthogReady = true
}

export function grantAnalyticsConsent() {
  try { localStorage.setItem(CONSENT_KEY, 'accepted') } catch { /* ignore */ }
  initPosthog()
}

export function denyAnalyticsConsent() {
  try { localStorage.setItem(CONSENT_KEY, 'declined') } catch { /* ignore */ }
  posthogReady = false
}

export function initObservability() {
  if (SENTRY_DSN) {
    Sentry.init({
      dsn: SENTRY_DSN,
      environment: ENVIRONMENT,
      release: RELEASE,
      integrations: [Sentry.browserTracingIntegration()],
      tracesSampleRate: 0.1,
      sendDefaultPii: false,
    })
  }
  // Only start PostHog if the user opted in on a previous visit.
  if (getAnalyticsConsent() === 'accepted') initPosthog()
}

// Safe no-ops when PostHog isn't initialised (not configured, or no consent yet).
export const analytics = {
  identify(user) {
    if (!user) return
    if (posthogReady) posthog.identify(String(user.id), { email: user.email })
    if (SENTRY_DSN) Sentry.setUser({ id: String(user.id), email: user.email })
  },
  reset() {
    if (posthogReady) posthog.reset()
    if (SENTRY_DSN) Sentry.setUser(null)
  },
  capture(event, props) {
    if (posthogReady) posthog.capture(event, props)
  },
}

export { Sentry }
