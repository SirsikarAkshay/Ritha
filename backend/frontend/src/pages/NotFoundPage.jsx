// src/pages/NotFoundPage.jsx
import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--midnight)',
      padding: '24px',
    }}>
      <div style={{ textAlign: 'center', maxWidth: '420px' }}>
        <div style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', color: 'var(--cream)', letterSpacing: '-0.02em', marginBottom: '8px' }}>
          Arokah
        </div>
        <div style={{ fontFamily: 'var(--font-display)', fontSize: '6rem', color: 'var(--terra)', lineHeight: 1, margin: '24px 0 8px' }}>
          404
        </div>
        <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', color: 'var(--cream)', marginBottom: '12px' }}>
          Page not found
        </div>
        <p style={{ color: 'var(--cream-dim)', fontSize: '0.875rem', lineHeight: 1.6, marginBottom: '32px' }}>
          This page doesn't exist or has moved.
        </p>
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
          <Link to="/" className="btn btn-primary">Go to dashboard</Link>
          <button className="btn btn-ghost" onClick={() => window.history.back()}>← Go back</button>
        </div>
      </div>
    </div>
  )
}
