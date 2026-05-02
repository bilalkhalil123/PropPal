"use client"

import { useState, useRef, useEffect } from "react"
import { useAuth, SignIn } from "@clerk/nextjs"
import { motion, AnimatePresence } from "framer-motion"
import {
  ChatBubbleLeftRightIcon,
  XMarkIcon,
} from "@heroicons/react/24/solid"
import { api } from "@/lib/api-client"

export type ChatTurn = { role: "user" | "assistant"; content: string }

type Props = {
  propertyId: string
  propertyName: string
  isAuthenticated: boolean
  authLoading: boolean
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function PropertyBookingChat({
  propertyId,
  propertyName,
  isAuthenticated,
  authLoading,
  open,
  onOpenChange,
}: Props) {
  const { getToken } = useAuth()
  const [messages, setMessages] = useState<ChatTurn[]>(() => [
    {
      role: "assistant",
      content: `Hi! I can help you schedule a visit for ${propertyName}. Just let me know when you'd like to come by.`,
    },
  ])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (open) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages, loading, open])

  const send = async () => {
    const text = input.trim()
    if (!text || loading || !isAuthenticated) return
    setError(null)
    setLoading(true)
    setInput("")
    try {
      const token = await getToken()
      if (!token) {
        setError("Please sign in to use the booking assistant.")
        return
      }
      const conversation_history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }))
      const res = await api.chat.booking(
        {
          message: text,
          property_id: propertyId,
          conversation_history,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      if (!res.success && res.error) {
        setError(res.error)
      }
      setMessages(
        (res.updated_history || []).map((m) => ({
          role: m.role === "user" ? "user" : "assistant",
          content: m.content,
        }))
      )
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Request failed"
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.96 }}
            transition={{ type: "spring", stiffness: 380, damping: 32 }}
            className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-40 w-[min(100vw-2rem,22rem)] sm:w-[min(100vw-2.5rem,26rem)] max-h-[min(70vh,34rem)] flex flex-col rounded-2xl bg-white shadow-[0_20px_50px_-12px_rgba(0,0,0,0.28)] border border-slate-200/90 overflow-hidden"
            role="dialog"
            aria-label="Visit booking assistant"
          >
            <div className="flex items-center justify-between gap-2 px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-slate-900 to-[color:var(--color-primary)] text-white shrink-0">
              <div className="min-w-0">
                <h3 className="text-sm font-semibold truncate">Book a visit</h3>
                <p className="text-[11px] text-white/80 truncate">{propertyName}</p>
              </div>
              <button
                type="button"
                onClick={() => onOpenChange(false)}
                className="shrink-0 p-2 rounded-xl hover:bg-white/15 transition-colors"
                aria-label="Close booking chat"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>

            {!isAuthenticated && !authLoading ? (
              <div className="flex-1 min-h-[200px] flex flex-col items-center justify-center p-5 text-center gap-3 overflow-y-auto">
                <p className="text-sm text-slate-600">
                  Sign in to chat and book a visit for this property.
                </p>
                <SignIn
                  routing="hash"
                  appearance={{
                    variables: {
                      colorPrimary: "var(--color-accent-gold)",
                      borderRadius: "12px",
                    },
                  }}
                />
              </div>
            ) : (
              <>
                <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2.5 min-h-0 bg-slate-50/80">
                  <AnimatePresence initial={false}>
                    {messages.map((m, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                      >
                        <div
                          className={`max-w-[92%] rounded-2xl px-3 py-2 text-[13px] leading-snug shadow-sm whitespace-pre-wrap ${
                            m.role === "user"
                              ? "bg-[color:var(--color-primary)] text-white rounded-br-md"
                              : "bg-white text-slate-800 border border-slate-100 rounded-bl-md"
                          }`}
                        >
                          {m.content}
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                  {loading && (
                    <div className="flex justify-start">
                      <div className="bg-white border border-slate-100 rounded-2xl rounded-bl-md px-3 py-2.5 text-xs text-slate-500 flex gap-2 items-center shadow-sm">
                        <span className="inline-flex gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:0ms]" />
                          <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:150ms]" />
                          <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:300ms]" />
                        </span>
                        Thinking…
                      </div>
                    </div>
                  )}
                  <div ref={bottomRef} />
                </div>
                {error && (
                  <p className="px-3 text-[11px] text-red-600 shrink-0 bg-amber-50/80 border-t border-amber-100 py-1.5">
                    {error}
                  </p>
                )}
                <div className="p-2.5 border-t border-slate-100 bg-white flex gap-2 shrink-0">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
                    placeholder="Message…"
                    disabled={loading || authLoading}
                    className="flex-1 min-w-0 rounded-xl border border-slate-200 px-3 py-2 text-[13px] bg-slate-50/50 focus:outline-none focus:ring-2 focus:ring-[color:var(--color-accent-gold)] disabled:opacity-50"
                  />
                  <button
                    type="button"
                    onClick={send}
                    disabled={loading || authLoading || !input.trim()}
                    className="shrink-0 px-3.5 py-2 rounded-xl font-semibold text-white text-xs bg-[linear-gradient(to_right,var(--color-primary),var(--color-accent-gold))] disabled:opacity-50"
                  >
                    Send
                  </button>
                </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {!open && (
          <motion.button
            type="button"
            key="booking-fab"
            initial={{ scale: 0.85, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.85, opacity: 0 }}
            transition={{ type: "spring", stiffness: 400, damping: 28 }}
            onClick={() => onOpenChange(true)}
            className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-[color:var(--color-primary)] to-[color:var(--color-accent-gold)] text-white shadow-[0_10px_30px_-5px_rgba(0,0,0,0.35)] border border-white/20 hover:scale-105 active:scale-95 transition-transform"
            aria-label="Open booking assistant"
          >
            <ChatBubbleLeftRightIcon className="h-7 w-7" />
          </motion.button>
        )}
      </AnimatePresence>
    </>
  )
}
