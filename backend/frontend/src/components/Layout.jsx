// src/components/Layout.jsx
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'

const NAV = [
  { to: '/',               label: 'Today',    icon: '✦' },
  { to: '/wardrobe',       label: 'Wardrobe', icon: '◈' },
  { to: '/itinerary',      label: 'Schedule', icon: '◷' },
  { to: '/trips',          label: 'Trips',    icon: '◎' },
  { to: '/cultural',       label: 'Culture',  icon: '◉' },
  { to: '/calendar',        label: 'Calendar', icon: '⊙' },
  { to: '/sustainability',  label: 'Impact',   icon: '◆' },
  { to: '/profile',         label: 'Profile',  icon: '◌' },
]

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const initial = (user?.first_name?.[0] || user?.email?.[0] || '?').toUpperCase()

  return (
    <div className="app-shell">
      {/* ── Sidebar ────────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="wordmark">Arokah</div>
          <div style={{ fontSize:'0.7rem', letterSpacing:'0.1em', textTransform:'uppercase', color:'var(--terra)', marginTop:'4px' }}>
            AI Style Companion
          </div>
        </div>

        <nav className="sidebar-nav">
          {NAV.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              <span className="icon">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User chip + logout */}
        <div className="sidebar-footer">
          <div className="user-chip">
            <div className="user-avatar">{initial}</div>
            <div style={{ flex:1, minWidth:0 }}>
              <div className="user-name" style={{ overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                {user?.first_name || 'You'}
              </div>
              <div className="user-email" style={{ overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                {user?.email}
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="btn btn-ghost btn-icon btn-sm"
              style={{ marginLeft:'4px', flexShrink:0 }}
              title="Sign out"
            >
              ⎋
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main ───────────────────────────────────────────── */}
      <main className="main-content">
        {children}
      </main>
    </div>
  )
}
