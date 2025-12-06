'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { api } from '@/lib/api-client'
import { UserButton } from '@clerk/nextjs'
import ChatSidebar from '@/components/ChatSidebar'
import Link from 'next/link'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  MapPinIcon,
  MagnifyingGlassIcon,
  BanknotesIcon,
  HomeModernIcon,
  CalendarIcon,
  PaperAirplaneIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import PropertyModal from '@/components/modals/PropertyModal'
import BuilderModal from '@/components/modals/BuilderModal'
import ServiceModal from '@/components/modals/ServiceModal'
import ImageLightbox from '@/components/modals/ImageLightbox'
import { motion } from 'framer-motion'
import QuickSuggestions from '@/components/QuickSuggestions'

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
  portfolio_images?: string[]
}

interface ServiceResult {
  _id?: string
  service_name?: string
  title?: string
  description?: string
  category?: string
  base_price?: number
  price_unit?: string
  price_range_min?: number
  price_range_max?: number
  estimated_duration?: string
  service_features?: string[]
  service_images?: string[]
  builder_id?: string
  score?: number
}

interface Message {
  id: string
  content: string
  sender: 'user' | 'ai'
  timestamp: Date
  properties?: Property[]
  builders?: Builder[]
  services?: ServiceResult[]
}

export default function ChatPage() {
  const { user, isAuthenticated, userId, clerkId } = useCurrentUser()
  const dbUserId = (user as any)?._id || userId || null
  const searchParams = useSearchParams()
  const router = useRouter()
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL as string | undefined
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content:
        "Welcome to PropPal AI! I'm here to help you find your perfect property or connect with builders. Ask me to find houses in specific cities, search by price range, or discover construction companies.",
      sender: 'ai',
      timestamp: new Date(),
    },
  ])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const hasProcessedQueryRef = useRef(false)
  const [sidebarRefresh, setSidebarRefresh] = useState(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const [interactiveActive, setInteractiveActive] = useState(false)
  const [creationType, setCreationType] = useState<'profile' | 'service' | null>(null)
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const typingTimerRef = useRef<NodeJS.Timeout | null>(null)
  const [wsConnected, setWsConnected] = useState(false)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null)
  const [isPropertyModalOpen, setIsPropertyModalOpen] = useState(false)
  const [isLightboxOpen, setIsLightboxOpen] = useState(false)
  const [currentImageIndex, setCurrentImageIndex] = useState(0)
  const [selectedBuilder, setSelectedBuilder] = useState<Builder | null>(null)
  const [isBuilderModalOpen, setIsBuilderModalOpen] = useState(false)
  const [selectedService, setSelectedService] = useState<ServiceResult | null>(null)
  const [isServiceModalOpen, setIsServiceModalOpen] = useState(false)

  const openPropertyModal = (property: Property) => {
    setSelectedProperty(property)
    setIsPropertyModalOpen(true)
  }

  const closePropertyModal = () => {
    setIsPropertyModalOpen(false)
    setSelectedProperty(null)
  }

  const openBuilderModal = (builder: Builder) => {
    setSelectedBuilder(builder)
    setIsBuilderModalOpen(true)
  }

  const closeBuilderModal = () => {
    setIsBuilderModalOpen(false)
    setSelectedBuilder(null)
  }

  const openServiceModal = (service: ServiceResult) => {
    setSelectedService(service)
    setIsServiceModalOpen(true)
  }

  const closeServiceModal = () => {
    setIsServiceModalOpen(false)
    setSelectedService(null)
  }

  const fetchAndOpenBuilderModal = async (builderId: string) => {
    try {
      setIsLoading(true)
      const builder = (await api.builders.getById(builderId)) as Builder
      openBuilderModal(builder)
    } catch (error) {
      console.error('Failed to fetch builder:', error)
      // Show error message to user
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-error`,
          content: 'Failed to load builder details. Please try again.',
          sender: 'ai',
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    const anyOverlayOpen =
      isPropertyModalOpen || isLightboxOpen || isBuilderModalOpen || isServiceModalOpen
    if (!anyOverlayOpen) {
      document.body.style.overflow = ''
      return
    }
    document.body.style.overflow = 'hidden'

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (isLightboxOpen) {
          setIsLightboxOpen(false)
        } else if (isPropertyModalOpen) {
          closePropertyModal()
        } else if (isServiceModalOpen) {
          closeServiceModal()
        } else if (isBuilderModalOpen) {
          setIsBuilderModalOpen(false)
        }
      }
      if (isLightboxOpen && selectedProperty?.images && selectedProperty.images.length > 1) {
        if (e.key === 'ArrowRight') {
          setCurrentImageIndex((prev) => (prev + 1) % selectedProperty.images!.length)
        } else if (e.key === 'ArrowLeft') {
          setCurrentImageIndex(
            (prev) =>
              (prev - 1 + selectedProperty.images!.length) % selectedProperty.images!.length,
          )
        }
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = ''
    }
  }, [
    isPropertyModalOpen,
    isLightboxOpen,
    isBuilderModalOpen,
    isServiceModalOpen,
    selectedProperty,
  ])

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
    setCurrentImageIndex(
      (prev) => (prev - 1 + selectedProperty.images!.length) % selectedProperty.images!.length,
    )
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    try {
      const key = 'chat_session_id'
      let sid = typeof window !== 'undefined' ? window.localStorage.getItem(key) : null
      if (!sid) {
        sid = `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
        window.localStorage.setItem(key, sid)
      }
      setSessionId(sid)
    } catch {
      setSessionId('session_fallback')
    }
  }, [])

  // Unified WebSocket connection setup
  useEffect(() => {
    // Don't connect if no API URL or clerk ID
    if (!API_BASE_URL || !clerkId) {
      console.log('⏳ Waiting for API URL and Clerk ID...')
      return
    }

    // Don't connect if session ID is not ready
    if (!sessionId) {
      console.log('⏳ Waiting for session ID...')
      return
    }

    // Create WebSocket URL
    let wsOrigin: string
    try {
      const urlObj = new URL(API_BASE_URL)
      wsOrigin = (urlObj.protocol === 'https:' ? 'wss://' : 'ws://') + urlObj.host
    } catch (error) {
      console.error('Invalid API_BASE_URL:', API_BASE_URL)
      const baseNoSlash = API_BASE_URL.replace(/\/$/, '')
      wsOrigin = baseNoSlash.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:')
    }

    const wsUrl = `${wsOrigin}/api/chat/ws?clerk_id=${encodeURIComponent(clerkId)}&session_id=${encodeURIComponent(sessionId)}`
    console.log('🔌 Connecting to WebSocket:', wsUrl)

    const connectWebSocket = () => {
      try {
        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onopen = () => {
          console.log('✅ WebSocket connected successfully')
          setWsConnected(true)
          setIsLoading(false)
        }

        ws.onmessage = (evt) => {
          try {
            const data = JSON.parse(evt.data)
            console.log('📩 Received:', data)

            if (data.type === 'agent') {
              if (data.interactive_mode) {
                setInteractiveActive(true)
                const metaType =
                  data.metadata?.agent_type ||
                  (data.classification === 'builder_create_profile'
                    ? 'profile'
                    : data.classification === 'builder_create_service'
                      ? 'service'
                      : null)
                if (metaType === 'profile' || metaType === 'service') {
                  setCreationType(metaType)
                }
              }

              // Add AI message
              const aiMessage: Message = {
                id: `${Date.now()}-agent`,
                content: data.message || '',
                sender: 'ai',
                timestamp: new Date(),
                properties: data.properties,
                builders: data.builders,
                services: data.services,
              }
              setMessages((prev) => [...prev, aiMessage])
              setIsLoading(false)
              setSidebarRefresh((v) => v + 1)
            } else if (data.type === 'completed') {
              // Interactive flow completed
              const completedMessage: Message = {
                id: `${Date.now()}-completed`,
                content: data.message || 'Completed successfully!',
                sender: 'ai',
                timestamp: new Date(),
              }
              setMessages((prev) => [...prev, completedMessage])
              setInteractiveActive(false)
              setCreationType(null)
              setIsLoading(false)
              setSidebarRefresh((v) => v + 1)
            } else if (data.type === 'error') {
              // Error response
              const errorMessage: Message = {
                id: `${Date.now()}-error`,
                content: `Error: ${data.message || 'Unknown error'}`,
                sender: 'ai',
                timestamp: new Date(),
              }
              setMessages((prev) => [...prev, errorMessage])
              setInteractiveActive(false)
              setCreationType(null)
              setIsLoading(false)
            }
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e)
          }
        }

        ws.onerror = (error: Event) => {
          console.error('❌ WebSocket connection error')
          console.error('Error details:', {
            wsUrl,
            readyState: ws.readyState,
            error: error,
          })
          setWsConnected(false)

          // Add error message to chat
          setMessages((prev) => [
            ...prev,
            {
              id: `${Date.now()}-ws-error`,
              content: 'Connection error. Using fallback mode (REST API).',
              sender: 'ai',
              timestamp: new Date(),
            },
          ])
        }

        ws.onclose = (event: CloseEvent) => {
          console.log('🔌 WebSocket disconnected', {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean,
          })
          setWsConnected(false)
          setInteractiveActive(false)
          setCreationType(null)
          wsRef.current = null

          // Only attempt to reconnect if it wasn't a clean close
          if (!event.wasClean && event.code !== 1000) {
            // Attempt to reconnect after 3 seconds
            if (reconnectTimeoutRef.current) {
              clearTimeout(reconnectTimeoutRef.current)
            }
            reconnectTimeoutRef.current = setTimeout(() => {
              console.log('🔄 Attempting to reconnect...')
              connectWebSocket()
            }, 3000)
          }
        }
      } catch (e) {
        console.error('Failed to create WebSocket:', e)
        setWsConnected(false)

        // Add error message to chat
        setMessages((prev) => [
          ...prev,
          {
            id: `${Date.now()}-ws-create-error`,
            content: 'Could not establish WebSocket connection. Using fallback mode (REST API).',
            sender: 'ai',
            timestamp: new Date(),
          },
        ])
      }
    }

    connectWebSocket()

    // Cleanup
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close(1000, 'Component unmounting')
        wsRef.current = null
      }
    }
  }, [API_BASE_URL, clerkId, sessionId])

  const sendMessage = useCallback(
    async (messageText: string, clearInput = false) => {
      if (!messageText.trim()) return

      const userMessage: Message = {
        id: Date.now().toString(),
        content: messageText,
        sender: 'user',
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, userMessage])
      if (clearInput) {
        setInputMessage('')
      }
      setIsLoading(true)

      // Send via WebSocket if connected
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        try {
          wsRef.current.send(
            JSON.stringify({
              type: 'message',
              text: messageText,
              clerk_id: clerkId,
              session_id: sessionId || 'session_fallback',
            }),
          )
          console.log('📤 Sent via WebSocket:', messageText)
        } catch (e) {
          console.error('Failed to send via WebSocket:', e)
          setIsLoading(false)

          // Fallback to REST API
          await fallbackToREST(messageText)
        }
      } else {
        // WebSocket not connected, use REST API fallback
        console.log('⚠️ WebSocket not connected, using REST API')
        await fallbackToREST(messageText)
      }
    },
    [clerkId, sessionId],
  )

  // Fallback REST API function
  const fallbackToREST = async (messageText: string) => {
    try {
      const response = (await api.chat.sendMessage(
        messageText,
        dbUserId || undefined,
        sessionId || 'session_fallback',
        clerkId || undefined,
      )) as {
        response: string
        classification: string
        properties?: Property[]
        builders?: Builder[]
        services?: ServiceResult[]
      }

      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: response.response,
        sender: 'ai',
        timestamp: new Date(),
        properties: response.properties,
        builders: response.builders,
        services: (response as any).services,
      }
      setMessages((prev) => [...prev, aiResponse])
      setSidebarRefresh((v) => v + 1)
    } catch (error) {
      console.error('Chat API error:', error)
      const errorResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: 'Sorry, I encountered an error. Please try again.',
        sender: 'ai',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorResponse])
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    const loadHistory = async () => {
      if (!dbUserId) return
      try {
        const res = (await api.chat.history(dbUserId, undefined, 50)) as any
        const serverMessages = (res?.messages || []) as Array<any>
        if (serverMessages.length === 0) return
        const mapped: Message[] = serverMessages.map((m: any, idx: number) => ({
          id: `${m.timestamp || 'ts'}-${idx}`,
          content: String(m.content || ''),
          sender: m.role === 'user' ? 'user' : 'ai',
          timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
          properties: m._payload?.properties as Property[] | undefined,
          builders: m._payload?.builders as Builder[] | undefined,
          services: m._payload?.services as ServiceResult[] | undefined,
        }))
        setMessages((prev) => (prev.length <= 1 ? mapped : prev))
      } catch (e) {
        // ignore history load errors
      }
    }
    loadHistory()
  }, [dbUserId])

  useEffect(() => {
    const query = searchParams.get('q')
    if (query && !hasProcessedQueryRef.current && user && sendMessage) {
      hasProcessedQueryRef.current = true
      setInputMessage(query)
      router.replace('/chat')
      sendMessage(query, false)
    }
  }, [searchParams, user, router, sendMessage])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputMessage.trim()) return

    // Send message via unified WebSocket (handles both normal and interactive modes)
    sendMessage(inputMessage, true)
  }

  const suggestedQuestions = [
    'Find houses in Islamabad',
    'Show me apartments in Karachi',
    'Find properties under 50 lakhs',
    'Show me 3 bedroom houses',
    'Find construction companies in Lahore',
    'Show me renovation services',
    'Find builders for home construction',
  ]

  // For scroll smoothness and scroll-to-bottom
  const scrollViewportRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    // Always scroll to bottom smoothly on messages change
    const viewport = scrollViewportRef.current
    if (viewport) {
      viewport.scrollTo({ top: viewport.scrollHeight, behavior: 'smooth' })
    }
  }, [messages])

  return (
    <div className="min-h-screen bg-gradient-to-br from-white via-[rgba(224,164,88,0.06)] to-white">
      {/* Chat Container */}
      <div className="w-full h-[calc(100vh-64px)] px-4 md:px-6 lg:px-10 py-6 mt-2">
        <div className="flex h-full">
          <div className="hidden lg:block">
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
          </div>

          {/* Two-column responsive layout for chat + insights */}
          <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-0">
            {/* Left: Conversation */}
            <div
              className={`flex flex-col ${isTyping ? 'lg:col-span-8' : 'lg:col-span-12'} min-h-0 transition-all duration-300`}
            >
              {/* Mobile sidebar toggle */}
              <div className="lg:hidden flex items-center justify-between px-4 py-3">
                <button
                  type="button"
                  onClick={() => setIsMobileSidebarOpen(true)}
                  className="rounded-lg border border-white/30 bg-white/60 backdrop-blur px-3 py-2 text-sm shadow-sm"
                >
                  Open history
                </button>
              </div>
              <ScrollArea className="flex-1 h-full" viewportRef={scrollViewportRef}>
                <div className="px-6 pb-6 pt-10 md:pt-12 space-y-5 bg-gradient-to-b from-white/70 via-white/60 to-white/70">
                  {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center text-center py-24 text-slate-600">
                      <SparklesIcon className="h-10 w-10 text-[color:var(--color-accent-gold)] mb-3" />
                      <p className="text-lg font-medium">Start your conversation with PropPal AI</p>
                      <p className="text-sm text-slate-400">
                        Ask about builders, properties, or your dream home.
                      </p>
                    </div>
                  )}
                  {messages.map((message) => {
                    const hasProperties = message.properties && message.properties.length > 0
                    const hasBuilders = message.builders && message.builders.length > 0
                    const hasServices = message.services && message.services.length > 0
                    const showTextMessage = !hasProperties && !hasBuilders && !hasServices

                    return (
                      <motion.div
                        key={message.id}
                        className="space-y-4"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3 }}
                      >
                        {showTextMessage && (
                          <div
                            className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                          >
                            {message.sender === 'user' ? (
                              <div className="max-w-3xl p-5 mb-1 rounded-xl shadow-md transition-all bg-gradient-to-r from-[color:var(--color-primary)] to-[color:var(--color-accent-gold)] text-white ml-auto">
                                <p className="leading-relaxed whitespace-pre-line font-sans">
                                  {message.content}
                                </p>
                                <p
                                  className="mt-2 text-xs/relaxed text-white/80"
                                  suppressHydrationWarning
                                >
                                  {message.timestamp.toLocaleTimeString([], {
                                    hour: '2-digit',
                                    minute: '2-digit',
                                  })}
                                </p>
                              </div>
                            ) : (
                              <div className="max-w-3xl p-5 mb-1 rounded-xl shadow-md transition-all bg-white/50 backdrop-blur-lg border border-slate-200/50 text-slate-800">
                                <p className="leading-relaxed whitespace-pre-line font-sans">
                                  {message.content}
                                </p>
                                <p className="mt-2 text-xs text-slate-500" suppressHydrationWarning>
                                  {message.timestamp.toLocaleTimeString([], {
                                    hour: '2-digit',
                                    minute: '2-digit',
                                  })}
                                </p>
                              </div>
                            )}
                          </div>
                        )}

                        {message.sender === 'ai' &&
                          message.properties &&
                          message.properties.length > 0 && (
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
                                          src={property.images[0] || '/placeholder.svg'}
                                          alt={property.title}
                                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                          onError={(e) => {
                                            const target = e.currentTarget as HTMLElement
                                            target.style.display = 'none'
                                            const nextSibling =
                                              target.nextElementSibling as HTMLElement
                                            if (nextSibling) {
                                              nextSibling.style.display = 'flex'
                                            }
                                          }}
                                        />
                                      ) : null}
                                      <div
                                        className={`h-full w-full flex items-center justify-center ${property.images && property.images.length > 0 ? 'hidden' : 'flex'}`}
                                      >
                                        <HomeModernIcon className="h-12 w-12 text-slate-400" />
                                      </div>
                                    </div>

                                    {/* Property Details */}
                                    <div className="p-4 flex flex-col flex-grow">
                                      <h3 className="font-semibold font-serif text-base text-slate-900 mb-2 line-clamp-2">
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
                                        <span className="text-sm text-slate-600">
                                          {property.city}
                                        </span>
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
                                        <span className="text-slate-500">
                                          {property.property_type}
                                        </span>
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

                        {message.sender === 'ai' &&
                          message.builders &&
                          message.builders.length > 0 && (
                            <div className="w-full max-w-6xl">
                              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {message.builders.map((builder) => (
                                  <div
                                    key={builder._id}
                                    onClick={() => openBuilderModal(builder)}
                                    className="bg-white rounded-xl shadow-sm border border-slate-200/50 overflow-hidden hover:shadow-lg hover:border-slate-300 transition-all duration-300 cursor-pointer flex flex-col h-full group"
                                  >
                                    {/* Builder Header */}
                                    <div className="h-40 bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center flex-shrink-0 relative">
                                      <div className="text-center text-white">
                                        <HomeModernIcon className="h-12 w-12 mx-auto mb-2 opacity-90" />
                                        <h3 className="text-sm font-semibold line-clamp-2 px-2">
                                          {builder.company_name}
                                        </h3>
                                      </div>
                                    </div>

                                    {/* Builder Details */}
                                    <div className="p-4 flex flex-col flex-grow">
                                      <h3 className="font-semibold font-serif text-base text-slate-900 mb-2 line-clamp-2">
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
                                            <span className="text-sm text-slate-600 ml-1">
                                              {builder.rating}
                                            </span>
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
                                      <div
                                        className="flex space-x-2 mt-auto pt-3"
                                        onClick={(e) => e.stopPropagation()}
                                      >
                                        <button
                                          onClick={() => openBuilderModal(builder)}
                                          className="flex-1 bg-gradient-to-r from-amber-500 to-orange-600 text-white py-2 px-3 rounded-lg text-sm font-medium hover:shadow-md transition-all text-center"
                                        >
                                          View Profile
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

                        {message.sender === 'ai' &&
                          message.services &&
                          message.services.length > 0 && (
                            <div className="w-full max-w-6xl">
                              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {message.services.map((svc, idx) => (
                                  <div
                                    key={`${svc._id || idx}`}
                                    className="bg-white/60 backdrop-blur rounded-xl shadow-card border border-slate-200/50 overflow-hidden hover:shadow-elevated hover:border-slate-300 transition-all duration-300 flex flex-col h-full"
                                  >
                                    {/* Top meta */}
                                    <div className="p-4 pb-0">
                                      <div className="flex items-center justify-between">
                                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                                          {svc.category || 'Service'}
                                        </span>
                                        {typeof svc.score === 'number' && (
                                          <span className="text-xs bg-teal-50 text-teal-700 px-2 py-1 rounded-full font-medium">
                                            {Math.round(svc.score * 100)}% match
                                          </span>
                                        )}
                                      </div>
                                    </div>

                                    {/* Content */}
                                    <div className="p-4 flex flex-col flex-grow">
                                      <h3 className="font-serif font-semibold text-base text-slate-900 mb-1 line-clamp-2">
                                        {svc.service_name || svc.title || 'Service'}
                                      </h3>
                                      {svc.description && (
                                        <p className="text-sm text-slate-700 mb-3 line-clamp-3">
                                          {svc.description}
                                        </p>
                                      )}

                                      {(svc.price_range_min || svc.price_range_max) && (
                                        <div className="flex items-center mb-3">
                                          <BanknotesIcon className="h-4 w-4 text-teal-600 mr-2" />
                                          <span className="text-sm font-semibold text-teal-700">
                                            {svc.price_range_min
                                              ? `Rs ${svc.price_range_min.toLocaleString()}`
                                              : ''}
                                            {svc.price_range_max
                                              ? ` - Rs ${svc.price_range_max.toLocaleString()}`
                                              : ''}
                                          </span>
                                        </div>
                                      )}

                                      {/* Actions */}
                                      <div className="mt-auto pt-2 flex gap-2">
                                        <button
                                          onClick={() => openServiceModal(svc)}
                                          className="flex-1 bg-gradient-to-r from-teal-500 to-cyan-600 text-white py-2 px-3 rounded-lg text-sm font-medium hover:shadow-md transition-all text-center"
                                        >
                                          View Service
                                        </button>
                                        {svc.builder_id ? (
                                          <button
                                            onClick={(e) => {
                                              e.stopPropagation()
                                              fetchAndOpenBuilderModal(svc.builder_id!)
                                            }}
                                            className="flex-1 bg-gradient-to-r from-amber-500 to-orange-600 text-white py-2 px-3 rounded-lg text-sm font-medium hover:shadow-md transition-all text-center"
                                          >
                                            View Builder
                                          </button>
                                        ) : null}
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
                      </motion.div>
                    )
                  })}

                  {isLoading && (
                    <div className="flex justify-start">
                      <div className="bg-white/60 backdrop-blur px-5 py-3.5 rounded-2xl shadow-sm border border-slate-200/50 animate-pulse text-slate-600">
                        Thinking…
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>

              {/* Property Details Modal */}
              <PropertyModal
                isOpen={isPropertyModalOpen && !!selectedProperty}
                property={selectedProperty as any}
                currentImageIndex={currentImageIndex}
                onClose={closePropertyModal}
                onPrev={showPrevImage}
                onNext={showNextImage}
                onDotClick={(idx) => setCurrentImageIndex(idx)}
                onOpenLightbox={() => setIsLightboxOpen(true)}
              />

              {/* Builder Details Modal */}
              <BuilderModal
                isOpen={isBuilderModalOpen && !!selectedBuilder}
                builder={selectedBuilder as any}
                onClose={closeBuilderModal}
              />

              {/* Service Details Modal */}
              <ServiceModal
                isOpen={isServiceModalOpen && !!selectedService}
                service={selectedService as any}
                onClose={closeServiceModal}
              />

              {/* Fullscreen Lightbox */}
              <ImageLightbox
                isOpen={Boolean(
                  isLightboxOpen && selectedProperty?.images && selectedProperty.images.length > 0,
                )}
                images={selectedProperty?.images || []}
                title={selectedProperty?.title || ''}
                currentIndex={currentImageIndex}
                onClose={() => setIsLightboxOpen(false)}
                onPrev={() => {
                  const total = selectedProperty?.images?.length || 1
                  setCurrentImageIndex((prev) => (prev - 1 + total) % total)
                }}
                onNext={() => {
                  const total = selectedProperty?.images?.length || 1
                  setCurrentImageIndex((prev) => (prev + 1) % total)
                }}
                onDotClick={(idx) => setCurrentImageIndex(idx)}
              />

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

              <div className="px-4 md:px-6 py-4 md:py-6 bg-white/80 backdrop-blur border-t border-slate-200 shadow-md sticky bottom-0">
                <form onSubmit={handleSendMessage} className="flex space-x-3 items-center relative">
                  {/* Connection Status Indicator */}
                  {!wsConnected && clerkId && sessionId && (
                    <div className="absolute -top-10 left-0 right-0 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-700 flex items-center gap-2 shadow-sm">
                      <div className="animate-pulse w-2 h-2 rounded-full bg-amber-500" />
                      <span>Connecting... (Fallback mode active)</span>
                    </div>
                  )}
                  {interactiveActive && (
                    <div className="absolute -top-10 left-0 right-0 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 text-xs text-blue-700 flex items-center gap-2 shadow-sm">
                      <div className="animate-pulse w-2 h-2 rounded-full bg-blue-500" />
                      <span>
                        Interactive mode: Creating your{' '}
                        {creationType === 'profile' ? 'profile' : 'service'}
                      </span>
                    </div>
                  )}

                  <Input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => {
                      setInputMessage(e.target.value)
                      setIsTyping(true)
                      if (typingTimerRef.current) clearTimeout(typingTimerRef.current)
                      typingTimerRef.current = setTimeout(() => setIsTyping(false), 1200)
                    }}
                    onFocus={() => setIsTyping(true)}
                    onBlur={() => setIsTyping(false)}
                    placeholder="Ask about properties, builders, or AI recommendations..."
                    className="flex-1 border border-slate-200 rounded-xl focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent transition-all text-slate-900 placeholder:text-slate-400 bg-white/80 backdrop-blur px-3 py-3"
                    disabled={isLoading}
                  />
                  <Button
                    type="submit"
                    disabled={!inputMessage.trim() || isLoading}
                    className="text-white px-6 py-3 rounded-xl shadow-md transition-all flex items-center gap-2 bg-gradient-to-r from-[color:var(--color-primary)] to-[color:var(--color-accent-gold)] hover:from-[color:var(--color-accent-gold)] hover:to-[color:var(--color-primary)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)] focus:ring-offset-2 min-w-[4.5rem]"
                    style={{
                      backgroundImage:
                        'linear-gradient(90deg, var(--color-primary), var(--color-accent-gold))',
                    }}
                  >
                    <PaperAirplaneIcon className="w-4 h-4" />
                    <span>Send</span>
                  </Button>
                </form>
              </div>
            </div>

            {/* Right: Insights / Suggestions (only while typing) */}
            {isTyping && (
              <motion.div
                className="lg:col-span-4 hidden lg:block"
                initial={{ x: 420, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ type: 'spring', stiffness: 260, damping: 26 }}
              >
                <QuickSuggestions
                  suggestedQuestions={suggestedQuestions}
                  onSelect={(q) => setInputMessage(q)}
                />
              </motion.div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Sidebar Overlay */}
      {isMobileSidebarOpen && (
        <div
          className="fixed inset-0 z-[70] bg-black/40"
          onClick={() => setIsMobileSidebarOpen(false)}
        >
          <div
            className="absolute left-0 top-0 h-full w-[80%] max-w-sm bg-white/70 backdrop-blur-xl border-r border-white/30 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/30">
              <h3 className="font-semibold" style={{ color: 'var(--color-primary)' }}>
                History & Prompts
              </h3>
              <button
                onClick={() => setIsMobileSidebarOpen(false)}
                className="rounded-md px-3 py-1 text-sm border border-white/30 bg-white/60"
              >
                Close
              </button>
            </div>
            <div className="h-[calc(100%-56px)] overflow-y-auto p-4 space-y-4">
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

              <div className="rounded-2xl bg-white/60 backdrop-blur border border-white/30 shadow-sm">
                <div className="p-4">
                  <h4
                    className="text-sm font-semibold mb-2"
                    style={{ color: 'var(--color-primary)' }}
                  >
                    Quick Prompts
                  </h4>
                  <div className="grid grid-cols-1 gap-2">
                    {['Find affordable houses', 'Best builder near me', ...suggestedQuestions].map(
                      (q, i) => (
                        <button
                          key={`${q}-${i}`}
                          onClick={() => {
                            setInputMessage(q)
                            setIsMobileSidebarOpen(false)
                          }}
                          className="text-left p-3 text-sm text-slate-700 hover:bg-white/70 border border-transparent hover:border-slate-200 rounded-xl transition-all"
                        >
                          <span className="mr-2" style={{ color: 'var(--color-accent-gold)' }}>
                            →
                          </span>
                          {q}
                        </button>
                      ),
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
