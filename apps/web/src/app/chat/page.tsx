'use client'

import { useState, useRef, useEffect, useCallback } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { useCurrentUser } from "@/hooks/useCurrentUser"
import { api } from "@/lib/api-client"
import { UserButton } from "@clerk/nextjs"
import ChatSidebar from "@/components/ChatSidebar"
import Link from "next/link"
import {
  MapPinIcon,
  BanknotesIcon,
  HomeModernIcon,
  CalendarIcon,
  XMarkIcon,
  PaperAirplaneIcon,
  SparklesIcon,
} from "@heroicons/react/24/outline"

interface Property {
  _id: string
  title: string
  price: number
  city: string
  bedrooms: number
  bathrooms: number
  area_sqft: number
  images?: string[]
  property_type: string
  score?: number
}

interface Builder {
  _id: string
  company_name: string
  specialization: string[]
  experience_years: number
  rating?: number
  location?: {
    city: string
  }
  about?: string
  score?: number
}

interface Message {
  id: string
  content: string
  sender: "user" | "ai"
  timestamp: Date
  properties?: Property[]
  builders?: Builder[]
}

export default function ChatPage() {
  const { user, isAuthenticated, userId, clerkId } = useCurrentUser()
  const dbUserId = (user as any)?._id || userId || null
  const searchParams = useSearchParams()
  const router = useRouter()
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL as string | undefined
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      content:
        "Welcome to PropPal AI! I'm here to help you find your perfect property or connect with builders. Ask me to find houses in specific cities, search by price range, or discover construction companies.",
      sender: "ai",
      timestamp: new Date(),
    },
  ])
  const [inputMessage, setInputMessage] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const hasProcessedQueryRef = useRef(false)
  const [sidebarRefresh, setSidebarRefresh] = useState(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const [interactiveActive, setInteractiveActive] = useState(false)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null)
  const [isPropertyModalOpen, setIsPropertyModalOpen] = useState(false)
  const [isLightboxOpen, setIsLightboxOpen] = useState(false)
  const [currentImageIndex, setCurrentImageIndex] = useState(0)
  const [selectedBuilder, setSelectedBuilder] = useState<Builder | null>(null)
  const [isBuilderModalOpen, setIsBuilderModalOpen] = useState(false)

  const openPropertyModal = (property: Property) => {
    setSelectedProperty(property)
    setIsPropertyModalOpen(true)
  }

  const closePropertyModal = () => {
    setIsPropertyModalOpen(false)
    setSelectedProperty(null)
  }

  useEffect(() => {
    const anyOverlayOpen = isPropertyModalOpen || isLightboxOpen || isBuilderModalOpen
    if (!anyOverlayOpen) {
      document.body.style.overflow = ""
      return
    }
    document.body.style.overflow = "hidden"

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (isLightboxOpen) {
          setIsLightboxOpen(false)
        } else if (isPropertyModalOpen) {
          closePropertyModal()
        } else if (isBuilderModalOpen) {
          setIsBuilderModalOpen(false)
        }
      }
      if (isLightboxOpen && selectedProperty?.images && selectedProperty.images.length > 1) {
        if (e.key === "ArrowRight") {
          setCurrentImageIndex((prev) => (prev + 1) % selectedProperty.images!.length)
        } else if (e.key === "ArrowLeft") {
          setCurrentImageIndex((prev) => (prev - 1 + selectedProperty.images!.length) % selectedProperty.images!.length)
        }
      }
    }
    window.addEventListener("keydown", onKeyDown)
    return () => {
      window.removeEventListener("keydown", onKeyDown)
      document.body.style.overflow = ""
    }
  }, [isPropertyModalOpen, isLightboxOpen, isBuilderModalOpen, selectedProperty])

  useEffect(() => {
    if (isPropertyModalOpen || isLightboxOpen) {
      setCurrentImageIndex(0)
    }
  }, [isPropertyModalOpen, isLightboxOpen, selectedProperty])

  const showNextImage = () => {
    if (!selectedProperty?.images || selectedProperty.images.length === 0) return
    setCurrentImageIndex((prev) => (prev + 1) % selectedProperty.images!.length)
  }

  const showPrevImage = () => {
    if (!selectedProperty?.images || selectedProperty.images.length === 0) return
    setCurrentImageIndex((prev) => (prev - 1 + selectedProperty.images!.length) % selectedProperty.images!.length)
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    try {
      const key = "chat_session_id"
      let sid = typeof window !== "undefined" ? window.localStorage.getItem(key) : null
      if (!sid) {
        sid = `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
        window.localStorage.setItem(key, sid)
      }
      setSessionId(sid)
    } catch {
      setSessionId("session_fallback")
    }
  }, [])

  const sendMessage = useCallback(
    async (messageText: string, clearInput = false) => {
      if (!messageText.trim()) return

      const userMessage: Message = {
        id: Date.now().toString(),
        content: messageText,
        sender: "user",
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, userMessage])
      if (clearInput) {
        setInputMessage("")
      }
      setIsLoading(true)

      try {
        const response = (await api.chat.sendMessage(
          messageText,
          dbUserId || undefined,
          sessionId || "session_fallback",
          clerkId || undefined,
        )) as {
          response: string
          classification: string
          properties?: Property[]
          builders?: Builder[]
          start_interactive?: { type: "service" | "profile"; ws_path: string; clerk_id_required?: boolean }
        }

        const handoffMessages = [
          "Starting service creation. Please connect via websocket to continue.",
          "Starting builder profile creation. Please connect via websocket to continue.",
        ]
        const si = (response as any).start_interactive as { type: "service" | "profile"; ws_path: string } | undefined
        const isHandoff = handoffMessages.includes(response.response)

        let wsPath: string | null = null
        if (si?.ws_path) {
          wsPath = si.ws_path
        } else if (isHandoff) {
          if (response.response.includes("service creation")) {
            wsPath = "/api/chat/ws/service/create"
          } else if (response.response.includes("builder profile creation")) {
            wsPath = "/api/chat/ws/profile/create"
          }
        }

        if (wsPath && API_BASE_URL) {
          let wsOrigin: string
          try {
            const urlObj = new URL(API_BASE_URL)
            wsOrigin = (urlObj.protocol === "https:" ? "wss://" : "ws://") + urlObj.host
          } catch {
            const baseNoSlash = API_BASE_URL.replace(/\/$/, "")
            wsOrigin = baseNoSlash.replace(/^http:/, "ws:").replace(/^https:/, "wss:")
          }
          const qs = `?clerk_id=${encodeURIComponent(clerkId || "")}`
          const wsUrl = `${wsOrigin}${wsPath}${qs}`
          try {
            const ws = new WebSocket(wsUrl)
            wsRef.current = ws
            setInteractiveActive(true)

            ws.onopen = () => {
              try {
                ws.send(JSON.stringify({ type: "user", text: messageText }))
              } catch {}
            }

            ws.onmessage = (evt) => {
              try {
                const payload = JSON.parse(evt.data)
                if (payload.type === "agent") {
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: `${Date.now()}-agent`,
                      content: String(payload.text || ""),
                      sender: "ai",
                      timestamp: new Date(),
                    },
                  ])
                } else if (payload.type === "completed") {
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: `${Date.now()}-done`,
                      content: String(payload.message || "Completed"),
                      sender: "ai",
                      timestamp: new Date(),
                    },
                  ])
                  ws.close()
                  wsRef.current = null
                  setInteractiveActive(false)
                } else if (payload.type === "error") {
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: `${Date.now()}-err`,
                      content: `Error: ${String(payload.message || "Unknown error")}`,
                      sender: "ai",
                      timestamp: new Date(),
                    },
                  ])
                  ws.close()
                  wsRef.current = null
                  setInteractiveActive(false)
                }
              } catch {
                // ignore malformed
              }
            }

            ws.onerror = () => {
              setMessages((prev) => [
                ...prev,
                {
                  id: `${Date.now()}-wserr`,
                  content: "Connection error during interactive flow.",
                  sender: "ai",
                  timestamp: new Date(),
                },
              ])
              wsRef.current = null
              setInteractiveActive(false)
            }

            ws.onclose = () => {
              wsRef.current = null
              setInteractiveActive(false)
            }
          } catch (e) {
            setMessages((prev) => [
              ...prev,
              {
                id: `${Date.now()}-wsex`,
                content: "Failed to start interactive flow.",
                sender: "ai",
                timestamp: new Date(),
              },
            ])
          }
        } else if (!isHandoff) {
          const aiResponse: Message = {
            id: (Date.now() + 1).toString(),
            content: response.response,
            sender: "ai",
            timestamp: new Date(),
            properties: response.properties,
            builders: response.builders,
          }
          setMessages((prev) => [...prev, aiResponse])
          setSidebarRefresh((v) => v + 1)
        }
      } catch (error) {
        console.error("Chat API error:", error)
        const errorResponse: Message = {
          id: (Date.now() + 1).toString(),
          content: "Sorry, I encountered an error. Please try again.",
          sender: "ai",
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, errorResponse])
      } finally {
        setIsLoading(false)
      }
    },
    [dbUserId, clerkId, API_BASE_URL, sessionId],
  )

  useEffect(() => {
    const loadHistory = async () => {
      if (!dbUserId) return
      try {
        const res = (await api.chat.history(dbUserId, undefined, 50)) as any
        const serverMessages = (res?.messages || []) as Array<any>
        if (serverMessages.length === 0) return
        const mapped: Message[] = serverMessages.map((m: any, idx: number) => ({
          id: `${m.timestamp || "ts"}-${idx}`,
          content: String(m.content || ""),
          sender: m.role === "user" ? "user" : "ai",
          timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
          properties: m._payload?.properties as Property[] | undefined,
          builders: m._payload?.builders as Builder[] | undefined,
        }))
        setMessages((prev) => (prev.length <= 1 ? mapped : prev))
      } catch (e) {
        // ignore history load errors
      }
    }
    loadHistory()
  }, [dbUserId])

  useEffect(() => {
    const query = searchParams.get("q")
    if (query && !hasProcessedQueryRef.current && user && sendMessage) {
      hasProcessedQueryRef.current = true
      setInputMessage(query)
      router.replace("/chat")
      sendMessage(query, false)
    }
  }, [searchParams, user, router, sendMessage])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (interactiveActive && wsRef.current) {
      const text = inputMessage
      if (!text.trim()) return
      setMessages((prev) => [
        ...prev,
        { id: Date.now().toString(), content: text, sender: "user", timestamp: new Date() },
      ])
      try {
        wsRef.current.send(JSON.stringify({ type: "user", text }))
      } catch {}
      setInputMessage("")
      return
    }
    sendMessage(inputMessage, true)
  }

  const suggestedQuestions = [
    "Find houses in Islamabad",
    "Show me apartments in Karachi",
    "Find properties under 50 lakhs",
    "Show me 3 bedroom houses",
    "Find construction companies in Lahore",
    "Show me renovation services",
    "Find builders for home construction",
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-50">
      <header className="bg-white/80 backdrop-blur-md border-b border-slate-200/50 sticky top-0 z-40 px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center space-x-2 text-slate-900 hover:text-slate-700 transition-colors">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-teal-500 to-cyan-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">P</span>
            </div>
            <span className="text-xl font-bold">PropPal</span>
          </Link>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-slate-600">
              <SparklesIcon className="w-4 h-4 text-teal-500" />
              <span className="text-sm font-medium">AI Assistant</span>
            </div>
            {isAuthenticated && <UserButton afterSignOutUrl="/" />}
          </div>
        </div>
      </header>

      {/* Chat Container */}
      <div className="max-w-7xl mx-auto h-[calc(100vh-64px)] px-2 md:px-4 py-4">
        <div className="flex h-full rounded-2xl bg-white border border-slate-200/50 overflow-hidden shadow-lg">
          <ChatSidebar
            userId={dbUserId || undefined}
            sessionId={sessionId}
            activeSessionId={sessionId}
            onNewSession={(sid) => {
              setSessionId(sid)
              setSidebarRefresh((v) => v + 1)
            }}
            refreshKey={sidebarRefresh}
          />

          <div className="flex flex-col flex-1">
            <div className="flex-1 overflow-y-auto p-6 space-y-5 bg-gradient-to-b from-white via-slate-50/50 to-white">
              {messages.map((message) => {
                const hasProperties = message.properties && message.properties.length > 0
                const hasBuilders = message.builders && message.builders.length > 0
                const showTextMessage = !hasProperties && !hasBuilders

                return (
                  <div key={message.id} className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                    {showTextMessage && (
                      <div className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}>
                        <div
                          className={`flex max-w-2xl ${message.sender === "user" ? "flex-row-reverse" : "flex-row"}`}
                        >
                          <div
                            className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold ${
                              message.sender === "user"
                                ? "bg-gradient-to-br from-teal-500 to-cyan-600 text-white ml-3"
                                : "bg-slate-200 text-slate-700 mr-3"
                            }`}
                          >
                            {message.sender === "user" ? "U" : "AI"}
                          </div>

                          <div
                            className={`rounded-2xl px-5 py-3.5 ${
                              message.sender === "user"
                                ? "bg-gradient-to-br from-teal-500 to-cyan-600 text-white shadow-md"
                                : "bg-slate-100 text-slate-900 shadow-sm border border-slate-200/50"
                            }`}
                          >
                            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
                            <p
                              className={`text-xs mt-2 ${
                                message.sender === "user" ? "text-teal-100" : "text-slate-500"
                              }`}
                              suppressHydrationWarning
                            >
                              {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}

                    {message.sender === "ai" && message.properties && message.properties.length > 0 && (
                      <div className="w-full max-w-6xl">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                          {message.properties.map((property) => (
                            <div
                              key={property._id}
                              className="bg-white rounded-xl shadow-sm border border-slate-200/50 overflow-hidden hover:shadow-lg hover:border-slate-300 transition-all duration-300 cursor-pointer flex flex-col h-full group"
                            >
                              {/* Property Image */}
                              <div className="h-40 bg-gradient-to-br from-slate-200 to-slate-300 flex items-center justify-center overflow-hidden flex-shrink-0 relative">
                                {property.images && property.images.length > 0 ? (
                                  <img
                                    src={property.images[0] || "/placeholder.svg"}
                                    alt={property.title}
                                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                    onError={(e) => {
                                      const target = e.currentTarget as HTMLElement
                                      target.style.display = "none"
                                      const nextSibling = target.nextElementSibling as HTMLElement
                                      if (nextSibling) {
                                        nextSibling.style.display = "flex"
                                      }
                                    }}
                                  />
                                ) : null}
                                <div
                                  className={`h-full w-full flex items-center justify-center ${property.images && property.images.length > 0 ? "hidden" : "flex"}`}
                                >
                                  <HomeModernIcon className="h-12 w-12 text-slate-400" />
                                </div>
                              </div>

                              {/* Property Details */}
                              <div className="p-4 flex flex-col flex-grow">
                                <h3 className="font-semibold text-base text-slate-900 mb-2 line-clamp-2">
                                  {property.title}
                                </h3>

                                {/* Price */}
                                <div className="flex items-center mb-3">
                                  <BanknotesIcon className="h-4 w-4 text-teal-600 mr-2" />
                                  <span className="text-lg font-bold text-teal-600">
                                    Rs {property.price.toLocaleString()}
                                  </span>
                                </div>

                                {/* Location */}
                                <div className="flex items-center mb-3">
                                  <MapPinIcon className="h-4 w-4 text-slate-500 mr-2" />
                                  <span className="text-sm text-slate-600">{property.city}</span>
                                </div>

                                {/* Property Stats */}
                                <div className="flex items-center justify-between mb-3 text-xs text-slate-600 bg-slate-50 rounded-lg p-2">
                                  <span>{property.bedrooms} bed</span>
                                  <span className="text-slate-300">•</span>
                                  <span>{property.bathrooms} bath</span>
                                  <span className="text-slate-300">•</span>
                                  <span>{property.area_sqft} sqft</span>
                                </div>

                                {/* Property Type & Score */}
                                <div className="flex items-center justify-between mb-3 text-xs">
                                  <span className="text-slate-500">{property.property_type}</span>
                                  {property.score && (
                                    <div className="flex items-center">
                                      <span className="bg-teal-100 text-teal-700 px-2 py-1 rounded-full text-xs font-medium">
                                        {Math.round(property.score * 100)}%
                                      </span>
                                    </div>
                                  )}
                                </div>

                                {/* Action Buttons */}
                                <div className="flex space-x-2 mt-auto pt-3">
                                  <button
                                    onClick={() => openPropertyModal(property)}
                                    className="flex-1 bg-gradient-to-r from-teal-500 to-cyan-600 text-white py-2 px-3 rounded-lg text-sm font-medium hover:shadow-md transition-all"
                                  >
                                    View Details
                                  </button>
                                  <button className="flex-1 border border-slate-300 text-slate-700 py-2 px-3 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors">
                                    Contact
                                  </button>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {message.sender === "ai" && message.builders && message.builders.length > 0 && (
                      <div className="w-full max-w-6xl">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                          {message.builders.map((builder) => (
                            <div
                              key={builder._id}
                              className="bg-white rounded-xl shadow-sm border border-slate-200/50 overflow-hidden hover:shadow-lg hover:border-slate-300 transition-all duration-300 cursor-pointer flex flex-col h-full group"
                            >
                              {/* Builder Header */}
                              <div className="h-40 bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center flex-shrink-0 relative">
                                <div className="text-center text-white">
                                  <HomeModernIcon className="h-12 w-12 mx-auto mb-2 opacity-90" />
                                  <h3 className="text-sm font-semibold line-clamp-2 px-2">{builder.company_name}</h3>
                                </div>
                              </div>

                              {/* Builder Details */}
                              <div className="p-4 flex flex-col flex-grow">
                                <h3 className="font-semibold text-base text-slate-900 mb-2 line-clamp-2">
                                  {builder.company_name}
                                </h3>

                                {/* Specialization Tags */}
                                <div className="flex flex-wrap gap-1.5 mb-3">
                                  {builder.specialization.slice(0, 2).map((spec, index) => (
                                    <span
                                      key={index}
                                      className="bg-amber-100 text-amber-700 px-2 py-1 rounded-full text-xs font-medium"
                                    >
                                      {spec}
                                    </span>
                                  ))}
                                </div>

                                {/* Experience & Rating */}
                                <div className="flex items-center justify-between mb-3 text-sm">
                                  <div className="flex items-center text-slate-600">
                                    <CalendarIcon className="h-4 w-4 mr-1" />
                                    <span>{builder.experience_years}y exp</span>
                                  </div>
                                  {builder.rating && (
                                    <div className="flex items-center">
                                      <span className="text-yellow-500">★</span>
                                      <span className="text-sm text-slate-600 ml-1">{builder.rating}</span>
                                    </div>
                                  )}
                                </div>

                                {/* Location */}
                                {builder.location && (
                                  <div className="flex items-center mb-3 text-sm text-slate-600">
                                    <MapPinIcon className="h-4 w-4 mr-1" />
                                    <span>{builder.location.city}</span>
                                  </div>
                                )}

                                {/* Score */}
                                {builder.score && (
                                  <div className="flex items-center justify-between mb-3 text-xs">
                                    <span className="text-slate-500">Match</span>
                                    <span className="bg-amber-100 text-amber-700 px-2 py-1 rounded-full font-medium">
                                      {Math.round(builder.score * 100)}%
                                    </span>
                                  </div>
                                )}

                                {/* Action Buttons */}
                                <div className="flex space-x-2 mt-auto pt-3">
                                  <Link
                                    href={`/builders/${builder._id}`}
                                    className="flex-1 bg-gradient-to-r from-amber-500 to-orange-600 text-white py-2 px-3 rounded-lg text-sm font-medium hover:shadow-md transition-all text-center"
                                  >
                                    View Profile
                                  </Link>
                                  <button className="flex-1 border border-slate-300 text-slate-700 py-2 px-3 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors">
                                    Contact
                                  </button>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-slate-100 rounded-2xl px-5 py-3.5 shadow-sm border border-slate-200/50">
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                      <div
                        className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
                        style={{ animationDelay: "0.1s" }}
                      ></div>
                      <div
                        className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
                        style={{ animationDelay: "0.2s" }}
                      ></div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Property Details Modal */}
            {isPropertyModalOpen && selectedProperty && (
              <div
                className="fixed inset-0 z-50 flex items-center justify-center"
                role="dialog"
                aria-modal="true"
                aria-labelledby="property-modal-title"
                onClick={closePropertyModal}
              >
                <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" />
                <div
                  className="relative bg-white rounded-2xl shadow-xl w-full max-w-4xl mx-4 overflow-hidden border border-slate-200"
                  onClick={(e) => e.stopPropagation()}
                >
                  {/* Header */}
                  <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
                    <h2 id="property-modal-title" className="text-lg font-semibold text-gray-900">
                      {selectedProperty.title}
                    </h2>
                    <button
                      aria-label="Close"
                      onClick={closePropertyModal}
                      className="p-2 rounded-lg hover:bg-slate-100 transition-colors"
                    >
                      <XMarkIcon className="w-5 h-5 text-slate-600" />
                    </button>
                  </div>

                  {/* Body */}
                  <div className="p-5 space-y-4">
                    {/* Image Slider */}
                    <div className="w-full">
                      <div
                        className="relative h-80 w-full bg-slate-100 rounded-xl overflow-hidden flex items-center justify-center cursor-zoom-in"
                        onClick={() => {
                          if (selectedProperty?.images && selectedProperty.images.length > 0) {
                            setIsLightboxOpen(true)
                          }
                        }}
                      >
                        {selectedProperty.images && selectedProperty.images.length > 0 ? (
                          <img
                            src={selectedProperty.images[currentImageIndex] || "/placeholder.svg"}
                            alt={selectedProperty.title}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              const target = e.currentTarget as HTMLElement
                              target.style.display = "none"
                            }}
                          />
                        ) : (
                          <HomeModernIcon className="h-14 w-14 text-slate-400" />
                        )}

                        {selectedProperty.images && selectedProperty.images.length > 1 && (
                          <>
                            {/* Prev */}
                            <button
                              type="button"
                              onClick={showPrevImage}
                              className="absolute left-2 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white text-gray-700 rounded-full w-9 h-9 flex items-center justify-center shadow-sm"
                              aria-label="Previous image"
                            >
                              ‹
                            </button>
                            {/* Next */}
                            <button
                              type="button"
                              onClick={showNextImage}
                              className="absolute right-2 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white text-gray-700 rounded-full w-9 h-9 flex items-center justify-center shadow-sm"
                              aria-label="Next image"
                            >
                              ›
                            </button>
                          </>
                        )}
                      </div>

                      {selectedProperty.images && selectedProperty.images.length > 1 && (
                        <div className="flex items-center justify-center gap-2 mt-3">
                          {selectedProperty.images.map((_, idx) => (
                            <button
                              key={idx}
                              aria-label={`Go to image ${idx + 1}`}
                              className={`w-2.5 h-2.5 rounded-full ${idx === currentImageIndex ? "bg-indigo-600" : "bg-slate-300"} transition-colors`}
                              onClick={() => setCurrentImageIndex(idx)}
                            />
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Price */}
                    <div className="flex items-center">
                      <BanknotesIcon className="h-5 w-5 text-green-600 mr-2" />
                      <span className="text-2xl font-bold text-green-600">
                        Rs {selectedProperty.price.toLocaleString()}
                      </span>
                    </div>

                    {/* Meta */}
                    <div className="grid grid-cols-2 gap-3 text-sm text-gray-700">
                      <div className="flex items-center">
                        <MapPinIcon className="h-4 w-4 text-gray-500 mr-2" />
                        <span>{selectedProperty.city}</span>
                      </div>
                      <div className="flex items-center justify-start gap-4">
                        <span>{selectedProperty.bedrooms} bed</span>
                        <span>{selectedProperty.bathrooms} bath</span>
                        <span>{selectedProperty.area_sqft} sqft</span>
                      </div>
                      <div className="col-span-2 flex items-center justify-between">
                        <span className="text-xs uppercase tracking-wide text-gray-500">
                          {selectedProperty.property_type}
                        </span>
                        {selectedProperty.score && (
                          <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                            Match: {Math.round(selectedProperty.score * 100)}%
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="px-5 py-4 border-t border-slate-200 flex justify-end gap-2">
                    <Link
                      href={`/properties/${selectedProperty._id}`}
                      className="px-4 py-2 rounded-xl border border-indigo-600 text-indigo-600 hover:bg-indigo-50 transition-colors"
                    >
                      View Full Details
                    </Link>
                    <button
                      onClick={closePropertyModal}
                      className="px-4 py-2 rounded-xl border border-slate-300 text-gray-700 hover:bg-slate-50 transition-colors"
                    >
                      Close
                    </button>
                    <button className="px-4 py-2 rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 transition-colors">
                      Contact Agent
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Builder Details Modal */}
            {isBuilderModalOpen && selectedBuilder && (
              <div
                className="fixed inset-0 z-50 flex items-center justify-center"
                role="dialog"
                aria-modal="true"
                aria-labelledby="builder-modal-title"
                onClick={() => setIsBuilderModalOpen(false)}
              >
                <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" />
                <div
                  className="relative bg-white rounded-2xl shadow-xl w-full max-w-3xl mx-4 overflow-hidden border border-slate-200"
                  onClick={(e) => e.stopPropagation()}
                >
                  {/* Header */}
                  <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
                    <h2 id="builder-modal-title" className="text-lg font-semibold text-gray-900">
                      {selectedBuilder.company_name}
                    </h2>
                    <button
                      aria-label="Close"
                      onClick={() => setIsBuilderModalOpen(false)}
                      className="p-2 rounded-lg hover:bg-slate-100 transition-colors"
                    >
                      <XMarkIcon className="w-5 h-5 text-slate-600" />
                    </button>
                  </div>

                  {/* Body */}
                  <div className="p-5 space-y-5">
                    {/* Top Summary */}
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-3">
                          <div className="w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center">
                            <HomeModernIcon className="h-6 w-6 text-amber-700" />
                          </div>
                          <div>
                            <h3 className="text-xl font-semibold text-gray-900">{selectedBuilder.company_name}</h3>
                            {selectedBuilder.location?.city && (
                              <div className="flex items-center text-sm text-gray-600 mt-1">
                                <MapPinIcon className="h-4 w-4 mr-1" />
                                <span>{selectedBuilder.location.city}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-sm text-gray-700 flex items-center">
                          <CalendarIcon className="h-4 w-4 mr-1" />
                          <span>{selectedBuilder.experience_years} years</span>
                        </div>
                        {selectedBuilder.rating && (
                          <div className="text-sm text-gray-700 flex items-center">
                            <span className="text-yellow-500">★</span>
                            <span className="ml-1">{selectedBuilder.rating}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Specializations */}
                    {selectedBuilder.specialization && selectedBuilder.specialization.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Specializations</h4>
                        <div className="flex flex-wrap gap-2">
                          {selectedBuilder.specialization.map((spec, idx) => (
                            <span key={idx} className="bg-amber-100 text-amber-800 px-2 py-1 rounded-full text-xs">
                              {spec}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* About */}
                    {selectedBuilder.about && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-2">About</h4>
                        <p className="text-sm text-gray-700 leading-relaxed">{selectedBuilder.about}</p>
                      </div>
                    )}

                    {/* Score */}
                    {selectedBuilder.score && (
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-500">Match</span>
                        <span className="bg-amber-100 text-amber-800 px-2 py-1 rounded">{Math.round(selectedBuilder.score * 100)}%</span>
                      </div>
                    )}
                  </div>

                  {/* Footer */}
                  <div className="px-5 py-4 border-t border-slate-200 flex justify-end gap-2">
                    <Link
                      href={`/builders/${selectedBuilder._id}`}
                      className="px-4 py-2 rounded-xl border border-amber-600 text-amber-700 hover:bg-amber-50 transition-colors"
                    >
                      View Full Profile
                    </Link>
                    <button
                      onClick={() => setIsBuilderModalOpen(false)}
                      className="px-4 py-2 rounded-xl border border-slate-300 text-gray-700 hover:bg-slate-50 transition-colors"
                    >
                      Close
                    </button>
                    <button className="px-4 py-2 rounded-xl bg-amber-600 text-white hover:bg-amber-700 transition-colors">
                      Contact
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Fullscreen Lightbox */}
            {isLightboxOpen && selectedProperty?.images && selectedProperty.images.length > 0 && (
              <div
                className="fixed inset-0 z-[60] bg-black/90 flex items-center justify-center"
                role="dialog"
                aria-modal="true"
                aria-label="Image lightbox"
                onClick={() => setIsLightboxOpen(false)}
              >
                <div className="relative w-full h-full max-w-6xl mx-auto px-6" onClick={(e) => e.stopPropagation()}>
                  <button
                    aria-label="Close"
                    onClick={() => setIsLightboxOpen(false)}
                    className="absolute top-6 right-6 p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white"
                  >
                    <XMarkIcon className="w-6 h-6" />
                  </button>

                  <div className="h-[75vh] mt-16 relative flex items-center justify-center">
                    <img
                      src={selectedProperty.images[currentImageIndex] || "/placeholder.svg"}
                      alt={selectedProperty.title}
                      className="max-h-full max-w-full object-contain"
                    />

                    {selectedProperty.images.length > 1 && (
                      <>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            setCurrentImageIndex(
                              (prev) => (prev - 1 + selectedProperty.images!.length) % selectedProperty.images!.length,
                            )
                          }}
                          className="absolute left-2 md:left-6 top-1/2 -translate-y-1/2 bg-white/15 hover:bg-white/25 text-white rounded-full w-10 h-10 flex items-center justify-center"
                          aria-label="Previous image"
                        >
                          ‹
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            setCurrentImageIndex((prev) => (prev + 1) % selectedProperty.images!.length)
                          }}
                          className="absolute right-2 md:right-6 top-1/2 -translate-y-1/2 bg-white/15 hover:bg-white/25 text-white rounded-full w-10 h-10 flex items-center justify-center"
                          aria-label="Next image"
                        >
                          ›
                        </button>
                      </>
                    )}
                  </div>

                  {selectedProperty.images.length > 1 && (
                    <div className="flex items-center justify-center gap-2 mt-6">
                      {selectedProperty.images.map((_, idx) => (
                        <button
                          key={idx}
                          aria-label={`Go to image ${idx + 1}`}
                          className={`w-2.5 h-2.5 rounded-full ${idx === currentImageIndex ? "bg-white" : "bg-white/40"} transition-colors`}
                          onClick={() => setCurrentImageIndex(idx)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {messages.length === 1 && (
              <div className="px-6 pb-4">
                <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl p-4 border border-slate-200/50">
                  <h3 className="text-xs font-semibold text-slate-700 mb-3 uppercase tracking-wide">
                    Suggested Questions
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {suggestedQuestions.map((question, index) => (
                      <button
                        key={index}
                        onClick={() => setInputMessage(question)}
                        className="text-left p-3 text-sm text-slate-700 hover:bg-white hover:border-slate-300 rounded-lg transition-all border border-transparent"
                      >
                        <span className="text-teal-600 mr-2">→</span>
                        {question}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div className="p-6 bg-white border-t border-slate-200/50">
              <form onSubmit={handleSendMessage} className="flex space-x-3">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder="Ask about properties, builders, or search listings..."
                  className="flex-1 px-5 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-transparent text-slate-900 placeholder:text-slate-400 transition-all"
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  disabled={!inputMessage.trim() || isLoading}
                  className="bg-gradient-to-r from-teal-500 to-cyan-600 text-white px-6 py-3 rounded-xl hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-all flex items-center space-x-2"
                >
                  <PaperAirplaneIcon className="w-4 h-4" />
                  <span>Send</span>
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

