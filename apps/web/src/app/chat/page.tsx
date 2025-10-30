'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { api } from '@/lib/api-client'
import { UserButton } from '@clerk/nextjs'
import ChatSidebar from '@/components/ChatSidebar'
import Link from 'next/link'
import { 
  HomeIcon, 
  MapPinIcon, 
  BanknotesIcon, 
  HomeModernIcon,
  CalendarIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'

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
  sender: 'user' | 'ai'
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
      id: '1',
      content: "Hello! I'm your PropPal AI assistant. I can help you find properties and builders in Pakistan. Try asking me to 'Find houses in Islamabad' or 'Show me construction companies in Karachi'. I can search for properties by location, price, and type, or find builders by specialization and experience.",
      sender: 'ai',
      timestamp: new Date()
    }
  ])
  const [inputMessage, setInputMessage] = useState('')
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

  // Close on Esc + prevent body scroll while modal or lightbox open
  useEffect(() => {
    const anyOverlayOpen = isPropertyModalOpen || isLightboxOpen || isBuilderModalOpen
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
        } else if (isBuilderModalOpen) {
          setIsBuilderModalOpen(false)
        }
      }
      if (isLightboxOpen && selectedProperty?.images && selectedProperty.images.length > 1) {
        if (e.key === 'ArrowRight') {
          // next
          setCurrentImageIndex((prev) => (prev + 1) % selectedProperty.images!.length)
        } else if (e.key === 'ArrowLeft') {
          // prev
          setCurrentImageIndex((prev) => (prev - 1 + selectedProperty.images!.length) % selectedProperty.images!.length)
        }
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = ''
    }
  }, [isPropertyModalOpen, isLightboxOpen, isBuilderModalOpen, selectedProperty])

  // Reset slider index when opening or property changes
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

  // Initialize or restore chat session id
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

  // Function to send a message (reusable)
  const sendMessage = useCallback(async (messageText: string, clearInput: boolean = false) => {
    if (!messageText.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: messageText,
      sender: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    if (clearInput) {
      setInputMessage('')
    }
    setIsLoading(true)

    try {
      // Call the chat API
      const response = await api.chat.sendMessage(messageText, dbUserId || undefined, sessionId || 'session_fallback', clerkId || undefined) as {
        response: string
        classification: string
        properties?: Property[]
        builders?: Builder[]
        start_interactive?: { type: 'service' | 'profile', ws_path: string, clerk_id_required?: boolean }
      }

      // Log the API response to console
      console.log('=== CHAT API RESPONSE ===')
      console.log('Full Response:', JSON.stringify(response, null, 2))
      console.log('Response Type:', typeof response)
      console.log('Classification:', response.classification)
      console.log('Has Properties:', !!response.properties)
      console.log('Properties Count:', response.properties?.length || 0)
      console.log('Has Builders:', !!response.builders)
      console.log('Builders Count:', response.builders?.length || 0)
      if (response.properties) {
        console.log('Properties:', JSON.stringify(response.properties, null, 2))
      }
      if (response.builders) {
        console.log('Builders:', JSON.stringify(response.builders, null, 2))
      }
      console.log('========================')

      // If agent requests interactive websocket flow, start it and route subsequent messages over WS
      const handoffMessages = [
        "Starting service creation. Please connect via websocket to continue.",
        "Starting builder profile creation. Please connect via websocket to continue."
      ]
      const si = (response as any).start_interactive as { type: 'service' | 'profile', ws_path: string } | undefined
      const isHandoff = handoffMessages.includes(response.response)
      
      // Determine the websocket path based on the response
      let wsPath: string | null = null
      if (si?.ws_path) {
        wsPath = si.ws_path
      } else if (isHandoff) {
        // Map handoff message to default websocket path
        if (response.response.includes('service creation')) {
          wsPath = '/api/chat/ws/service/create'
        } else if (response.response.includes('builder profile creation')) {
          wsPath = '/api/chat/ws/profile/create'
        }
      }
      
      if (wsPath && API_BASE_URL) {
        // Do NOT show the handoff message to the user; silently start websocket flow
        // Keep the user message visible - we'll resend via WS but also show in chat
        // Build WS URL
        let wsOrigin: string
        try {
          const urlObj = new URL(API_BASE_URL)
          wsOrigin = (urlObj.protocol === 'https:' ? 'wss://' : 'ws://') + urlObj.host
        } catch {
          const baseNoSlash = API_BASE_URL.replace(/\/$/, '')
          wsOrigin = baseNoSlash.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:')
        }
        const qs = `?clerk_id=${encodeURIComponent(clerkId || '')}`
        const wsUrl = `${wsOrigin}${wsPath}${qs}`
          try {
            const ws = new WebSocket(wsUrl)
            wsRef.current = ws
            setInteractiveActive(true)

            ws.onopen = () => {
              // Immediately send the user's original intent so the agent can start asking relevant questions
              try { ws.send(JSON.stringify({ type: 'user', text: messageText })) } catch {}
            }

            ws.onmessage = (evt) => {
              try {
                const payload = JSON.parse(evt.data)
                if (payload.type === 'agent') {
                  setMessages(prev => [...prev, { id: `${Date.now()}-agent`, content: String(payload.text || ''), sender: 'ai', timestamp: new Date() }])
                } else if (payload.type === 'completed') {
                  setMessages(prev => [...prev, { id: `${Date.now()}-done`, content: String(payload.message || 'Completed'), sender: 'ai', timestamp: new Date() }])
                  ws.close()
                  wsRef.current = null
                  setInteractiveActive(false)
                } else if (payload.type === 'error') {
                  setMessages(prev => [...prev, { id: `${Date.now()}-err`, content: `Error: ${String(payload.message || 'Unknown error')}`, sender: 'ai', timestamp: new Date() }])
                  ws.close()
                  wsRef.current = null
                  setInteractiveActive(false)
                }
              } catch {
                // ignore malformed
              }
            }

            ws.onerror = () => {
              setMessages(prev => [...prev, { id: `${Date.now()}-wserr`, content: 'Connection error during interactive flow.', sender: 'ai', timestamp: new Date() }])
              wsRef.current = null
              setInteractiveActive(false)
            }

            ws.onclose = () => {
              wsRef.current = null
              setInteractiveActive(false)
            }

            // No need for setTimeout; we send on onopen
          } catch (e) {
            setMessages(prev => [...prev, { id: `${Date.now()}-wsex`, content: 'Failed to start interactive flow.', sender: 'ai', timestamp: new Date() }])
          }
      } else if (!isHandoff) {
        // Normal non-interactive response: show AI message unless it's a handoff message
        const aiResponse: Message = {
          id: (Date.now() + 1).toString(),
          content: response.response,
          sender: 'ai',
          timestamp: new Date(),
          properties: response.properties,
          builders: response.builders
        }
        setMessages(prev => [...prev, aiResponse])
        setSidebarRefresh((v) => v + 1)
      } else {
        // Handoff message without start_interactive flag - just suppress the AI message
        // Keep the user message visible
      }
    } catch (error) {
      console.error('Chat API error:', error)
      const errorResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: 'Sorry, I encountered an error. Please try again.',
        sender: 'ai',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorResponse])
    } finally {
      setIsLoading(false)
    }
  }, [dbUserId, clerkId, API_BASE_URL, sessionId])

  // Load persisted history for this user (DB id only)
  useEffect(() => {
    const loadHistory = async () => {
      if (!dbUserId) return
      try {
        const res = await api.chat.history(dbUserId, undefined, 50) as any
        const serverMessages = (res?.messages || []) as Array<any>
        if (serverMessages.length === 0) return
        const mapped: Message[] = serverMessages.map((m: any, idx: number) => ({
          id: `${m.timestamp || 'ts'}-${idx}`,
          content: String(m.content || ''),
          sender: m.role === 'user' ? 'user' : 'ai',
          timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
          properties: m._payload?.properties as Property[] | undefined,
          builders: m._payload?.builders as Builder[] | undefined,
        }))
        // Keep welcome message only if no history exists
        setMessages((prev) => (prev.length <= 1 ? mapped : prev))
      } catch (e) {
        // ignore history load errors
      }
    }
    loadHistory()
  }, [dbUserId])

  // Check for query parameter from other pages
  useEffect(() => {
    const query = searchParams.get('q')
    if (query && !hasProcessedQueryRef.current && user && sendMessage) {
      hasProcessedQueryRef.current = true
      setInputMessage(query)
      // Clean the URL
      router.replace('/chat')
      // Automatically send the message
      sendMessage(query, false)
    }
  }, [searchParams, user, router, sendMessage])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    // If interactive flow is active, route message over the existing websocket
    if (interactiveActive && wsRef.current) {
      const text = inputMessage
      if (!text.trim()) return
      setMessages(prev => [...prev, { id: Date.now().toString(), content: text, sender: 'user', timestamp: new Date() }])
      try { wsRef.current.send(JSON.stringify({ type: 'user', text })) } catch {}
      setInputMessage('')
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
    "Find builders for home construction"
  ]

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-slate-200 px-4 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center space-x-2 text-indigo-600 hover:text-indigo-700">
            <span className="text-2xl font-bold">PropPal</span>
          </Link>
          <div className="flex items-center space-x-4">
            <span className="text-lg font-semibold text-gray-900">AI Assistant</span>
            {isAuthenticated && <UserButton afterSignOutUrl="/" />}
          </div>
        </div>
      </header>

      {/* Chat Container */}
      <div className="max-w-7xl mx-auto h-[calc(100vh-80px)] px-2 md:px-4">
        <div className="flex h-full rounded-2xl bg-white border border-slate-200 overflow-hidden">
          <ChatSidebar userId={dbUserId || undefined} sessionId={sessionId} activeSessionId={sessionId} onNewSession={(sid) => { setSessionId(sid); setSidebarRefresh((v) => v + 1) }} refreshKey={sidebarRefresh} />
          <div className="flex flex-col flex-1">
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 md:p-5 space-y-4 bg-slate-50">
          {messages.map((message) => {
            // Determine if this message has properties or builders
            const hasProperties = message.properties && message.properties.length > 0
            const hasBuilders = message.builders && message.builders.length > 0
            const showTextMessage = !hasProperties && !hasBuilders

            return (
              <div key={message.id} className="space-y-4">
                {showTextMessage && (
                  <div className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`flex max-w-2xl ${message.sender === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                      <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
                        message.sender === 'user' 
                          ? 'bg-indigo-600 text-white ml-3' 
                          : 'bg-slate-200 text-slate-600 mr-3'
                      }`}>
                        {message.sender === 'user' ? '👤' : '🤖'}
                      </div>

                      <div className={`rounded-3xl px-5 py-3.5 ${
                        message.sender === 'user'
                          ? 'bg-indigo-600 text-white'
                          : 'bg-white text-gray-900 shadow-lg'
                      }`}>
                        <p className={`whitespace-pre-wrap ${message.sender === 'user' ? 'text-base' : 'text-lg'}`}>{message.content}</p>
                        <p 
                          className={`text-xs mt-1.5 ${
                            message.sender === 'user' ? 'text-indigo-100' : 'text-gray-400'
                          }`}
                          suppressHydrationWarning
                        >
                          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              
              {/* Property Cards */}
              {message.sender === 'ai' && message.properties && message.properties.length > 0 && (
                <div className="w-full max-w-6xl">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {message.properties.map((property) => (
                      <div key={property._id} className="bg-white rounded-2xl shadow-md overflow-hidden hover:shadow-xl hover:scale-105 transition-all duration-300 cursor-pointer flex flex-col h-full">
                        {/* Property Image */}
                        <div className="h-48 bg-gradient-to-br from-indigo-400 to-indigo-600 flex items-center justify-center overflow-hidden flex-shrink-0">
                          {property.images && property.images.length > 0 ? (
                            <img 
                              src={property.images[0]} 
                              alt={property.title}
                              className="w-full h-full object-cover"
                              onError={(e) => {
                                const target = e.currentTarget as HTMLElement;
                                target.style.display = 'none';
                                const nextSibling = target.nextElementSibling as HTMLElement;
                                if (nextSibling) {
                                  nextSibling.style.display = 'flex';
                                }
                              }}
                            />
                          ) : null}
                          <div className={`h-full w-full flex items-center justify-center ${property.images && property.images.length > 0 ? 'hidden' : 'flex'}`}>
                            <HomeModernIcon className="h-16 w-16 text-white opacity-50" />
                          </div>
                        </div>
                        
                        {/* Property Details */}
                        <div className="p-4 flex flex-col flex-grow">
                          <h3 className="font-semibold text-xl text-gray-900 mb-3 line-clamp-2">{property.title}</h3>
                          
                          {/* Price */}
                          <div className="flex items-center mb-2">
                            <BanknotesIcon className="h-4 w-4 text-green-600 mr-1" />
                            <span className="text-xl font-bold text-green-600">
                              Rs {property.price.toLocaleString()}
                            </span>
                          </div>
                          
                          {/* Location */}
                          <div className="flex items-center mb-2">
                            <MapPinIcon className="h-4 w-4 text-gray-500 mr-1" />
                            <span className="text-sm text-gray-600">{property.city}</span>
                          </div>
                          
                          {/* Property Stats */}
                          <div className="flex items-center justify-between mb-3 text-sm text-gray-600">
                            <span>{property.bedrooms} bed</span>
                            <span>{property.bathrooms} bath</span>
                            <span>{property.area_sqft} sqft</span>
                          </div>
                          
                          {/* Property Type & Score */}
                          <div className="flex items-center justify-between mb-3 text-xs text-gray-500">
                            <span>{property.property_type}</span>
                            {property.score && (
                              <div className="flex items-center">
                                <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                                  Score: {Math.round(property.score * 100)}%
                                </span>
                              </div>
                            )}
                          </div>
                          
                          {/* Action Buttons */}
                          <div className="flex space-x-2 mt-auto pt-3">
                            <button
                              onClick={() => openPropertyModal(property)}
                              className="flex-1 bg-indigo-600 text-white py-2.5 px-3 rounded-xl text-sm font-medium hover:bg-indigo-700 transition-colors"
                            >
                              View Details
                            </button>
                            <button className="flex-1 border border-indigo-600 text-indigo-600 py-2.5 px-3 rounded-xl text-sm font-medium hover:bg-indigo-50 transition-colors">
                              Contact Agent
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Builder Cards */}
              {message.sender === 'ai' && message.builders && message.builders.length > 0 && (
                <div className="w-full max-w-6xl">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {message.builders.map((builder) => (
                      <div key={builder._id} className="bg-white rounded-2xl shadow-md overflow-hidden hover:shadow-xl hover:scale-105 transition-all duration-300 cursor-pointer flex flex-col h-full">
                        {/* Builder Header */}
                        <div className="h-48 bg-gradient-to-br from-amber-500 to-amber-600 flex items-center justify-center flex-shrink-0">
                          <div className="text-center text-white">
                            <HomeModernIcon className="h-16 w-16 mx-auto mb-2 opacity-80" />
                            <h3 className="text-lg font-semibold line-clamp-2">{builder.company_name}</h3>
                          </div>
                        </div>
                        
                        {/* Builder Details */}
                        <div className="p-4 flex flex-col flex-grow">
                          <h3 className="font-semibold text-xl text-gray-900 mb-3 line-clamp-2">{builder.company_name}</h3>
                          
                          {/* Specialization Tags */}
                          <div className="flex flex-wrap gap-1 mb-3">
                            {builder.specialization.map((spec, index) => (
                              <span key={index} className="bg-amber-100 text-amber-800 px-2 py-1 rounded-full text-xs">
                                {spec}
                              </span>
                            ))}
                          </div>
                          
                          {/* Experience & Rating */}
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center">
                              <CalendarIcon className="h-4 w-4 text-gray-500 mr-1" />
                              <span className="text-sm text-gray-600">{builder.experience_years} years experience</span>
                            </div>
                            {builder.rating && (
                              <div className="flex items-center">
                                <span className="text-yellow-500">★</span>
                                <span className="text-sm text-gray-600 ml-1">{builder.rating}</span>
                              </div>
                            )}
                          </div>
                          
                          {/* Location */}
                          {builder.location && (
                            <div className="flex items-center mb-3">
                              <MapPinIcon className="h-4 w-4 text-gray-500 mr-1" />
                              <span className="text-sm text-gray-600">{builder.location.city}</span>
                            </div>
                          )}
                          
                          {/* About */}
                          {builder.about && (
                            <p className="text-sm text-gray-600 mb-3 line-clamp-2">{builder.about}</p>
                          )}
                          
                          {/* Score */}
                          {builder.score && (
                            <div className="flex items-center justify-between mb-3 text-xs text-gray-500">
                              <span>Relevance Score</span>
                              <span className="bg-amber-100 text-amber-800 px-2 py-1 rounded text-xs">
                                {Math.round(builder.score * 100)}%
                              </span>
                            </div>
                          )}
                          
                          {/* Action Buttons */}
                          <div className="flex space-x-2 mt-auto pt-3">
                            <Link
                              href={`/builders/${builder._id}`}
                              className="flex-1 bg-amber-600 text-white py-2.5 px-3 rounded-xl text-sm font-medium hover:bg-amber-700 transition-colors text-center"
                            >
                              View Profile
                            </Link>
                            <button className="flex-1 border border-amber-600 text-amber-600 py-2.5 px-3 rounded-xl text-sm font-medium hover:bg-amber-50 transition-colors">
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

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white rounded-3xl px-5 py-3.5 shadow-lg">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
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
                        src={selectedProperty.images[currentImageIndex]}
                        alt={selectedProperty.title}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          const target = e.currentTarget as HTMLElement
                          target.style.display = 'none'
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
                          className={`w-2.5 h-2.5 rounded-full ${idx === currentImageIndex ? 'bg-indigo-600' : 'bg-slate-300'} transition-colors`}
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
                  src={selectedProperty.images[currentImageIndex]}
                  alt={selectedProperty.title}
                  className="max-h-full max-w-full object-contain"
                />

                {selectedProperty.images.length > 1 && (
                  <>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setCurrentImageIndex((prev) => (prev - 1 + selectedProperty.images!.length) % selectedProperty.images!.length) }}
                      className="absolute left-2 md:left-6 top-1/2 -translate-y-1/2 bg-white/15 hover:bg-white/25 text-white rounded-full w-10 h-10 flex items-center justify-center"
                      aria-label="Previous image"
                    >
                      ‹
                    </button>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setCurrentImageIndex((prev) => (prev + 1) % selectedProperty.images!.length) }}
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
                      className={`w-2.5 h-2.5 rounded-full ${idx === currentImageIndex ? 'bg-white' : 'bg-white/40'} transition-colors`}
                      onClick={() => setCurrentImageIndex(idx)}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

            {/* Suggested Questions */}
            {messages.length === 1 && (
              <div className="px-2 md:px-0 pb-4">
                <div className="bg-white rounded-2xl p-5 shadow">
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">Try asking:</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {suggestedQuestions.map((question, index) => (
                      <button
                        key={index}
                        onClick={() => setInputMessage(question)}
                        className="text-left p-3 text-sm text-indigo-600 hover:bg-indigo-50 rounded-xl transition-colors"
                      >
                        "{question}"
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Input Area */}
            <div className="p-4 bg-white border-t border-slate-200">
              <form onSubmit={handleSendMessage} className="flex space-x-3">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder="Ask about properties, search listings, or get help..."
                  className="flex-1 px-5 py-3.5 border border-slate-300 rounded-2xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900 placeholder:text-gray-400"
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  disabled={!inputMessage.trim() || isLoading}
                  className="bg-indigo-600 text-white px-8 py-3.5 rounded-2xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-md hover:shadow-lg transition-all"
                >
                  Send
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

