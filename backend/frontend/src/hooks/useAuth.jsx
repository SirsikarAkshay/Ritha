// src/hooks/useAuth.jsx
import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { auth as authApi } from '../api/index.js'
import { api } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null)
  const [loading, setLoading] = useState(true)

  const loadUser = useCallback(async () => {
    if (!localStorage.getItem('gg_access')) { setLoading(false); return }
    try {
      const me = await authApi.me()
      setUser(me)
    } catch {
      api.clearTokens()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadUser() }, [loadUser])

  const login = async (email, password) => {
    // Throws on 401 (wrong creds) or 403 (unverified) — let LoginPage handle it
    const data = await authApi.login({ email, password })
    api.setTokens(data.access, data.refresh)
    const me = await authApi.me()
    setUser(me)
    return me
  }

  const logout = async () => {
    const refresh = localStorage.getItem('gg_refresh')
    try { if (refresh) await authApi.logout(refresh) } catch {}
    api.clearTokens()
    setUser(null)
  }

  const updateUser = (updates) => setUser(u => ({ ...u, ...updates }))

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, updateUser, reload: loadUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
