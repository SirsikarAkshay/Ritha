// src/components/Toast.jsx
export function ToastList({ toasts }) {
  if (!toasts?.length) return null
  return (
    <div style={{
      position: 'fixed',
      bottom: '2rem',
      right: '2rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      zIndex: 9999,
      maxWidth: '360px',
    }}>
      {toasts.map(t => (
        <div
          key={t.id}
          className={`alert alert-${t.type === 'error' ? 'error' : 'success'}`}
          style={{
            animation: 'fadeUp 0.3s cubic-bezier(0.16,1,0.3,1) both',
            boxShadow: 'var(--shadow-lg)',
          }}
        >
          {t.type === 'error' ? '⚠ ' : '✓ '}{t.message}
        </div>
      ))}
    </div>
  )
}
