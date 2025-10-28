'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api-client'

type SessionItem = {
  session_id: string
  last_message: string
  updated_at: string
}

export default function ChatSidebar({ userId, sessionId, activeSessionId, onNewSession, refreshKey }: { userId?: string; sessionId?: string | null; activeSessionId?: string | null; onNewSession?: (sid: string) => void; refreshKey?: number }) {
  const [sessions, setSessions] = useState<SessionItem[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const load = async () => {
      if (!userId) return
      setLoading(true)
      try {
        const res = await api.chat.sessions(userId) as any
        setSessions(res?.sessions || [])
      } catch {
        // ignore
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [userId, sessionId, refreshKey])

  const startNew = () => {
    const sid = `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
    try { window.localStorage.setItem('chat_session_id', sid) } catch {}
    onNewSession?.(sid)
  }

  return (
    <aside className="hidden md:flex md:w-64 lg:w-72 flex-col border-r border-slate-200 bg-white">
      <div className="p-3 border-b border-slate-200">
        <button onClick={startNew} className="w-full bg-indigo-600 text-white py-2.5 rounded-xl text-sm font-medium hover:bg-indigo-700 transition-colors">+ New chat</button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {loading && <div className="p-3 text-sm text-slate-500">Loading…</div>}
        {!loading && sessions.length === 0 && (
          <div className="p-3 text-sm text-slate-500">No previous chats</div>
        )}
        <ul className="p-2 space-y-1">
          {sessions.map((s) => (
            <li key={s.session_id}>
              <button
                onClick={() => {
                  try { window.localStorage.setItem('chat_session_id', s.session_id) } catch {}
                  window.location.href = '/chat'
                }}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-slate-100 ${activeSessionId === s.session_id ? 'bg-slate-100' : ''}`}
                title={s.last_message}
              >
                <div className="truncate font-medium text-slate-700">{s.last_message || 'Conversation'}</div>
                <div className="text-xs text-slate-400 mt-0.5">{new Date(s.updated_at).toLocaleString()}</div>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  )
}


