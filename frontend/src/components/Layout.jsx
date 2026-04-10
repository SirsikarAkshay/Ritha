// src/components/Layout.jsx
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import { useTheme } from '../hooks/useTheme.jsx'
import Logo from './Logo.jsx'

const NAV = [
  { to: '/',               label: 'Today',    icon: '✦' },
  { to: '/wardrobe',       label: 'Wardrobe', icon: '◈' },
  { to: '/itinerary',      label: 'Schedule', icon: '◷' },
  { to: '/trips',          label: 'Trips',    icon: '◎' },
  { to: '/recommend',      label: 'Recommend', icon: '✧' },
  { to: '/cultural',       label: 'Culture',  icon: '◉' },
  { to: '/sustainability',  label: 'Impact',   icon: '◆' },
  { to: '/people',          label: 'People',   icon: '◐' },
  { to: '/messages',        label: 'Messages', icon: '◍' },
  { to: '/shared-wardrobes', label: 'Shared',  icon: '◑' },
  { to: '/profile',         label: 'Profile',  icon: '◌' },
]

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
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
          <Logo style={{ height:'72px', width:'auto', display:'block', maxWidth:'100%' }} />
          <div style={{ fontSize:'0.7rem', letterSpacing:'0.1em', textTransform:'uppercase', color:'var(--terra)', marginTop:'10px' }}>
            Your wardrobe assistant
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

        {/* Theme toggle — prominent row */}
        <div style={{ padding:'0 16px 12px' }}>
          <button
            onClick={toggleTheme}
            aria-label="Toggle theme"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            style={{
              width:'100%',
              display:'flex',
              alignItems:'center',
              justifyContent:'space-between',
              gap:'12px',
              padding:'10px 14px',
              background:'var(--surface-2)',
              border:'1px solid var(--border)',
              borderRadius:'10px',
              color:'var(--cream)',
              cursor:'pointer',
              fontSize:'0.8125rem',
              fontFamily:'var(--font-body)',
              transition:'background var(--transition), border-color var(--transition)',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-3)'; e.currentTarget.style.borderColor = 'var(--border-hover)' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'var(--surface-2)'; e.currentTarget.style.borderColor = 'var(--border)' }}
          >
            <span style={{ display:'flex', alignItems:'center', gap:'10px' }}>
              <span style={{ fontSize:'1.1rem', lineHeight:1 }}>{theme === 'dark' ? '☾' : '☀'}</span>
              <span>{theme === 'dark' ? 'Dark mode' : 'Light mode'}</span>
            </span>
            <span
              aria-hidden="true"
              style={{
                position:'relative',
                width:'32px',
                height:'18px',
                borderRadius:'999px',
                background: theme === 'dark' ? 'var(--terra)' : 'var(--surface-3)',
                transition:'background var(--transition)',
                flexShrink:0,
              }}
            >
              <span style={{
                position:'absolute',
                top:'2px',
                left: theme === 'dark' ? '16px' : '2px',
                width:'14px',
                height:'14px',
                borderRadius:'50%',
                background:'var(--cream)',
                transition:'left var(--transition)',
              }} />
            </span>
          </button>
        </div>

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
