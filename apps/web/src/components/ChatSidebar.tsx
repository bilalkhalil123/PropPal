'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api-client'
import { PlusCircle, PanelLeftClose, PanelRightOpen, MessageSquare, Trash2 } from 'lucide-react'
import { motion } from 'framer-motion'

type SessionItem = {
  session_id: string
  last_message: string
  updated_at: string
}

export default function ChatSidebar({ userId, sessionId, activeSessionId, onNewSession, refreshKey }: { userId?: string; sessionId?: string | null; activeSessionId?: string | null; onNewSession?: (sid: string) => void; refreshKey?: number }) {
  const [sessions, setSessions] = useState<SessionItem[]>([])
  const [loading, setLoading] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null)

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

  const deleteSession = async (sid: string) => {
    if (!userId) return
    setDeletingId(sid)
    try {
      await api.chat.deleteSession(userId, sid)
      setSessions((prev) => prev.filter((s) => s.session_id !== sid))
      if (activeSessionId === sid) {
        try { window.localStorage.removeItem('chat_session_id') } catch {}
        onNewSession?.(`s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`)
      }
    } catch (err) {
      console.error('Failed to delete session', err)
      alert('Failed to delete chat. Please try again.')
    } finally {
      setDeletingId(null)
      setPendingDeleteId(null)
    }
  }

  return (
    <aside
      className={`hidden md:flex flex-col bg-white/40 backdrop-blur-xl border border-white/20 rounded-r-2xl transition-all duration-300 ease-in-out ${
        collapsed ? 'w-20' : 'w-72'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/20">
        <div className={`flex items-center gap-2 ${collapsed ? 'opacity-0 pointer-events-none w-0' : 'opacity-100'} overflow-hidden transition-opacity`}>
          <MessageSquare className="h-5 w-5" />
          <h3 className="text-sm font-serif tracking-tight" style={{ color: 'var(--foreground)' }}>Conversations</h3>
        </div>
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="rounded-full p-2 shadow-sm bg-gradient-to-r from-[color:var(--color-primary)] to-[color:var(--color-accent-gold)] text-white hover:ring-2 hover:ring-[color:var(--color-accent-gold)] transition-all"
          aria-label="Toggle sidebar"
        >
          {collapsed ? <PanelRightOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      {/* New chat */}
      <div className="p-3">
        <button
          onClick={startNew}
          className={`w-full bg-gradient-to-r from-[color:var(--color-primary)] to-[color:var(--color-accent-gold)] text-white font-medium py-2.5 px-4 rounded-2xl shadow-md hover:ring-2 hover:ring-[color:var(--color-accent-gold)] active:scale-95 transition-all ${
            collapsed ? 'flex items-center justify-center' : ''
          }`}
          title={collapsed ? 'New Chat' : undefined}
        >
          {collapsed ? <PlusCircle className="h-5 w-5" /> : '+ New chat'}
        </button>
      </div>

      {/* Sessions */}
      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-white/20">
        {loading && <div className="p-3 text-sm text-slate-500">Loading…</div>}
        {!loading && sessions.length === 0 && (
          <div className="p-3 text-sm text-slate-500">No previous chats</div>
        )}
        <ul className="p-2 space-y-3">
          {sessions.map((s) => (
            <motion.li key={s.session_id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }} className="space-y-2">
              <div
                className={`w-full rounded-xl text-sm transition-all flex items-center bg-white/60 hover:bg-white/80 border border-white/20 px-3 ${
                  activeSessionId === s.session_id ? 'bg-gradient-to-r from-[color:var(--color-primary)]/15 to-[color:var(--color-accent-gold)]/10 border-[color:var(--color-accent-gold)]/30 shadow-sm' : ''
                }`}
              >
                <button
                  onClick={() => {
                    try { window.localStorage.setItem('chat_session_id', s.session_id) } catch {}
                    window.location.href = '/chat'
                  }}
                  className="flex-1 text-left py-3 pr-3 overflow-hidden"
                  title={s.last_message}
                  disabled={deletingId === s.session_id}
                >
                  <div className={`truncate font-medium text-slate-700 leading-tight ${collapsed ? 'hidden' : 'block'}`}>
                    {s.last_message || 'Conversation'}
                  </div>
                  <div className={`text-xs text-slate-400 mt-1 ${collapsed ? 'hidden' : 'block'}`}>
                    {new Date(s.updated_at).toLocaleString()}
                  </div>
                  {collapsed && <div className="w-2 h-2 rounded-full bg-slate-300" />}
                </button>
                {!collapsed && (
                  <button
                    onClick={() => setPendingDeleteId(s.session_id)}
                    className="p-2 rounded-full text-slate-500 hover:text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50 self-center"
                    aria-label="Delete chat"
                    disabled={deletingId === s.session_id}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>

              {pendingDeleteId === s.session_id && (
                <div className="rounded-xl border border-slate-200 bg-white shadow-sm px-4 py-3">
                  <div className="text-sm font-semibold text-slate-800 mb-1">Delete chat?</div>
                  <div className="text-sm text-slate-600 mb-3">
                    This will permanently remove this chat history. This action cannot be undone.
                  </div>
                  <div className="flex justify-end gap-2">
                    <button
                      className="px-3 py-2 rounded-lg text-sm text-slate-600 hover:bg-slate-100"
                      onClick={() => setPendingDeleteId(null)}
                      disabled={deletingId === pendingDeleteId}
                    >
                      Cancel
                    </button>
                    <button
                      className="px-3 py-2 rounded-lg text-sm text-white bg-red-600 hover:bg-red-700 disabled:opacity-60"
                      onClick={() => deleteSession(pendingDeleteId)}
                      disabled={deletingId === pendingDeleteId}
                    >
                      {deletingId === pendingDeleteId ? 'Deleting...' : 'Delete'}
                    </button>
                  </div>
                </div>
              )}
            </motion.li>
          ))}
        </ul>
      </div>
    </aside>
  )
}


