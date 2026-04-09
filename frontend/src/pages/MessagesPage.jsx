// src/pages/MessagesPage.jsx
// 1:1 chat. Left pane: conversation list. Right pane: active thread.
// Live updates via WebSocket; sending uses the REST POST /send/ path.
import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { messaging as chatApi, social as socialApi } from '../api/index.js'
import { connectWebSocket } from '../api/ws.js'
import { useAuth } from '../hooks/useAuth.jsx'

export default function MessagesPage() {
  const { user } = useAuth()
  const location = useLocation()
  const [conversations, setConversations] = useState([])
  const [active, setActive]                = useState(null)  // conversation object
  const [messages, setMessages]            = useState([])
  const [draft, setDraft]                  = useState('')
  const [sending, setSending]              = useState(false)
  const [loadingList, setLoadingList]      = useState(true)
  const [loadingMsgs, setLoadingMsgs]      = useState(false)
  const wsRef      = useRef(null)
  const scrollRef  = useRef(null)

  // If navigated here with { state: { openUserId } }, auto-open that DM
  useEffect(() => {
    const openUserId = location.state?.openUserId
    if (openUserId) {
      chatApi.conversations.openWith(openUserId).then(conv => {
        setActive(conv)
        loadConversations()
      }).catch(err => {
        const msg = err.response?.data?.error?.message || 'Could not open conversation.'
        window.__toast?.(msg, 'error')
      })
    }
  }, [location.state?.openUserId])

  const loadConversations = async () => {
    setLoadingList(true)
    try {
      const list = await chatApi.conversations.list()
      setConversations(Array.isArray(list) ? list : (list.results || []))
    } finally {
      setLoadingList(false)
    }
  }

  useEffect(() => { loadConversations() }, [])

  // When the active conversation changes: load history, open WS
  useEffect(() => {
    if (!active) {
      setMessages([])
      if (wsRef.current) { wsRef.current.close(); wsRef.current = null }
      return
    }

    let cancelled = false
    setLoadingMsgs(true)
    chatApi.conversations.messages(active.id).then(list => {
      if (cancelled) return
      setMessages(Array.isArray(list) ? list : [])
      setTimeout(scrollToBottom, 50)
    }).finally(() => !cancelled && setLoadingMsgs(false))

    // Mark as read when opened
    chatApi.conversations.markRead(active.id).catch(() => {})

    // Open WebSocket for live updates
    const ws = connectWebSocket(`/ws/chat/${active.id}/`)
    wsRef.current = ws
    ws.on('message', (data) => {
      if (data?.type === 'message' && data.message) {
        setMessages(prev => {
          // Avoid dup if we just POSTed and the server bounce came back
          if (prev.some(m => m.id === data.message.id)) return prev
          return [...prev, data.message]
        })
        setTimeout(scrollToBottom, 50)
        // Mark read immediately if we're looking at it
        chatApi.conversations.markRead(active.id).catch(() => {})
      }
    })

    return () => {
      cancelled = true
      ws.close()
    }
  }, [active?.id])

  const scrollToBottom = () => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }

  const send = async (e) => {
    e?.preventDefault()
    const body = draft.trim()
    if (!body || !active || sending) return
    setSending(true)
    try {
      const msg = await chatApi.conversations.send(active.id, body)
      setMessages(prev => prev.some(m => m.id === msg.id) ? prev : [...prev, msg])
      setDraft('')
      setTimeout(scrollToBottom, 50)
      // Refresh the side list so last-message preview updates
      loadConversations()
    } catch (err) {
      window.__toast?.(err.response?.data?.error?.message || 'Failed to send.', 'error')
    } finally {
      setSending(false)
    }
  }

  return (
    <div>
      <div className="page-header fade-up">
        <div className="date-line">Social</div>
        <h1>Messages</h1>
        <p>Direct message the people you're connected with.</p>
      </div>

      <div className="fade-up fade-up-delay-1" style={{
        display: 'grid',
        gridTemplateColumns: '300px 1fr',
        gap: '20px',
        height: 'calc(100vh - 260px)',
        minHeight: '500px',
      }}>
        {/* ── Conversation list ───────────────────────────────────── */}
        <div className="card" style={{ padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '16px', borderBottom: '1px solid var(--border)' }}>
            <div className="card-label">Conversations</div>
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {loadingList ? (
              <div style={{ padding: '20px', color: 'var(--cream-dim)', fontSize: '0.8125rem' }}>Loading…</div>
            ) : conversations.length === 0 ? (
              <div style={{ padding: '20px', color: 'var(--cream-dim)', fontSize: '0.8125rem' }}>
                No conversations yet. Start one from the People page.
              </div>
            ) : (
              conversations.map(conv => (
                <button
                  key={conv.id}
                  onClick={() => setActive(conv)}
                  style={{
                    display: 'flex',
                    gap: '12px',
                    alignItems: 'flex-start',
                    width: '100%',
                    padding: '14px 16px',
                    border: 'none',
                    background: active?.id === conv.id ? 'var(--surface-2)' : 'transparent',
                    borderBottom: '1px solid var(--border)',
                    cursor: 'pointer',
                    textAlign: 'left',
                    color: 'var(--cream)',
                  }}
                >
                  <Avatar name={conv.other_user?.display_name || conv.other_user?.handle} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
                      <span style={{ fontWeight: 500, fontSize: '0.875rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {conv.other_user?.display_name || '@' + conv.other_user?.handle}
                      </span>
                      {conv.unread_count > 0 && (
                        <span style={{ background: 'var(--terra)', color: 'var(--cream)', borderRadius: '10px', padding: '1px 7px', fontSize: '0.7rem', flexShrink: 0 }}>
                          {conv.unread_count}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {conv.last_message?.body || 'No messages yet.'}
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* ── Active thread ──────────────────────────────────────── */}
        <div className="card" style={{ padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {!active ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--cream-dim)' }}>
              Select a conversation to start chatting.
            </div>
          ) : (
            <>
              <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Avatar name={active.other_user?.display_name || active.other_user?.handle} />
                <div>
                  <div style={{ fontWeight: 500, color: 'var(--cream)' }}>
                    {active.other_user?.display_name || '@' + active.other_user?.handle}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--cream-dim)' }}>@{active.other_user?.handle}</div>
                </div>
              </div>

              <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {loadingMsgs ? (
                  <div style={{ color: 'var(--cream-dim)', fontSize: '0.8125rem' }}>Loading messages…</div>
                ) : messages.length === 0 ? (
                  <div style={{ color: 'var(--cream-dim)', fontSize: '0.8125rem' }}>
                    Say hello to {active.other_user?.display_name || '@' + active.other_user?.handle}.
                  </div>
                ) : (
                  messages.map(msg => {
                    const mine = msg.sender === user?.id
                    return (
                      <div key={msg.id} style={{
                        alignSelf: mine ? 'flex-end' : 'flex-start',
                        maxWidth: '70%',
                        background: mine ? 'var(--terra)' : 'var(--surface-2)',
                        color: mine ? 'var(--cream)' : 'var(--cream)',
                        padding: '8px 14px',
                        borderRadius: '16px',
                        fontSize: '0.875rem',
                        lineHeight: 1.4,
                        wordBreak: 'break-word',
                      }}>
                        {msg.body}
                      </div>
                    )
                  })
                )}
              </div>

              <form onSubmit={send} style={{ borderTop: '1px solid var(--border)', padding: '12px 16px', display: 'flex', gap: '10px' }}>
                <input
                  className="input"
                  value={draft}
                  onChange={e => setDraft(e.target.value)}
                  placeholder={`Message ${active.other_user?.display_name || '@' + active.other_user?.handle}`}
                  style={{ flex: 1 }}
                  disabled={sending}
                />
                <button type="submit" className="btn btn-primary btn-sm" disabled={sending || !draft.trim()}>
                  {sending ? 'Sending…' : 'Send'}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function Avatar({ name }) {
  const initial = (name || '?').charAt(0).toUpperCase().replace('@', name?.charAt(1)?.toUpperCase() || '?')
  return (
    <div style={{
      width: '38px', height: '38px', borderRadius: '50%',
      background: 'var(--terra-dim)', color: 'var(--terra-light)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: '0.875rem', fontWeight: 500, flexShrink: 0,
    }}>
      {initial}
    </div>
  )
}
