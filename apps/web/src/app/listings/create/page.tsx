'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { motion, AnimatePresence } from 'framer-motion'
import {
  MicrophoneIcon,
  StopIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  SparklesIcon,
  PhotoIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'

interface PropertyFormData {
  title: string
  description: string
  price: string
  property_type: string
  area_sqft: string
  bedrooms: string
  bathrooms: string
  floors: string
  city: string
  area: string
  lng: string
  lat: string
  images: string[]
}

const REQUIRED_FIELDS: (keyof PropertyFormData)[] = [
  'title',
  'description',
  'price',
  'property_type',
  'area_sqft',
  'bedrooms',
  'bathrooms',
  'city',
  'area',
]

export default function CreateListingPage() {
  const { user, isAuthenticated, clerkId, loading } = useCurrentUser()
  const router = useRouter()
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL

  const [formData, setFormData] = useState<PropertyFormData>({
    title: '',
    description: '',
    price: '',
    property_type: '',
    area_sqft: '',
    bedrooms: '',
    bathrooms: '',
    floors: '1',
    city: '',
    area: '',
    lng: '',
    lat: '',
    images: [],
  })

  const [isVoiceMode, setIsVoiceMode] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const [missingFields, setMissingFields] = useState<string[]>([])
  const [statusMessage, setStatusMessage] = useState<string>('')
  const [statusType, setStatusType] = useState<'info' | 'success' | 'error'>('info')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [partialTranscript, setPartialTranscript] = useState<string>('')
  const [accumulatedTranscript, setAccumulatedTranscript] = useState<string>('')
  const [uploadingImages, setUploadingImages] = useState(false)
  const [isGeneratingDescription, setIsGeneratingDescription] = useState(false)
  const [uploadingAudio, setUploadingAudio] = useState(false)
  const audioInputRef = useRef<HTMLInputElement>(null)

  // Query queue system
  interface QueuedQuery {
    id: string
    text: string
    timestamp: number
    status: 'pending' | 'processing' | 'completed' | 'error'
  }
  const [queryQueue, setQueryQueue] = useState<QueuedQuery[]>([])
  const [currentQueryId, setCurrentQueryId] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const sessionIdRef = useRef<string | null>(null)
  const pauseTimerRef = useRef<NodeJS.Timeout | null>(null)
  const accumulatedTextRef = useRef<string>('')
  const isProcessingQueryRef = useRef<boolean>(false)
  const queryQueueRef = useRef<QueuedQuery[]>([])
  const queryTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const currentQueryIdRef = useRef<string | null>(null)
  const isRecordingRef = useRef<boolean>(false)

  // Initialize session ID
  useEffect(() => {
    try {
      const key = 'property_listing_session_id'
      let sid = typeof window !== 'undefined' ? window.localStorage.getItem(key) : null
      if (!sid) {
        sid = `p_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
        window.localStorage.setItem(key, sid)
      }
      sessionIdRef.current = sid
    } catch {
      sessionIdRef.current = 'session_fallback'
    }
  }, [])

  // Sync queryQueueRef with state
  useEffect(() => {
    queryQueueRef.current = queryQueue
  }, [queryQueue])

  // Process next query from queue
  const processNextQuery = useCallback(() => {
    // Don't process if already processing or WebSocket not ready
    if (
      isProcessingQueryRef.current ||
      !wsRef.current ||
      wsRef.current.readyState !== WebSocket.OPEN
    ) {
      console.log(
        '⏸️ Cannot process: processing=',
        isProcessingQueryRef.current,
        'ws=',
        wsRef.current?.readyState,
      )
      return
    }

    // Get next pending query
    const nextQuery = queryQueueRef.current.find((q) => q.status === 'pending')
    if (!nextQuery) {
      console.log('✅ No pending queries in queue')
      return
    }

    // Mark as processing
    isProcessingQueryRef.current = true
    currentQueryIdRef.current = nextQuery.id
    setCurrentQueryId(nextQuery.id)
    setQueryQueue((prev) =>
      prev.map((q) => (q.id === nextQuery.id ? { ...q, status: 'processing' } : q)),
    )

    setIsProcessing(true)
    console.log('📤 Processing query from queue:', nextQuery.text)

    // Set timeout for query (30 seconds max)
    if (queryTimeoutRef.current) {
      clearTimeout(queryTimeoutRef.current)
    }
    const queryIdForTimeout = nextQuery.id
    queryTimeoutRef.current = setTimeout(() => {
      console.warn('⏱️ Query timeout, marking as error and processing next')
      if (currentQueryIdRef.current === queryIdForTimeout) {
        setQueryQueue((prev) =>
          prev.map((q) => (q.id === queryIdForTimeout ? { ...q, status: 'error' } : q)),
        )
        isProcessingQueryRef.current = false
        currentQueryIdRef.current = null
        setCurrentQueryId(null)
        setIsProcessing(false)
        setTimeout(() => processNextQuery(), 100)
      }
    }, 30000) // 30 second timeout

    try {
      wsRef.current.send(
        JSON.stringify({
          type: 'property_create',
          text: nextQuery.text,
          clerk_id: clerkId,
          session_id: sessionIdRef.current,
        }),
      )
    } catch (error) {
      console.error('Error sending query:', error)
      // Mark query as error
      setQueryQueue((prev) =>
        prev.map((q) => (q.id === nextQuery.id ? { ...q, status: 'error' } : q)),
      )
      isProcessingQueryRef.current = false
      currentQueryIdRef.current = null
      setCurrentQueryId(null)
      setIsProcessing(false)
      // Try next query
      setTimeout(() => processNextQuery(), 100)
    }
  }, [clerkId])

  // Mark current query as completed and process next
  const completeCurrentQuery = useCallback(() => {
    // Clear timeout
    if (queryTimeoutRef.current) {
      clearTimeout(queryTimeoutRef.current)
      queryTimeoutRef.current = null
    }

    const completedId = currentQueryIdRef.current
    if (completedId) {
      setQueryQueue((prev) =>
        prev.map((q) => (q.id === completedId ? { ...q, status: 'completed' } : q)),
      )
    }
    isProcessingQueryRef.current = false
    currentQueryIdRef.current = null
    setCurrentQueryId(null)
    setIsProcessing(false)

    // Remove completed queries after a delay
    setTimeout(() => {
      setQueryQueue((prev) => prev.filter((q) => q.status !== 'completed'))
    }, 2000)

    // Process next query
    setTimeout(() => processNextQuery(), 100)
  }, [processNextQuery])

  // WebSocket connection for real-time updates
  useEffect(() => {
    if (!API_BASE_URL || !clerkId || !sessionIdRef.current || !isVoiceMode) {
      return
    }

    let wsOrigin: string
    try {
      const urlObj = new URL(API_BASE_URL)
      wsOrigin = (urlObj.protocol === 'https:' ? 'wss://' : 'ws://') + urlObj.host
    } catch (error) {
      const baseNoSlash = API_BASE_URL.replace(/\/$/, '')
      wsOrigin = baseNoSlash.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:')
    }

    const wsUrl = `${wsOrigin}/api/chat/ws?clerk_id=${encodeURIComponent(clerkId)}&session_id=${encodeURIComponent(sessionIdRef.current)}`

    const connectWebSocket = () => {
      try {
        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onopen = () => {
          console.log('✅ WebSocket connected for property creation')
          setWsConnected(true)
          setStatusMessage('Connected. You can start speaking.')
          setStatusType('success')
          // Process any pending queries when WebSocket connects
          // Will be handled by the useEffect that watches wsConnected
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            console.log('📨 WebSocket message:', data)

            if (data.type === 'field_update') {
              // Update only the fields that were actually changed
              if (data.updates) {
                const updates = data.updates as Record<string, any>
                setFormData((prev) => {
                  const updated = { ...prev }
                  // Only update the fields that were sent in updates
                  Object.keys(updates).forEach((key) => {
                    if (key in updated) {
                      const value = updates[key]
                      // Handle images array separately, convert others to string
                      if (key === 'images' && Array.isArray(value)) {
                        updated.images = value
                      } else if (key !== 'images') {
                        updated[key as keyof PropertyFormData] = String(value) as any
                      }
                    }
                  })
                  return updated
                })
                console.log('✅ Updated fields:', Object.keys(updates))
              }

              // Update missing fields
              if (data.missing_fields) {
                setMissingFields(data.missing_fields)
              }

              // Update status message
              if (data.message) {
                setStatusMessage(data.message)
                setStatusType('info')
              }

              // Complete current query and process next
              completeCurrentQuery()
            } else if (data.type === 'completed') {
              setStatusMessage(data.message || 'Property listing created successfully!')
              setStatusType('success')
              completeCurrentQuery()
              setIsRecording(false)
              setPartialTranscript('')
              setAccumulatedTranscript('')
              // Clear queue on completion
              setQueryQueue([])
              queryQueueRef.current = []

              // Redirect to seller page after completion
              setTimeout(() => {
                router.push('/seller')
              }, 2000)
            } else if (data.type === 'error') {
              setStatusMessage(data.message || 'An error occurred')
              setStatusType('error')
              // Mark current query as error and process next
              const errorId = currentQueryIdRef.current
              if (errorId) {
                setQueryQueue((prev) =>
                  prev.map((q) => (q.id === errorId ? { ...q, status: 'error' } : q)),
                )
              }
              // Clear timeout
              if (queryTimeoutRef.current) {
                clearTimeout(queryTimeoutRef.current)
                queryTimeoutRef.current = null
              }
              isProcessingQueryRef.current = false
              currentQueryIdRef.current = null
              setCurrentQueryId(null)
              setIsProcessing(false)
              // Process next query after error
              setTimeout(() => processNextQuery(), 500)
            } else if (data.type === 'agent') {
              setStatusMessage(data.message || '')
              setStatusType('info')
              // Don't complete query on agent messages - they're just informational
            } else if (data.type === 'processing') {
              setIsProcessing(true)
              setStatusMessage(data.message || 'Processing...')
              setStatusType('info')
            }
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e)
          }
        }

        ws.onerror = (error) => {
          console.error('❌ WebSocket error:', error)
          setWsConnected(false)
          setStatusMessage('Connection error. Please try again.')
          setStatusType('error')
        }

        ws.onclose = () => {
          console.log('🔌 WebSocket disconnected')
          setWsConnected(false)
          // Mark current query as error if processing
          const disconnectedId = currentQueryIdRef.current
          if (isProcessingQueryRef.current && disconnectedId) {
            setQueryQueue((prev) =>
              prev.map((q) => (q.id === disconnectedId ? { ...q, status: 'error' } : q)),
            )
            isProcessingQueryRef.current = false
            currentQueryIdRef.current = null
            setCurrentQueryId(null)
            setIsProcessing(false)
          }
          if (isVoiceMode && isRecording) {
            // Attempt to reconnect after a delay
            setTimeout(() => {
              if (isVoiceMode) {
                connectWebSocket()
              }
            }, 3000)
          }
        }
      } catch (error) {
        console.error('Failed to create WebSocket:', error)
        setStatusMessage('Failed to connect. Please try again.')
        setStatusType('error')
      }
    }

    if (isVoiceMode) {
      connectWebSocket()
    }

    return () => {
      // Only close WebSocket if voice mode is explicitly disabled
      // Don't close just because component re-renders or form is edited
      if (!isVoiceMode && wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [API_BASE_URL, clerkId, isVoiceMode, completeCurrentQuery, processNextQuery])

  // Auto-process queue when WebSocket connects or queue changes
  useEffect(() => {
    if (wsConnected && queryQueue.length > 0 && !isProcessingQueryRef.current) {
      // Small delay to ensure WebSocket is fully ready
      const timer = setTimeout(() => {
        processNextQuery()
      }, 100)
      return () => clearTimeout(timer)
    }
  }, [wsConnected, queryQueue.length, processNextQuery])

  // Initialize Web Speech API
  useEffect(() => {
    if (typeof window === 'undefined') return

    // Suppress noisy browser console errors for known Web Speech network hiccups
    const originalConsoleError = console.error
    console.error = (...args: any[]) => {
      if (
        args.length &&
        typeof args[0] === 'string' &&
        args[0].includes('Speech recognition error: network')
      ) {
        return
      }
      originalConsoleError(...args)
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

    if (!SpeechRecognition) {
      console.warn('Web Speech API not supported in this browser')
      return
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interimTranscript = ''
      let finalTranscript = ''

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' '
        } else {
          interimTranscript += transcript
        }
      }

      // Show partial transcript in real-time
      if (interimTranscript) {
        setPartialTranscript(interimTranscript)
      }

      // Clear pause timer when new speech is detected
      if (pauseTimerRef.current) {
        clearTimeout(pauseTimerRef.current)
        pauseTimerRef.current = null
      }

      // Accumulate final transcripts
      if (finalTranscript.trim()) {
        accumulatedTextRef.current += ' ' + finalTranscript.trim()
        setAccumulatedTranscript(accumulatedTextRef.current)
        setPartialTranscript('') // Clear interim when we have final

        // Set a 2.5-second pause timer to form a new query
        if (pauseTimerRef.current) {
          clearTimeout(pauseTimerRef.current)
        }
        pauseTimerRef.current = setTimeout(() => {
          if (accumulatedTextRef.current.trim()) {
            const queryText = accumulatedTextRef.current.trim()
            // Create a new query and add to queue
            const newQuery: QueuedQuery = {
              id: `query_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
              text: queryText,
              timestamp: Date.now(),
              status: 'pending',
            }

            setQueryQueue((prev) => {
              const updated = [...prev, newQuery]
              queryQueueRef.current = updated
              // Try to process queue after state update
              setTimeout(() => processNextQuery(), 50)
              return updated
            })

            // Clear accumulated text after adding to queue
            accumulatedTextRef.current = ''
            setAccumulatedTranscript('')
          }
        }, 2500) // 2.5 seconds pause
      }
    }

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      // Handle different error types appropriately
      if (event.error === 'aborted') {
        // "aborted" is usually harmless - happens when recognition is stopped/restarted
        // Don't show this as an error to the user, just log it
        console.log('Speech recognition aborted (normal during restart)')
        // Don't set isRecording to false - let the onend handler manage restart
        return
      } else if (event.error === 'no-speech') {
        // No speech detected - this is normal, don't treat as error
        console.log('No speech detected')
        // Don't stop recording, let it continue listening
        return
      } else if (event.error === 'audio-capture') {
        console.error('Speech recognition error: audio-capture')
        setStatusMessage('Microphone not found. Please check your settings.')
        setStatusType('error')
        setIsRecording(false)
      } else if (event.error === 'network') {
        // Network hiccup — treat as handled and avoid noisy console.error
        try {
          // Best-effort to prevent bubbling to the console
          ;(event as any)?.preventDefault?.()
          ;(event as any)?.stopPropagation?.()
        } catch (_) {
          // ignore
        }
        console.warn('Speech recognition network issue (handled). Online:', navigator.onLine)
        setStatusMessage(
          navigator.onLine
            ? 'Network issue. Voice input paused—please try again.'
            : 'You appear offline. Voice input paused until connection is restored.'
        )
        setStatusType('error')
        // Stop recording cleanly to avoid restart loops while offline
        isRecordingRef.current = false
        setIsRecording(false)
        setIsVoiceMode(false)
        if (pauseTimerRef.current) {
          clearTimeout(pauseTimerRef.current)
          pauseTimerRef.current = null
        }
        try {
          recognition.abort()
        } catch (e) {
          // Ignore abort errors
        }
        return
      } else if (event.error === 'not-allowed') {
        console.error('Speech recognition error: not-allowed')
        setStatusMessage('Microphone permission denied. Please allow microphone access.')
        setStatusType('error')
        setIsRecording(false)
      } else {
        // Other errors - log but don't necessarily stop
        console.warn('Speech recognition error:', event.error)
        // Only stop if it's a critical error
        if (event.error === 'service-not-allowed' || event.error === 'bad-grammar') {
          setIsRecording(false)
        }
      }
    }

    recognition.onend = () => {
      // Use ref to check recording state (synchronous, not stale closure)
      if (!isRecordingRef.current) {
        console.log('🛑 Recognition ended - not restarting (recording stopped)')
        return
      }

      // Use a small delay to avoid immediate restart issues
      setTimeout(() => {
        // Double-check ref again (it might have changed during timeout)
        if (isRecordingRef.current && recognitionRef.current) {
          try {
            recognitionRef.current.start()
            console.log('🔄 Speech recognition restarted (onend handler)')
          } catch (e: any) {
            if (
              e.code === 11 ||
              e.name === 'InvalidStateError' ||
              e.name === 'AbortError' ||
              e.message?.includes('aborted')
            ) {
              console.log('🔄 Recognition already running or aborted (normal)')
            } else {
              console.warn('Failed to restart recognition:', e)
              // Try again after a longer delay
              setTimeout(() => {
                if (isRecordingRef.current && recognitionRef.current) {
                  try {
                    recognitionRef.current.start()
                    console.log('🔄 Speech recognition restarted (retry)')
                  } catch (e2: any) {
                    if (
                      e2.code !== 11 &&
                      e2.name !== 'InvalidStateError' &&
                      e2.name !== 'AbortError' &&
                      !e2.message?.includes('aborted')
                    ) {
                      console.error('Failed to restart recognition (retry):', e2)
                      isRecordingRef.current = false
                      setIsRecording(false)
                    }
                  }
                }
              }, 500)
            }
          }
        }
      }, 150)
    }

    recognitionRef.current = recognition

    return () => {
      // Restore console.error
      console.error = originalConsoleError

      if (pauseTimerRef.current) {
        clearTimeout(pauseTimerRef.current)
      }
      // Use ref for cleanup check
      if (!isRecordingRef.current && recognitionRef.current) {
        try {
          recognitionRef.current.abort()
        } catch (e) {
          // Ignore errors when stopping
        }
      }
    }
  }, [clerkId, isRecording])

  const startVoiceInput = () => {
    if (!recognitionRef.current) {
      setStatusMessage('Speech recognition not available in this browser.')
      setStatusType('error')
      return
    }

    isRecordingRef.current = true
    setIsVoiceMode(true)
    setIsRecording(true)
    setStatusMessage('Listening... Please describe your property.')
    setStatusType('info')

    try {
      recognitionRef.current.start()
    } catch (e: any) {
      // Handle common errors gracefully
      if (
        e.code === 11 ||
        e.name === 'InvalidStateError' ||
        e.name === 'AbortError' ||
        e.message?.includes('aborted')
      ) {
        // Already started or aborted - this is normal, just log
        console.log('Recognition already running or aborted (normal)')
        // Don't show error to user, recognition is likely already working
      } else {
        console.error('Failed to start recognition:', e)
        setStatusMessage('Failed to start voice input. Please try again.')
        setStatusType('error')
        isRecordingRef.current = false
        setIsRecording(false)
      }
    }
  }

  const stopVoiceInput = () => {
    // CRITICAL: Set ref to false FIRST to prevent restart in onend handler
    isRecordingRef.current = false
    setIsRecording(false)
    setIsVoiceMode(false)
    
    if (pauseTimerRef.current) {
      clearTimeout(pauseTimerRef.current)
      pauseTimerRef.current = null
    }

    // Stop recognition BEFORE processing accumulated text
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort() // Use abort() instead of stop() for immediate termination
        console.log('🛑 Speech recognition aborted')
      } catch (e: any) {
        // Ignore errors when stopping (might already be stopped)
        if (
          e.name !== 'InvalidStateError' &&
          e.name !== 'AbortError' &&
          !e.message?.includes('aborted')
        ) {
          console.warn('Error stopping recognition:', e)
        }
      }
    }

    // Add any remaining accumulated text to queue
    if (accumulatedTextRef.current.trim()) {
      const queryText = accumulatedTextRef.current.trim()
      const newQuery: QueuedQuery = {
        id: `query_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
        text: queryText,
        timestamp: Date.now(),
        status: 'pending',
      }

      setQueryQueue((prev) => {
        const updated = [...prev, newQuery]
        queryQueueRef.current = updated
        // Try to process queue after state update
        setTimeout(() => processNextQuery(), 50)
        return updated
      })

      accumulatedTextRef.current = ''
      setAccumulatedTranscript('')
    }

    setPartialTranscript('')
    setStatusMessage('Voice input stopped.')
    setStatusType('info')
  }

  const handleInputChange = (field: keyof PropertyFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setUploadingImages(true)
    setStatusMessage('Uploading images...')
    setStatusType('info')

    try {
      if (!API_BASE_URL || !clerkId) {
        throw new Error('API URL or Clerk ID not available')
      }

      const formData = new FormData()
      Array.from(files).forEach((file) => {
        formData.append('files', file)
      })

      const response = await fetch(
        `${API_BASE_URL}/api/storage/upload?clerk_id=${encodeURIComponent(clerkId)}`,
        {
          method: 'POST',
          body: formData,
        },
      )

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }))
        throw new Error(errorData.detail || 'Failed to upload images')
      }

      const result = await response.json()
      setFormData((prev) => ({
        ...prev,
        images: [...prev.images, ...result.urls],
      }))
      setStatusMessage(`${result.count} image(s) uploaded successfully!`)
      setStatusType('success')
    } catch (error: any) {
      console.error('Error uploading images:', error)
      setStatusMessage(error.message || 'Failed to upload images')
      setStatusType('error')
    } finally {
      setUploadingImages(false)
      // Reset file input
      e.target.value = ''
    }
  }

  const removeImage = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      images: prev.images.filter((_, i) => i !== index),
    }))
  }

  const generateDescription = async () => {
    setIsGeneratingDescription(true)
    setStatusMessage('Generating description...')
    setStatusType('info')

    try {
      if (!API_BASE_URL || !clerkId) {
        throw new Error('API URL or Clerk ID not available')
      }

      // Prepare property data for description generation
      const propertyData = {
        title: formData.title || 'Property',
        description: formData.description || '',
        price: formData.price ? parseFloat(formData.price) : null,
        property_type: formData.property_type || '',
        area_sqft: formData.area_sqft ? parseFloat(formData.area_sqft) : null,
        bedrooms: formData.bedrooms ? parseInt(formData.bedrooms) : null,
        bathrooms: formData.bathrooms ? parseInt(formData.bathrooms) : null,
        floors: formData.floors ? parseInt(formData.floors) : null,
        city: formData.city || '',
        area: formData.area || '',
      }

      const response = await fetch(
        `${API_BASE_URL}/api/properties/generate-description?clerk_id=${encodeURIComponent(clerkId)}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(propertyData),
        },
      )

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ detail: 'Failed to generate description' }))
        throw new Error(errorData.detail || 'Failed to generate description')
      }

      const result = await response.json()
      if (result.description) {
        setFormData((prev) => ({ ...prev, description: result.description }))
        setStatusMessage('Description generated successfully!')
        setStatusType('success')
      } else {
        throw new Error('No description generated')
      }
    } catch (error: any) {
      console.error('Error generating description:', error)
      setStatusMessage(error.message || 'Failed to generate description')
      setStatusType('error')
    } finally {
      setIsGeneratingDescription(false)
    }
  }

  const handleAudioFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file type
    const validTypes = [
      'audio/mpeg',
      'audio/mp3',
      'audio/wav',
      'audio/ogg',
      'audio/webm',
      'audio/m4a',
      'audio/x-m4a',
    ]
    if (!validTypes.includes(file.type) && !file.name.match(/\.(mp3|wav|ogg|webm|m4a)$/i)) {
      setStatusMessage('Please upload a valid audio file (MP3, WAV, OGG, WebM, M4A)')
      setStatusType('error')
      return
    }

    // Check file size (max 25MB)
    if (file.size > 25 * 1024 * 1024) {
      setStatusMessage('Audio file is too large. Maximum size is 25MB.')
      setStatusType('error')
      return
    }

    setUploadingAudio(true)
    setStatusMessage('Uploading and transcribing audio...')
    setStatusType('info')

    try {
      if (!API_BASE_URL || !clerkId) {
        throw new Error('API URL or Clerk ID not available')
      }

      const formData = new FormData()
      formData.append('audio_file', file)

      const response = await fetch(
        `${API_BASE_URL}/api/properties/transcribe-audio?clerk_id=${encodeURIComponent(clerkId)}`,
        {
          method: 'POST',
          body: formData,
        },
      )

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ detail: 'Failed to transcribe audio' }))
        throw new Error(errorData.detail || 'Failed to transcribe audio')
      }

      const result = await response.json()
      if (result.transcript) {
        // Add transcribed text to query queue
        const newQuery: QueuedQuery = {
          id: `query_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
          text: result.transcript,
          timestamp: Date.now(),
          status: 'pending',
        }

        setQueryQueue((prev) => {
          const updated = [...prev, newQuery]
          queryQueueRef.current = updated
          // Try to process queue after state update
          setTimeout(() => processNextQuery(), 50)
          return updated
        })

        setStatusMessage(
          `Audio transcribed successfully! Processing: "${result.transcript.substring(0, 100)}${result.transcript.length > 100 ? '...' : ''}"`,
        )
        setStatusType('success')
      } else {
        throw new Error('No transcript generated')
      }
    } catch (error: any) {
      console.error('Error transcribing audio:', error)
      setStatusMessage(error.message || 'Failed to transcribe audio')
      setStatusType('error')
    } finally {
      setUploadingAudio(false)
      // Reset file input
      if (audioInputRef.current) {
        audioInputRef.current.value = ''
      }
    }
  }

  const calculateProgress = () => {
    const filled = REQUIRED_FIELDS.filter((field) => {
      const value = formData[field]
      return value !== '' && value !== null && value !== undefined
    }).length
    return Math.round((filled / REQUIRED_FIELDS.length) * 100)
  }

  const getMissingFieldsList = () => {
    return REQUIRED_FIELDS.filter((field) => {
      const value = formData[field]
      return !value || value === ''
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setStatusMessage('Creating property listing...')
    setStatusType('info')

    try {
      if (!API_BASE_URL || !clerkId) {
        throw new Error('API URL or Clerk ID not available')
      }

      // Validate required fields before submitting
      const price = parseFloat(formData.price)
      const areaSqft = parseFloat(formData.area_sqft)
      const bedrooms = parseInt(formData.bedrooms)
      const bathrooms = parseInt(formData.bathrooms)
      // lat/lng are optional - only parse if provided
      const lng = formData.lng ? parseFloat(formData.lng) : null
      const lat = formData.lat ? parseFloat(formData.lat) : null

      if (isNaN(price) || price <= 0) {
        throw new Error('Price must be a valid positive number')
      }
      if (isNaN(areaSqft) || areaSqft <= 0) {
        throw new Error('Area must be a valid positive number')
      }
      if (isNaN(bedrooms) || bedrooms < 0) {
        throw new Error('Bedrooms must be a valid non-negative number')
      }
      if (isNaN(bathrooms) || bathrooms < 0) {
        throw new Error('Bathrooms must be a valid non-negative number')
      }
      // Only validate lat/lng if they were provided
      if (formData.lng && (lng === null || isNaN(lng))) {
        throw new Error('Longitude must be a valid number')
      }
      if (formData.lat && (lat === null || isNaN(lat))) {
        throw new Error('Latitude must be a valid number')
      }

      const payload: any = {
        title: formData.title.trim(),
        description: formData.description.trim(),
        price: price,
        property_type: formData.property_type,
        area_sqft: areaSqft,
        bedrooms: bedrooms,
        bathrooms: bathrooms,
        floors: parseInt(formData.floors) || 1,
        city: formData.city.trim(),
        area: formData.area.trim(),
        images: formData.images.filter((img) => img.trim() !== ''),
      }
      
      // Only include lat/lng if they have valid values
      if (lng !== null && !isNaN(lng)) {
        payload.lng = lng
      }
      if (lat !== null && !isNaN(lat)) {
        payload.lat = lat
      }

      const response = await fetch(
        `${API_BASE_URL}/api/properties?clerk_id=${encodeURIComponent(clerkId)}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        },
      )

      if (!response.ok) {
        let errorMessage = 'Failed to create property listing'
        try {
          const errorData = await response.json()
          // Handle different error response formats
          if (errorData.detail) {
            // FastAPI validation errors can be a list or a string
            if (Array.isArray(errorData.detail)) {
              errorMessage = errorData.detail
                .map((err: any) => {
                  if (typeof err === 'object' && err.msg) {
                    return `${err.loc?.join('.')}: ${err.msg}`
                  }
                  return String(err)
                })
                .join(', ')
            } else {
              errorMessage = String(errorData.detail)
            }
          } else if (errorData.message) {
            errorMessage = String(errorData.message)
          } else if (typeof errorData === 'string') {
            errorMessage = errorData
          }
        } catch (parseError) {
          // If JSON parsing fails, use the status text
          errorMessage = response.statusText || 'Unknown error occurred'
        }
        throw new Error(errorMessage)
      }

      const result = await response.json()
      setStatusMessage('Property listing created successfully!')
      setStatusType('success')

      // Redirect to seller page
      setTimeout(() => {
        router.push('/seller')
      }, 1500)
    } catch (error: any) {
      console.error('Error creating property:', error)
      // Extract error message properly
      let errorMessage = 'Failed to create property listing'
      if (error instanceof Error) {
        errorMessage = error.message
      } else if (typeof error === 'string') {
        errorMessage = error
      } else if (error && typeof error === 'object') {
        errorMessage = error.message || error.detail || JSON.stringify(error)
      }
      setStatusMessage(errorMessage)
      setStatusType('error')
    } finally {
      setIsSubmitting(false)
    }
  }

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/sign-in')
    }
  }, [loading, isAuthenticated, router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[linear-gradient(to_bottom,rgba(249,249,249,0.85),rgba(237,236,232,0.9))]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[color:var(--color-primary)] mx-auto mb-4"></div>
          <p className="text-[color:var(--color-primary)]">Loading...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  const progress = calculateProgress()
  const missing = getMissingFieldsList()

  return (
    <div className="min-h-screen bg-[linear-gradient(to_bottom,rgba(249,249,249,0.85),rgba(237,236,232,0.9))] text-[color:var(--color-primary)]">
      <div className="max-w-4xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-4 text-[color:var(--color-primary)]">
            Create Property Listing
          </h1>
          <p className="text-slate-700">
            Fill out the form manually or use voice input to describe your property. Fields will be
            filled in real-time.
          </p>
        </div>

        {/* Progress Indicator */}
        <div className="mb-8 rounded-2xl bg-white/70 backdrop-blur-xl border border-slate-200 shadow-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-slate-700">Progress</span>
            <span className="text-sm font-bold text-[color:var(--color-primary)]">{progress}%</span>
          </div>
          <div className="w-full bg-slate-200 rounded-full h-3 mb-4">
            <motion.div
              className="h-3 rounded-full bg-[linear-gradient(to_right,#f59e0b,var(--color-accent-gold))]"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          {missing.length > 0 && (
            <div className="text-sm text-slate-600">
              <span className="font-semibold">Missing fields:</span>{' '}
              {missing.map((field) => field.replace('_', ' ')).join(', ')}
            </div>
          )}
        </div>

        {/* Status Message */}
        <AnimatePresence>
          {statusMessage && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className={`mb-6 rounded-xl p-4 flex items-center gap-3 ${
                statusType === 'success'
                  ? 'bg-green-50 border border-green-200 text-green-800'
                  : statusType === 'error'
                    ? 'bg-red-50 border border-red-200 text-red-800'
                    : 'bg-blue-50 border border-blue-200 text-blue-800'
              }`}
            >
              {statusType === 'success' ? (
                <CheckCircleIcon className="h-5 w-5 flex-shrink-0" />
              ) : statusType === 'error' ? (
                <ExclamationCircleIcon className="h-5 w-5 flex-shrink-0" />
              ) : (
                <SparklesIcon className="h-5 w-5 flex-shrink-0" />
              )}
              <span className="text-sm font-medium">{statusMessage}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Voice Input Controls */}
        <div className="mb-8 space-y-4">
          <div className="flex gap-4 flex-wrap">
            {!isRecording ? (
              <>
                <button
                  onClick={startVoiceInput}
                  className="flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white bg-[linear-gradient(to_right,#f59e0b,var(--color-accent-gold))] hover:scale-105 active:scale-95 transition-all shadow-md"
                >
                  <MicrophoneIcon className="h-5 w-5" />
                  Start Voice Input
                </button>
                <label className="flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white bg-blue-600 hover:bg-blue-700 hover:scale-105 active:scale-95 transition-all shadow-md cursor-pointer">
                  <input
                    ref={audioInputRef}
                    type="file"
                    accept="audio/*,.mp3,.wav,.ogg,.webm,.m4a"
                    onChange={handleAudioFileUpload}
                    className="hidden"
                    disabled={uploadingAudio}
                  />
                  {uploadingAudio ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                      Processing...
                    </>
                  ) : (
                    <>
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={1.5}
                        stroke="currentColor"
                        className="h-5 w-5"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 01-.99-3.467l2.31-.66A2.25 2.25 0 009 15.553z"
                        />
                      </svg>
                      Upload Audio File
                    </>
                  )}
                </label>
              </>
            ) : (
              <button
                onClick={stopVoiceInput}
                className="flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white bg-red-600 hover:bg-red-700 hover:scale-105 active:scale-95 transition-all shadow-md"
              >
                <StopIcon className="h-5 w-5" />
                Stop Recording
              </button>
            )}
            {wsConnected && (
              <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-green-50 border border-green-200">
                <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse"></div>
                <span className="text-sm font-medium text-green-800">Connected</span>
              </div>
            )}
            {isProcessing && (
              <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-blue-50 border border-blue-200">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span className="text-sm font-medium text-blue-800">Processing...</span>
              </div>
            )}
          </div>

          {/* Partial Transcript Display */}
          {(partialTranscript || accumulatedTranscript) && (
            <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
              <div className="text-xs font-semibold text-slate-600 mb-2">Live Transcript:</div>
              <div className="text-sm text-slate-800">
                {accumulatedTranscript && (
                  <span className="text-slate-700">{accumulatedTranscript}</span>
                )}
                {partialTranscript && (
                  <span className="text-slate-400 italic">{partialTranscript}</span>
                )}
              </div>
            </div>
          )}

          {/* Query Queue Display */}
          {queryQueue.length > 0 && (
            <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
              <div className="text-xs font-semibold text-slate-600 mb-3 flex items-center justify-between">
                <span>
                  Query Queue ({queryQueue.filter((q) => q.status !== 'completed').length} active)
                </span>
                <button
                  onClick={() => {
                    setQueryQueue([])
                    queryQueueRef.current = []
                  }}
                  className="text-xs text-red-600 hover:text-red-700"
                >
                  Clear Queue
                </button>
              </div>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {queryQueue
                  .filter((q) => q.status !== 'completed')
                  .map((query) => (
                    <div
                      key={query.id}
                      className={`p-3 rounded-lg border text-sm ${
                        query.status === 'processing'
                          ? 'bg-blue-50 border-blue-300'
                          : query.status === 'error'
                            ? 'bg-red-50 border-red-300'
                            : 'bg-white border-slate-300'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            {query.status === 'processing' && (
                              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600"></div>
                            )}
                            {query.status === 'pending' && (
                              <div className="h-3 w-3 rounded-full bg-yellow-500"></div>
                            )}
                            {query.status === 'error' && (
                              <ExclamationCircleIcon className="h-4 w-4 text-red-600" />
                            )}
                            <span
                              className={`text-xs font-semibold ${
                                query.status === 'processing'
                                  ? 'text-blue-700'
                                  : query.status === 'error'
                                    ? 'text-red-700'
                                    : 'text-yellow-700'
                              }`}
                            >
                              {query.status === 'processing'
                                ? 'Processing...'
                                : query.status === 'error'
                                  ? 'Error'
                                  : 'Pending'}
                            </span>
                          </div>
                          <p className="text-slate-700 line-clamp-2">{query.text}</p>
                        </div>
                        {query.status === 'error' && (
                          <button
                            onClick={() => {
                              setQueryQueue((prev) =>
                                prev.map((q) =>
                                  q.id === query.id ? { ...q, status: 'pending' } : q,
                                ),
                              )
                              setTimeout(() => processNextQuery(), 100)
                            }}
                            className="text-xs px-2 py-1 rounded bg-red-100 text-red-700 hover:bg-red-200"
                          >
                            Retry
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid md:grid-cols-2 gap-6">
            {/* Title */}
            <div className="md:col-span-2">
              <label className="block text-sm font-semibold mb-2 text-slate-700">Title *</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => handleInputChange('title', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="e.g., Beautiful 3-Bedroom House in F-10"
                required
              />
            </div>

            {/* Description */}
            <div className="md:col-span-2">
              <label className="block text-sm font-semibold mb-2 text-slate-700">
                Description *
              </label>
              <div className="relative">
                <textarea
                  value={formData.description}
                  onChange={(e) => handleInputChange('description', e.target.value)}
                  rows={4}
                  className="w-full px-4 py-3 pr-24 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                  placeholder="Describe your property..."
                  required
                />
                <button
                  type="button"
                  onClick={generateDescription}
                  disabled={isGeneratingDescription}
                  className="absolute bottom-2 left-2 px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-100 text-blue-700 hover:bg-blue-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-1"
                >
                  {isGeneratingDescription ? (
                    <>
                      <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600"></div>
                      Generating...
                    </>
                  ) : (
                    <>
                      <SparklesIcon className="h-3 w-3" />
                      Generate
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Price */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">
                Price (PKR) *
              </label>
              <input
                type="number"
                value={formData.price}
                onChange={(e) => handleInputChange('price', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="15000000"
                required
                min="0"
                step="0.01"
              />
            </div>

            {/* Property Type */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">
                Property Type *
              </label>
              <select
                value={formData.property_type}
                onChange={(e) => handleInputChange('property_type', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                required
              >
                <option value="">Select type</option>
                <option value="house">House</option>
                <option value="apartment">Apartment</option>
                <option value="plot">Plot</option>
                <option value="commercial">Commercial</option>
                <option value="villa">Villa</option>
                <option value="flat">Flat</option>
              </select>
            </div>

            {/* Area (sqft) */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">
                Area (sqft) *
              </label>
              <input
                type="number"
                value={formData.area_sqft}
                onChange={(e) => handleInputChange('area_sqft', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="2500"
                required
                min="0"
                step="0.01"
              />
            </div>

            {/* Bedrooms */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">Bedrooms *</label>
              <input
                type="number"
                value={formData.bedrooms}
                onChange={(e) => handleInputChange('bedrooms', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="3"
                required
                min="0"
              />
            </div>

            {/* Bathrooms */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">Bathrooms *</label>
              <input
                type="number"
                value={formData.bathrooms}
                onChange={(e) => handleInputChange('bathrooms', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="2"
                required
                min="0"
              />
            </div>

            {/* Floors */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">Floors</label>
              <input
                type="number"
                value={formData.floors}
                onChange={(e) => handleInputChange('floors', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="1"
                min="1"
              />
            </div>

            {/* City */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">City *</label>
              <input
                type="text"
                value={formData.city}
                onChange={(e) => handleInputChange('city', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="Islamabad"
                required
              />
            </div>

            {/* Area/Sector */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">
                Area/Sector *
              </label>
              <input
                type="text"
                value={formData.area}
                onChange={(e) => handleInputChange('area', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="F-10/3"
                required
              />
            </div>

            {/* Longitude */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">Longitude (Optional)</label>
              <input
                type="number"
                value={formData.lng}
                onChange={(e) => handleInputChange('lng', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="73.0479"
                step="0.0001"
              />
            </div>

            {/* Latitude */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">Latitude (Optional)</label>
              <input
                type="number"
                value={formData.lat}
                onChange={(e) => handleInputChange('lat', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="33.6844"
                step="0.0001"
              />
            </div>
          </div>

          {/* Image Upload Section */}
          <div className="md:col-span-2">
            <label className="block text-sm font-semibold mb-2 text-slate-700">
              Property Images
            </label>
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 cursor-pointer transition-all">
                  <PhotoIcon className="h-5 w-5" />
                  {uploadingImages ? 'Uploading...' : 'Upload Images'}
                  <input
                    type="file"
                    multiple
                    accept="image/*"
                    onChange={handleImageUpload}
                    className="hidden"
                    disabled={uploadingImages}
                  />
                </label>
                {uploadingImages && (
                  <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[color:var(--color-primary)]"></div>
                    <span className="text-sm text-slate-600">Uploading...</span>
                  </div>
                )}
              </div>

              {/* Image Preview Grid */}
              {formData.images.length > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {formData.images.map((url, index) => (
                    <div key={index} className="relative group">
                      <img
                        src={url}
                        alt={`Property ${index + 1}`}
                        className="w-full h-32 object-cover rounded-xl border border-slate-200"
                      />
                      <button
                        type="button"
                        onClick={() => removeImage(index)}
                        className="absolute top-2 right-2 p-1 rounded-full bg-red-500 text-white opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex gap-4 pt-6">
            <button
              type="submit"
              disabled={isSubmitting || missing.length > 0}
              className="flex-1 px-8 py-4 rounded-xl font-semibold text-white bg-[linear-gradient(to_right,#f59e0b,var(--color-accent-gold))] hover:scale-105 active:scale-95 transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
            >
              {isSubmitting ? 'Creating...' : 'Create Listing'}
            </button>
            <button
              type="button"
              onClick={() => router.back()}
              className="px-6 py-4 rounded-xl font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 transition-all"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
