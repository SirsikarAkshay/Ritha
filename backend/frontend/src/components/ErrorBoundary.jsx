// src/components/ErrorBoundary.jsx
import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('Arokah UI error:', error, info)
  }

  render() {
    if (this.state.hasError) {
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
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', color: 'var(--cream)', marginBottom: '8px' }}>
              Arokah
            </div>
            <div style={{ fontSize: '3rem', margin: '24px 0' }}>⚠</div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', color: 'var(--cream)', marginBottom: '12px' }}>
              Something went wrong
            </div>
            <p style={{ color: 'var(--cream-dim)', fontSize: '0.875rem', lineHeight: 1.6, marginBottom: '24px' }}>
              {this.state.error?.message || 'An unexpected error occurred.'}
            </p>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
              <button
                className="btn btn-primary"
                onClick={() => window.location.reload()}
              >
                ↻ Reload page
              </button>
              <button
                className="btn btn-ghost"
                onClick={() => { window.location.href = '/' }}
              >
                Go to dashboard
              </button>
            </div>
            {process.env.NODE_ENV === 'development' && (
              <pre style={{
                marginTop: '24px', fontSize: '0.7rem', color: 'var(--cream-dim)',
                textAlign: 'left', background: 'var(--surface-2)', padding: '12px',
                borderRadius: 'var(--radius-md)', overflow: 'auto', maxHeight: '200px',
              }}>
                {this.state.error?.stack}
              </pre>
            )}
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
