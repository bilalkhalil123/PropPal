'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { api } from '@/lib/api-client'
import { UserButton } from '@clerk/nextjs'
import Link from 'next/link'
import { 
  HomeIcon, 
  MapPinIcon, 
  BanknotesIcon, 
  HomeModernIcon,
  CalendarIcon
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
  const { user, isAuthenticated, userId } = useCurrentUser()
  const searchParams = useSearchParams()
  const router = useRouter()
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
  const hasProcessedQueryRef = useRef(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

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
      const response = await api.chat.sendMessage(messageText, userId, 'session_123') as {
        response: string
        classification: string
        properties?: Property[]
        builders?: Builder[]
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

      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: response.response,
        sender: 'ai',
        timestamp: new Date(),
        properties: response.properties,
        builders: response.builders
      }
      
      setMessages(prev => [...prev, aiResponse])
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
  }, [userId])

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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200 px-4 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center space-x-2 text-blue-600 hover:text-blue-700">
            <span className="text-2xl font-bold">PropPal</span>
          </Link>
          <div className="flex items-center space-x-4">
            <span className="text-lg font-semibold text-gray-900">AI Assistant</span>
            {isAuthenticated && <UserButton afterSignOutUrl="/" />}
          </div>
        </div>
      </header>

      {/* Chat Container */}
      <div className="flex flex-col h-[calc(100vh-80px)] max-w-6xl mx-auto">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
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
                          ? 'bg-blue-500 text-white ml-3' 
                          : 'bg-gray-200 text-gray-600 mr-3'
                      }`}>
                        {message.sender === 'user' ? '👤' : '🤖'}
                      </div>

                      <div className={`rounded-2xl px-4 py-3 ${
                        message.sender === 'user'
                          ? 'bg-blue-500 text-white'
                          : 'bg-white text-gray-900 shadow-sm border border-gray-200'
                      }`}>
                        <p className="whitespace-pre-wrap">{message.content}</p>
                        <p 
                          className={`text-xs mt-1 ${
                            message.sender === 'user' ? 'text-blue-100' : 'text-gray-500'
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
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {message.properties.map((property) => (
                      <div key={property._id} className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow flex flex-col h-full">
                        {/* Property Image */}
                        <div className="h-48 bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center overflow-hidden flex-shrink-0">
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
                          <h3 className="font-semibold text-lg text-gray-900 mb-2 line-clamp-2">{property.title}</h3>
                          
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
                            <button className="flex-1 bg-blue-600 text-white py-2 px-3 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
                              View Details
                            </button>
                            <button className="flex-1 border border-blue-600 text-blue-600 py-2 px-3 rounded-lg text-sm font-medium hover:bg-blue-50 transition-colors">
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
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {message.builders.map((builder) => (
                      <div key={builder._id} className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow flex flex-col h-full">
                        {/* Builder Header */}
                        <div className="h-48 bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center flex-shrink-0">
                          <div className="text-center text-white">
                            <HomeModernIcon className="h-16 w-16 mx-auto mb-2 opacity-80" />
                            <h3 className="text-lg font-semibold line-clamp-2">{builder.company_name}</h3>
                          </div>
                        </div>
                        
                        {/* Builder Details */}
                        <div className="p-4 flex flex-col flex-grow">
                          <h3 className="font-semibold text-lg text-gray-900 mb-2 line-clamp-2">{builder.company_name}</h3>
                          
                          {/* Specialization Tags */}
                          <div className="flex flex-wrap gap-1 mb-3">
                            {builder.specialization.map((spec, index) => (
                              <span key={index} className="bg-orange-100 text-orange-800 px-2 py-1 rounded-full text-xs">
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
                              <span className="bg-orange-100 text-orange-800 px-2 py-1 rounded text-xs">
                                {Math.round(builder.score * 100)}%
                              </span>
                            </div>
                          )}
                          
                          {/* Action Buttons */}
                          <div className="flex space-x-2 mt-auto pt-3">
                            <button className="flex-1 bg-orange-600 text-white py-2 px-3 rounded-lg text-sm font-medium hover:bg-orange-700 transition-colors">
                              View Profile
                            </button>
                            <button className="flex-1 border border-orange-600 text-orange-600 py-2 px-3 rounded-lg text-sm font-medium hover:bg-orange-50 transition-colors">
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
              <div className="bg-white rounded-2xl px-4 py-3 shadow-sm border border-gray-200">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Questions */}
        {messages.length === 1 && (
          <div className="px-4 pb-4">
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Try asking:</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {suggestedQuestions.map((question, index) => (
                  <button
                    key={index}
                    onClick={() => setInputMessage(question)}
                    className="text-left p-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    "{question}"
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="p-4 bg-white border-t border-gray-200">
          <form onSubmit={handleSendMessage} className="flex space-x-3">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask about properties, search listings, or get help..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder:text-gray-400"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!inputMessage.trim() || isLoading}
              className="bg-blue-500 text-white px-6 py-3 rounded-xl hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

