"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { api } from "@/lib/api-client"
import { useCurrentUser } from "@/hooks/useCurrentUser"
import {
	ChatBubbleLeftRightIcon,
	PaperAirplaneIcon,
	ArrowLeftIcon,
	UserCircleIcon,
	BuildingOffice2Icon,
} from "@heroicons/react/24/outline"

interface OtherParticipant {
	id: string
	name: string
	role: string
	company_name?: string | null
}

interface Conversation {
	_id: string
	conversation_type: string
	participant_ids: string[]
	last_message?: string | null
	last_message_at?: string | null
	other_participant?: OtherParticipant
	participant_names?: Record<string, string>
	builder_companies?: Record<string, string>
}

interface Message {
	_id: string
	sender_id: string
	content: string
	created_at: string
}

const POLL_INTERVAL_MESSAGES = 3000 // 3 seconds for active chat
const POLL_INTERVAL_CONVERSATIONS = 5000 // 5 seconds for sidebar

export default function MessagesPage() {
	const { clerkId, userId, isAuthenticated } = useCurrentUser()
	const searchParams = useSearchParams()
	const [conversations, setConversations] = useState<Conversation[]>([])
	const [messages, setMessages] = useState<Message[]>([])
	const [selectedId, setSelectedId] = useState<string | null>(null)
	const [input, setInput] = useState("")
	const [loading, setLoading] = useState(true)
	const [sending, setSending] = useState(false)
	const messagesEndRef = useRef<HTMLDivElement>(null)
	const shouldAutoScroll = useRef(true)

	const roleParam = searchParams.get("role")

	const activeConversationId = useMemo(() => {
		const param = searchParams.get("conversation")
		return param || selectedId
	}, [searchParams, selectedId])

	const activeConversation = useMemo(
		() => conversations.find((c) => c._id === activeConversationId),
		[conversations, activeConversationId]
	)

	// -------------------------------------------------------
	// Conversation list loader (used for initial + polling)
	// -------------------------------------------------------
	const loadConversations = useCallback(async () => {
		if (!clerkId || !isAuthenticated) return
		try {
			const res = await api.conversations.list(clerkId)
			setConversations(res.conversations || [])
		} catch (error) {
			console.error(error)
		}
	}, [clerkId, isAuthenticated])

	// Initial load
	useEffect(() => {
		const init = async () => {
			if (!clerkId || !isAuthenticated) {
				setLoading(false)
				return
			}
			try {
				const res = await api.conversations.list(clerkId)
				setConversations(res.conversations || [])
				if (!selectedId && res.conversations?.length) {
					setSelectedId(res.conversations[0]._id)
				}
			} catch (error) {
				console.error(error)
			} finally {
				setLoading(false)
			}
		}
		init()
	}, [clerkId, isAuthenticated]) // eslint-disable-line react-hooks/exhaustive-deps

	// -------------------------------------------------------
	// Message loader (used for initial + polling)
	// -------------------------------------------------------
	const loadMessages = useCallback(async () => {
		if (!clerkId || !activeConversationId) return
		try {
			const res = await api.conversations.messages(clerkId, activeConversationId)
			const fresh = res.messages || []
			setMessages((prev) => {
				// Only update if there are actual changes (avoids unnecessary re-render / scroll)
				if (prev.length !== fresh.length || (fresh.length > 0 && prev[prev.length - 1]?._id !== fresh[fresh.length - 1]?._id)) {
					return fresh
				}
				return prev
			})
		} catch (error) {
			console.error(error)
		}
	}, [clerkId, activeConversationId])

	// Load messages on conversation switch
	useEffect(() => {
		if (!clerkId || !activeConversationId) return
		// Reset and load
		setMessages([])
		shouldAutoScroll.current = true
		loadMessages()
	}, [clerkId, activeConversationId, loadMessages])

	// -------------------------------------------------------
	// Polling: messages (active chat) + conversation sidebar
	// -------------------------------------------------------
	useEffect(() => {
		if (!clerkId || !activeConversationId) return
		const interval = setInterval(loadMessages, POLL_INTERVAL_MESSAGES)
		return () => clearInterval(interval)
	}, [clerkId, activeConversationId, loadMessages])

	useEffect(() => {
		if (!clerkId || !isAuthenticated) return
		const interval = setInterval(loadConversations, POLL_INTERVAL_CONVERSATIONS)
		return () => clearInterval(interval)
	}, [clerkId, isAuthenticated, loadConversations])

	// Auto-scroll when new messages arrive
	useEffect(() => {
		if (shouldAutoScroll.current) {
			messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
		}
	}, [messages])

	// -------------------------------------------------------
	// Optimistic send — show immediately, then sync
	// -------------------------------------------------------
	const handleSend = async () => {
		if (!clerkId || !activeConversationId || !input.trim() || !userId) return
		const content = input.trim()
		setSending(true)
		setInput("")

		// Optimistic message — render immediately
		const optimisticMsg: Message = {
			_id: `temp-${Date.now()}`,
			sender_id: userId,
			content,
			created_at: new Date().toISOString(),
		}
		setMessages((prev) => [...prev, optimisticMsg])
		shouldAutoScroll.current = true

		try {
			await api.conversations.sendMessage(clerkId, activeConversationId, { content })
			// After backend confirms, re-fetch to get the real message id
			await loadMessages()
			// Also update the sidebar preview
			await loadConversations()
		} catch (error) {
			console.error(error)
			// Remove the optimistic message on failure
			setMessages((prev) => prev.filter((m) => m._id !== optimisticMsg._id))
			setInput(content) // restore the text
		} finally {
			setSending(false)
		}
	}

	const formatTime = (dateString: string) => {
		const date = new Date(dateString)
		return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
	}

	const formatDate = (dateString: string) => {
		const date = new Date(dateString)
		const now = new Date()
		const diff = now.getTime() - date.getTime()
		const days = Math.floor(diff / (1000 * 60 * 60 * 24))
		if (days === 0) return "Today"
		if (days === 1) return "Yesterday"
		return date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
	}

	const getDisplayName = (convo: Conversation) => {
		const other = convo.other_participant
		if (other?.name) {
			return other.name
		}
		return convo.conversation_type.replace(/_/g, " ")
	}

	const getDisplaySubtitle = (convo: Conversation) => {
		const other = convo.other_participant
		if (other?.role === "builder" && other.company_name) {
			return other.company_name
		}
		return ""
	}

	const backHref = roleParam === "builder" ? "/builder" : "/buyer"

	if (!isAuthenticated) {
		return (
			<div className="min-h-screen flex items-center justify-center bg-[linear-gradient(to_bottom,rgba(249,249,249,0.85),rgba(237,236,232,0.9))]">
				<div className="text-center">
					<ChatBubbleLeftRightIcon className="h-16 w-16 text-slate-300 mx-auto mb-4" />
					<h2 className="text-xl font-bold text-slate-700 mb-2">Sign in to view messages</h2>
					<Link href="/sign-in" className="text-indigo-600 hover:underline">Sign in →</Link>
				</div>
			</div>
		)
	}

	return (
		<div className="min-h-screen bg-[linear-gradient(to_bottom,rgba(249,249,249,0.85),rgba(237,236,232,0.9))]">
			<div className="max-w-6xl mx-auto px-4 md:px-6 py-6">
				{/* Back Link */}
				<Link href={backHref} className="inline-flex items-center text-slate-600 hover:text-slate-900 text-sm mb-4">
					<ArrowLeftIcon className="h-4 w-4 mr-2" />
					Back to Dashboard
				</Link>

				<div className="rounded-2xl bg-white/70 backdrop-blur-xl border border-slate-200 shadow-lg overflow-hidden" style={{ height: "calc(100vh - 180px)" }}>
					<div className="grid grid-cols-1 md:grid-cols-[320px_1fr] h-full">
						{/* Sidebar */}
						<aside className="border-r border-slate-200 flex flex-col h-full">
							<div className="p-4 border-b border-slate-200 bg-white/50">
								<h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
									<ChatBubbleLeftRightIcon className="h-5 w-5 text-[color:var(--color-primary)]" />
									Conversations
								</h2>
							</div>

							<div className="flex-1 overflow-y-auto">
								{loading && (
									<div className="flex justify-center py-8">
										<div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[color:var(--color-primary)]"></div>
									</div>
								)}
								{!loading && conversations.length === 0 && (
									<div className="text-center py-12 px-4">
										<ChatBubbleLeftRightIcon className="h-10 w-10 text-slate-300 mx-auto mb-3" />
										<p className="text-sm text-slate-500">No conversations yet</p>
									</div>
								)}
								{conversations.map((conversation) => {
									const isActive = conversation._id === activeConversationId
									const name = getDisplayName(conversation)
									const subtitle = getDisplaySubtitle(conversation)
									const isBuilder = conversation.other_participant?.role === "builder"

									return (
										<button
											key={conversation._id}
											onClick={() => setSelectedId(conversation._id)}
											className={`w-full text-left p-4 border-b border-slate-100 transition-colors ${
												isActive
													? "bg-[color:var(--color-primary)]/10 border-l-2 border-l-[color:var(--color-primary)]"
													: "hover:bg-slate-50"
											}`}
										>
											<div className="flex items-center gap-3">
												<div className={`h-10 w-10 rounded-full flex items-center justify-center shrink-0 ${
													isBuilder ? "bg-amber-100" : "bg-indigo-100"
												}`}>
													{isBuilder ? (
														<BuildingOffice2Icon className="h-5 w-5 text-amber-700" />
													) : (
														<UserCircleIcon className="h-5 w-5 text-indigo-700" />
													)}
												</div>
												<div className="flex-1 min-w-0">
													<div className="flex items-center justify-between">
														<span className="font-semibold text-slate-900 text-sm truncate">{name}</span>
														{conversation.last_message_at && (
															<span className="text-xs text-slate-400 shrink-0 ml-2">
																{formatDate(conversation.last_message_at)}
															</span>
														)}
													</div>
													{subtitle && (
														<p className="text-xs text-slate-500 truncate">{subtitle}</p>
													)}
													{conversation.last_message && (
														<p className="text-xs text-slate-400 truncate mt-0.5">
															{conversation.last_message}
														</p>
													)}
												</div>
											</div>
										</button>
									)
								})}
							</div>
						</aside>

						{/* Chat Area */}
						<section className="flex flex-col h-full">
							{/* Chat Header */}
							{activeConversation ? (
								<>
									<div className="p-4 border-b border-slate-200 bg-white/50 flex items-center gap-3">
										<div className={`h-10 w-10 rounded-full flex items-center justify-center ${
											activeConversation.other_participant?.role === "builder" ? "bg-amber-100" : "bg-indigo-100"
										}`}>
											{activeConversation.other_participant?.role === "builder" ? (
												<BuildingOffice2Icon className="h-5 w-5 text-amber-700" />
											) : (
												<UserCircleIcon className="h-5 w-5 text-indigo-700" />
											)}
										</div>
										<div>
											<h3 className="font-bold text-slate-900">
												{getDisplayName(activeConversation)}
											</h3>
											{getDisplaySubtitle(activeConversation) && (
												<p className="text-xs text-slate-500">
													{getDisplaySubtitle(activeConversation)}
												</p>
											)}
										</div>
									</div>

									{/* Messages */}
									<div className="flex-1 overflow-y-auto p-4 space-y-3">
										{messages.length === 0 && (
											<div className="text-center py-16">
												<ChatBubbleLeftRightIcon className="h-10 w-10 text-slate-300 mx-auto mb-3" />
												<p className="text-sm text-slate-400">Start the conversation</p>
											</div>
										)}
										{messages.map((message) => {
											const isMine = message.sender_id === userId
											const isOptimistic = message._id.startsWith("temp-")
											// Determine sender name
											const senderName = isMine
												? "You"
												: activeConversation.participant_names?.[message.sender_id] || "Unknown"
											return (
												<div
													key={message._id}
													className={`flex ${isMine ? "justify-end" : "justify-start"}`}
												>
													<div
														className={`max-w-[75%] rounded-2xl px-4 py-3 ${
															isMine
																? "bg-[linear-gradient(135deg,var(--color-primary),var(--color-accent-gold))] text-white rounded-br-md"
																: "bg-slate-100 text-slate-900 rounded-bl-md"
														} ${isOptimistic ? "opacity-70" : ""}`}
													>
														{!isMine && (
															<p className="text-xs font-semibold mb-1 opacity-70">{senderName}</p>
														)}
														<p className="text-sm leading-relaxed">{message.content}</p>
														<p className={`text-[10px] mt-1 ${isMine ? "text-white/70" : "text-slate-400"}`}>
															{isOptimistic ? "Sending..." : formatTime(message.created_at)}
														</p>
													</div>
												</div>
											)
										})}
										<div ref={messagesEndRef} />
									</div>

									{/* Input */}
									<div className="p-4 border-t border-slate-200 bg-white/50">
										<div className="flex gap-2">
											<Input
												value={input}
												onChange={(e) => setInput(e.target.value)}
												placeholder="Type a message..."
												className="rounded-xl border-slate-300 flex-1"
												onKeyDown={(e) => {
													if (e.key === "Enter" && !e.shiftKey) {
														e.preventDefault()
														handleSend()
													}
												}}
												disabled={sending}
											/>
											<Button
												onClick={handleSend}
												disabled={sending || !input.trim()}
												className="rounded-xl bg-[linear-gradient(to_right,var(--color-primary),var(--color-accent-gold))] text-white px-4"
											>
												<PaperAirplaneIcon className="h-5 w-5" />
											</Button>
										</div>
									</div>
								</>
							) : (
								<div className="flex-1 flex items-center justify-center">
									<div className="text-center">
										<ChatBubbleLeftRightIcon className="h-16 w-16 text-slate-300 mx-auto mb-4" />
										<h3 className="text-lg font-semibold text-slate-600">Select a conversation</h3>
										<p className="text-sm text-slate-400">Choose from the sidebar to start chatting</p>
									</div>
								</div>
							)}
						</section>
					</div>
				</div>
			</div>
		</div>
	)
}
