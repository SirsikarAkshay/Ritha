// Observability: Sentry (errors/traces) + PostHog (product analytics).
//
// Both are gated on build-time env vars — if a key isn't set (e.g. local dev),
// the corresponding tool is a no-op, so nothing breaks and no data is sent.
// Configure in production via the static-site build env (see render.yaml):
//   VITE_SENTRY_DSN, VITE_POSTHOG_KEY, VITE_POSTHOG_HOST, VITE_APP_VERSION
import * as Sentry from '@sentry/react'
import posthog from 'posthog-js'

const env = import.meta.env ?? {}
const SENTRY_DSN   = env.VITE_SENTRY_DSN
const POSTHOG_KEY  = env.VITE_POSTHOG_KEY
const POSTHOG_HOST = env.VITE_POSTHOG_HOST || 'https://eu.i.posthog.com'
const RELEASE      = env.VITE_APP_VERSION || undefined
const ENVIRONMENT  = env.MODE || 'production'

let posthogReady = false

export function initObservability() {
  if (SENTRY_DSN) {
    Sentry.init({
      dsn: SENTRY_DSN,
      environment: ENVIRONMENT,
      release: RELEASE,
      integrations: [Sentry.browserTracingIntegration()],
      tracesSampleRate: 0.1,
      sendDefaultPii: false,   // don't attach IP/cookies; we set user id explicitly
    })
  }

  if (POSTHOG_KEY) {
    posthog.init(POSTHOG_KEY, {
      api_host: POSTHOG_HOST,
      capture_pageview: true,          // SPA route changes (history API) are auto-captured
      autocapture: true,
      person_profiles: 'identified_only',  // no profiles for anonymous visitors
      mask_all_text: false,
      // Don't record sensitive inputs if session replay is later enabled.
      session_recording: { maskAllInputs: true },
    })
    posthogReady = true
  }
}

// Safe no-ops when PostHog isn't configured.
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

// Re-export so callers can wrap routes/components in a Sentry error boundary.
export { Sentry }
