import { useEffect, useState } from 'react'

interface Conversation {
  id: string
  name: string | null
  created_at?: string | null
  rating?: number | null
}

function formatConversationLabel(createdAt: string | null | undefined): string {
  if (!createdAt) return 'Conversation'
  try {
    const d = new Date(createdAt)
    if (Number.isNaN(d.getTime())) return 'Conversation'
    return `Conversation ${d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })}`
  } catch {
    return 'Conversation'
  }
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  rating?: number | null
}

interface ChatScreenProps {
  apiBaseUrl: string
  token: string
  tokenType: string
  onLogout: () => void
}

function RatingStars({
  value,
  onChange,
}: {
  value?: number | null
  onChange?: (rating: number) => void
}) {
  return (
    <div className="rating-stars">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          className={star <= (value || 0) ? 'star star-filled' : 'star'}
          onClick={() => onChange?.(star)}
        >
          {star <= (value || 0) ? '★' : '☆'}
        </button>
      ))}
    </div>
  )
}

export function ChatScreen({ apiBaseUrl, token, tokenType, onLogout }: ChatScreenProps) {
  const authHeader = `${tokenType || 'bearer'} ${token}`
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [loadingConversations, setLoadingConversations] = useState(false)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [conversationRating, setConversationRating] = useState<number | null>(null)

  useEffect(() => {
    void loadConversations()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadConversations = async () => {
    setLoadingConversations(true)
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/conversations`, {
        headers: {
          Authorization: authHeader,
        },
      })
      if (!response.ok) {
        throw new Error('Failed to load conversations.')
      }
      const data: Conversation[] = await response.json()
      setConversations(data)
      if (!selectedConversationId && data.length > 0) {
        void handleSelectConversation(data[0].id)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversations.')
    } finally {
      setLoadingConversations(false)
    }
  }

  const handleCreateConversation = async () => {
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/conversations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: authHeader,
        },
        body: JSON.stringify({}),
      })
      if (!response.ok) {
        throw new Error('Failed to create conversation.')
      }
      const conv: Conversation = await response.json()
      setConversations((prev) => [conv, ...prev])
      void handleSelectConversation(conv.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create conversation.')
    }
  }

  const handleSelectConversation = async (conversationId: string) => {
    setSelectedConversationId(conversationId)
    setMessages([])
    setLoadingMessages(true)
    setError(null)
    try {
      const [convRes, messagesRes] = await Promise.all([
        fetch(`${apiBaseUrl}/conversations/${conversationId}`, {
          headers: {
            Authorization: authHeader,
          },
        }),
        fetch(`${apiBaseUrl}/conversations/${conversationId}/messages`, {
          headers: {
            Authorization: authHeader,
          },
        }),
      ])

      if (!convRes.ok) {
        throw new Error('Failed to load conversation.')
      }
      const conv: Conversation = await convRes.json()
      setConversationRating(conv.rating ?? null)

      if (!messagesRes.ok) {
        throw new Error('Failed to load messages.')
      }
      const msgs: Message[] = await messagesRes.json()
      setMessages(msgs)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversation.')
    } finally {
      setLoadingMessages(false)
    }
  }

  const handleSendMessage = async () => {
    if (!selectedConversationId || !newMessage.trim()) return
    const content = newMessage.trim()
    const optimisticId = `opt-${Date.now()}`
    const optimisticUserMessage: Message = {
      id: optimisticId,
      role: 'user',
      content,
    }
    setMessages((prev) => [...prev, optimisticUserMessage])
    setNewMessage('')
    setError(null)
    setSending(true)
    try {
      const response = await fetch(`${apiBaseUrl}/conversations/${selectedConversationId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: authHeader,
        },
        body: JSON.stringify({ content }),
      })
      if (!response.ok) {
        throw new Error('Failed to send message.')
      }
      const data = await response.json()
      const { user_message, assistant_message } = data
      setMessages((prev) => [
        ...prev.filter((m) => !m.id.startsWith('opt-')),
        user_message,
        assistant_message,
      ])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message.')
      setMessages((prev) => prev.filter((m) => m.id !== optimisticId))
      setNewMessage(content)
    } finally {
      setSending(false)
    }
  }

  const handleTextareaKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSendMessage()
    }
  }

  const handleRateMessage = async (messageId: string, rating: number) => {
    if (!selectedConversationId) return
    try {
      const response = await fetch(
        `${apiBaseUrl}/conversations/${selectedConversationId}/messages/${messageId}/rating`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: authHeader,
          },
          body: JSON.stringify({ rating }),
        },
      )
      if (!response.ok) {
        throw new Error('Failed to rate message.')
      }
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, rating } : m)),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rate message.')
    }
  }

  const handleRateConversation = async (rating: number) => {
    if (!selectedConversationId) return
    try {
      const response = await fetch(`${apiBaseUrl}/conversations/${selectedConversationId}/rating`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: authHeader,
        },
        body: JSON.stringify({ rating }),
      })
      if (!response.ok) {
        throw new Error('Failed to rate conversation.')
      }
      setConversationRating(rating)
      setConversations((prev) =>
        prev.map((c) => (c.id === selectedConversationId ? { ...c, rating } : c)),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rate conversation.')
    }
  }

  return (
    <div className="chat-shell">
      <div className="chat-header-bar">
        <span className="chat-header-title">Kitchen Assistant</span>
        <button
          type="button"
          className="chat-logout-button"
          onClick={onLogout}
        >
          Log out
        </button>
      </div>
      <div className="chat-layout">
        <aside className="chat-sidebar">
          <div className="chat-sidebar-header">
            <h2>Conversations</h2>
          </div>
          {loadingConversations && <p className="chat-muted">Loading...</p>}
          <ul className="chat-conversation-list">
            {conversations.map((conv) => (
              <li key={conv.id}>
                <button
                  type="button"
                  className={
                    conv.id === selectedConversationId
                      ? 'chat-conversation-item active'
                      : 'chat-conversation-item'
                  }
                  onClick={() => void handleSelectConversation(conv.id)}
                >
                  <span className="chat-conversation-name">
                    {formatConversationLabel(conv.created_at)}
                  </span>
                </button>
              </li>
            ))}
            {!loadingConversations && conversations.length === 0 && (
              <li className="chat-muted">No conversations yet.</li>
            )}
          </ul>
          <button
            type="button"
            className="chat-new-conversation-btn"
            onClick={handleCreateConversation}
          >
            + New conversation
          </button>
        </aside>

        <main className="chat-main">
          {selectedConversationId ? (
            <>
              <div
                className={`chat-messages${!loadingMessages && messages.length === 0 ? ' chat-messages--empty' : ''}`}
                aria-live="polite"
              >
                {loadingMessages && <p className="chat-muted">Loading messages...</p>}
                {!loadingMessages && messages.length === 0 && (
                  <p className="chat-muted">Send a message to start the conversation.</p>
                )}
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={
                      message.role === 'user'
                        ? 'chat-message chat-message-user'
                        : 'chat-message chat-message-assistant'
                    }
                  >
                    <div className="chat-message-meta">
                      <span className="chat-message-role">
                        {message.role === 'user' ? 'You' : 'Assistant'}
                      </span>
                      {message.role === 'assistant' && (
                        <RatingStars
                          value={message.rating}
                          onChange={(rating) => handleRateMessage(message.id, rating)}
                        />
                      )}
                    </div>
                    <p className="chat-message-content">{message.content}</p>
                  </div>
                ))}
                {sending && (
                  <div className="chat-message chat-message-assistant chat-typing-bubble">
                    <div className="chat-message-meta">
                      <span className="chat-message-role">Assistant</span>
                    </div>
                    <div className="chat-typing-dots">
                      <span className="chat-typing-dot" />
                      <span className="chat-typing-dot" />
                      <span className="chat-typing-dot" />
                    </div>
                  </div>
                )}
              </div>
              <div className="chat-input-row">
                <textarea
                  value={newMessage}
                  onChange={(event) => setNewMessage(event.target.value)}
                  onKeyDown={handleTextareaKeyDown}
                  placeholder="Ask the kitchen assistant..."
                  rows={2}
                />
                <button
                  type="button"
                  className="chat-button primary"
                  onClick={() => void handleSendMessage()}
                  disabled={!newMessage.trim()}
                >
                  Send
                </button>
              </div>
            </>
          ) : (
            <div className="chat-empty">
              <p className="chat-muted">Select or create a conversation to begin.</p>
            </div>
          )}
          {error && (
            <p className="chat-error">
              {error}{' '}
              <button type="button" className="chat-link-button" onClick={onLogout}>
                Log in again
              </button>
            </p>
          )}
        </main>

        <aside className="chat-meta">
          <h2>Conversation rating</h2>
          {selectedConversationId ? (
            <>
              <RatingStars value={conversationRating} onChange={handleRateConversation} />
              <p className="chat-muted-small">Rate this conversation from 1 to 5 stars.</p>
            </>
          ) : (
            <p className="chat-muted-small">Choose a conversation to rate it.</p>
          )}
        </aside>
      </div>
    </div>
  )
}

