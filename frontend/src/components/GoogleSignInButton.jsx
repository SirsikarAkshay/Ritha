// src/components/GoogleSignInButton.jsx
// Renders Google Identity Services' official button and exchanges the returned
// ID token for our JWT via useAuth().loginWithGoogle. Renders nothing when
// VITE_GOOGLE_CLIENT_ID isn't configured, so the app is unaffected until you
// set it at build time.
import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'

const CLIENT_ID = import.meta.env?.VITE_GOOGLE_CLIENT_ID || ''
const GSI_SRC = 'https://accounts.google.com/gsi/client'

// Load the GSI script once, shared across mounts.
let gsiPromise = null
function loadGsi() {
  if (gsiPromise) return gsiPromise
  gsiPromise = new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) return resolve()
    const s = document.createElement('script')
    s.src = GSI_SRC
    s.async = true
    s.defer = true
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('gsi-load-failed'))
    document.head.appendChild(s)
  })
  return gsiPromise
}

export default function GoogleSignInButton({ onError }) {
  const ref = useRef(null)
  const { loginWithGoogle } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!CLIENT_ID) return
    let cancelled = false
    loadGsi()
      .then(() => {
        if (cancelled || !window.google?.accounts?.id || !ref.current) return
        window.google.accounts.id.initialize({
          client_id: CLIENT_ID,
          callback: async (resp) => {
            try {
              await loginWithGoogle(resp.credential)
              navigate('/')
            } catch (e) {
              onError?.(
                e?.response?.data?.error?.message ||
                  'Google sign-in failed. Please try again.',
              )
            }
          },
        })
        window.google.accounts.id.renderButton(ref.current, {
          theme: 'outline',
          size: 'large',
          text: 'continue_with',
          shape: 'pill',
          width: 320,
          logo_alignment: 'center',
        })
      })
      .catch(() => onError?.('Could not load Google sign-in.'))
    return () => {
      cancelled = true
    }
  }, [loginWithGoogle, navigate, onError])

  if (!CLIENT_ID) return null
  return <div ref={ref} style={{ display: 'flex', justifyContent: 'center' }} />
}
