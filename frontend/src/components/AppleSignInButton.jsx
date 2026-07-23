// src/components/AppleSignInButton.jsx
// Runs Sign in with Apple (popup) and exchanges the returned ID token for our
// JWT via useAuth().loginWithApple. Apple only returns the user's name on the
// first authorization, so we forward it when present. Renders nothing unless
// VITE_APPLE_CLIENT_ID (an Apple Services ID) is configured at build time.
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'

const CLIENT_ID = import.meta.env?.VITE_APPLE_CLIENT_ID || ''
const REDIRECT_URI = import.meta.env?.VITE_APPLE_REDIRECT_URI || ''
const APPLE_SRC =
  'https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js'

let applePromise = null
function loadApple() {
  if (applePromise) return applePromise
  applePromise = new Promise((resolve, reject) => {
    if (window.AppleID?.auth) return resolve()
    const s = document.createElement('script')
    s.src = APPLE_SRC
    s.async = true
    s.defer = true
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('apple-load-failed'))
    document.head.appendChild(s)
  })
  return applePromise
}

function AppleLogo() {
  return (
    <svg width="16" height="16" viewBox="0 0 384 512" fill="currentColor" aria-hidden="true">
      <path d="M318.7 268.7c-.2-36.7 16.4-64.4 50-84.8-18.8-26.9-47.2-41.7-84.7-44.6-35.5-2.8-74.3 20.7-88.5 20.7-15 0-49.4-19.7-76.4-19.7C63.3 141.2 4 184.8 4 273.5q0 39.3 14.4 81.2c12.8 36.7 59 126.7 107.2 125.2 25.2-.6 43-17.9 75.8-17.9 31.8 0 48.3 17.9 76.4 17.9 48.6-.7 90.4-82.5 102.6-119.3-65.2-30.7-61.7-90-61.7-91.9zm-56.6-164.2c27.3-32.4 24.8-61.9 24-72.5-24.1 1.4-52 16.4-67.9 34.9-17.5 19.8-27.8 44.3-25.6 71.9 26.1 2 49.9-11.4 69.5-34.3z" />
    </svg>
  )
}

export default function AppleSignInButton({ onError }) {
  const { loginWithApple } = useAuth()
  const navigate = useNavigate()
  const [ready, setReady] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!CLIENT_ID) return
    let cancelled = false
    loadApple()
      .then(() => {
        if (cancelled || !window.AppleID?.auth) return
        window.AppleID.auth.init({
          clientId: CLIENT_ID,
          scope: 'name email',
          redirectURI: REDIRECT_URI,
          usePopup: true,
        })
        setReady(true)
      })
      .catch(() => onError?.('Could not load Apple sign-in.'))
    return () => {
      cancelled = true
    }
  }, [onError])

  const handleClick = async () => {
    if (!ready || busy) return
    setBusy(true)
    try {
      const res = await window.AppleID.auth.signIn()
      const idToken = res?.authorization?.id_token
      if (!idToken) throw new Error('no-token')
      const name = res?.user?.name || {}
      await loginWithApple(idToken, name.firstName || '', name.lastName || '')
      navigate('/')
    } catch (e) {
      // Apple throws {error:'popup_closed_by_user'} on cancel — don't surface it.
      if (e?.error !== 'popup_closed_by_user') {
        onError?.(
          e?.response?.data?.error?.message ||
            'Apple sign-in failed. Please try again.',
        )
      }
    } finally {
      setBusy(false)
    }
  }

  if (!CLIENT_ID) return null
  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={!ready || busy}
      style={{
        width: '320px',
        maxWidth: '100%',
        height: '40px',
        margin: '0 auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px',
        borderRadius: '999px',
        border: 'none',
        background: '#000',
        color: '#fff',
        fontSize: '0.9rem',
        fontWeight: 500,
        cursor: ready && !busy ? 'pointer' : 'default',
        opacity: ready ? 1 : 0.6,
      }}
    >
      <AppleLogo />
      {busy ? 'Signing in…' : 'Continue with Apple'}
    </button>
  )
}
