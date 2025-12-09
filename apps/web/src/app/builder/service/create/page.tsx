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
  ArrowLeftIcon,
  PhotoIcon,
  XMarkIcon,
  MusicalNoteIcon,
} from '@heroicons/react/24/outline'

interface BuilderServiceFormData {
  title: string
  description: string
  category: string
  base_price: string
  price_unit: string
  estimated_duration: string
  service_features: string
  service_images: string[]
}

const REQUIRED_FIELDS: (keyof Omit<BuilderServiceFormData, 'service_images'>)[] = [
  'title',
  'description',
  'category',
  'base_price',
  'price_unit',
]

const CATEGORY_OPTIONS = [
  'Construction',
  'Renovation',
  'Interior Design',
  'Plumbing',
  'Electrical',
  'Painting',
  'Landscaping',
  'HVAC',
  'Roofing',
  'Masonry',
  'Civil',
  'Maintenance',
  'Other',
]

const PRICE_UNIT_OPTIONS = [
  'per sqft',
  'per hour',
  'per day',
  'per room',
  'per project',
  'fixed price',
]

export default function CreateBuilderServicePage() {
  const { user, isAuthenticated, clerkId, loading } = useCurrentUser()
  const router = useRouter()
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL

  const [formData, setFormData] = useState<BuilderServiceFormData>({
    title: '',
    description: '',
    category: '',
    base_price: '',
    price_unit: '',
    estimated_duration: '',
    service_features: '',
    service_images: [],
  })

  const [isVoiceMode, setIsVoiceMode] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const [missingFields, setMissingFields] = useState<string[]>([])
  const [statusMessage, setStatusMessage] = useState<string>('')
  const [statusType, setStatusType] = useState<'info' | 'success' | 'error'>('info')
  const [uploadingImages, setUploadingImages] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [partialTranscript, setPartialTranscript] = useState<string>('')
  const [accumulatedTranscript, setAccumulatedTranscript] = useState<string>('')
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
      const key = 'builder_service_session_id'
      let sid = typeof window !== 'undefined' ? window.localStorage.getItem(key) : null
      if (!sid) {
        sid = `bs_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
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
    if (
      isProcessingQueryRef.current ||
      !wsRef.current ||
      wsRef.current.readyState !== WebSocket.OPEN
    ) {
      return
    }

    const nextQuery = queryQueueRef.current.find((q) => q.status === 'pending')
    if (!nextQuery) {
      return
    }

    isProcessingQueryRef.current = true
    currentQueryIdRef.current = nextQuery.id
    setCurrentQueryId(nextQuery.id)
    setQueryQueue((prev) =>
      prev.map((q) => (q.id === nextQuery.id ? { ...q, status: 'processing' } : q)),
    )

    setIsProcessing(true)
    console.log('📤 Processing query from queue:', nextQuery.text)

    if (queryTimeoutRef.current) {
      clearTimeout(queryTimeoutRef.current)
    }
    const queryIdForTimeout = nextQuery.id
    queryTimeoutRef.current = setTimeout(() => {
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
    }, 30000)

    try {
      wsRef.current.send(
        JSON.stringify({
          type: 'builder_service_form_extract',
          text: nextQuery.text,
          clerk_id: clerkId,
          session_id: sessionIdRef.current,
        }),
      )
    } catch (error) {
      console.error('Error sending query:', error)
      setQueryQueue((prev) =>
        prev.map((q) => (q.id === nextQuery.id ? { ...q, status: 'error' } : q)),
      )
      isProcessingQueryRef.current = false
      currentQueryIdRef.current = null
      setCurrentQueryId(null)
      setIsProcessing(false)
      setTimeout(() => processNextQuery(), 100)
    }
  }, [clerkId])

  // Mark current query as completed and process next
  const completeCurrentQuery = useCallback(() => {
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

    setTimeout(() => {
      setQueryQueue((prev) => prev.filter((q) => q.status !== 'completed'))
    }, 2000)

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
          console.log('✅ WebSocket connected for service creation')
          setWsConnected(true)
          setStatusMessage('Connected. You can start speaking.')
          setStatusType('success')
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            console.log('📨 WebSocket message:', data)

            if (data.type === 'field_update') {
              if (data.updates) {
                const updates = data.updates as Record<string, any>
                setFormData((prev) => {
                  const updated = { ...prev }
                  Object.keys(updates).forEach((key) => {
                    if (key in updated && key !== 'service_images') {
                      const value = updates[key]
                      if (key === 'service_features' && Array.isArray(value)) {
                        updated.service_features = value.join(', ')
                      } else {
                        (updated as any)[key] = String(value)
                      }
                    }
                  })
                  return updated
                })
              }

              if (data.missing_fields) {
                setMissingFields(data.missing_fields)
              }

              if (data.message) {
                setStatusMessage(data.message)
                setStatusType('info')
              }

              completeCurrentQuery()
            } else if (data.type === 'completed') {
              setStatusMessage(data.message || 'Builder service created successfully!')
              setStatusType('success')
              completeCurrentQuery()
              setIsRecording(false)
              setPartialTranscript('')
              setAccumulatedTranscript('')
              setQueryQueue([])
              queryQueueRef.current = []

              setTimeout(() => {
                router.push('/builder')
              }, 2000)
            } else if (data.type === 'error') {
              setStatusMessage(data.message || 'An error occurred')
              setStatusType('error')
              const errorId = currentQueryIdRef.current
              if (errorId) {
                setQueryQueue((prev) =>
                  prev.map((q) => (q.id === errorId ? { ...q, status: 'error' } : q)),
                )
              }
              if (queryTimeoutRef.current) {
                clearTimeout(queryTimeoutRef.current)
                queryTimeoutRef.current = null
              }
              isProcessingQueryRef.current = false
              currentQueryIdRef.current = null
              setCurrentQueryId(null)
              setIsProcessing(false)
              setTimeout(() => processNextQuery(), 500)
            } else if (data.type === 'agent') {
              setStatusMessage(data.message || '')
              setStatusType('info')
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
      if (!isVoiceMode && wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [API_BASE_URL, clerkId, isVoiceMode, completeCurrentQuery, processNextQuery, router, isRecording])

  // Auto-process queue when WebSocket connects
  useEffect(() => {
    if (wsConnected && queryQueue.length > 0 && !isProcessingQueryRef.current) {
      setTimeout(() => processNextQuery(), 100)
    }
  }, [wsConnected, queryQueue.length, processNextQuery])

  // Initialize Web Speech API
  useEffect(() => {
    if (typeof window === 'undefined') return

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

    if (!SpeechRecognition) {
      setStatusMessage('Speech recognition is not supported in this browser.')
      setStatusType('error')
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

      setPartialTranscript(interimTranscript)

      if (finalTranscript) {
        accumulatedTextRef.current += finalTranscript
        setAccumulatedTranscript(accumulatedTextRef.current)

        if (pauseTimerRef.current) {
          clearTimeout(pauseTimerRef.current)
        }
        pauseTimerRef.current = setTimeout(() => {
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
              setTimeout(() => processNextQuery(), 50)
              return updated
            })

            accumulatedTextRef.current = ''
            setAccumulatedTranscript('')
          }
        }, 2000)
      }
    }

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (event.error === 'no-speech') {
        return
      }
      if (event.error === 'aborted') {
        return
      }
      console.error('Speech recognition error:', event.error)
      setStatusMessage(`Speech recognition error: ${event.error}`)
      setStatusType('error')
    }

    recognition.onend = () => {
      // Use ref to check recording state (synchronous, not stale closure)
      if (!isRecordingRef.current) {
        console.log('🛑 Recognition ended - not restarting (recording stopped)')
        return
      }

      setTimeout(() => {
        if (isRecordingRef.current && recognitionRef.current) {
          try {
            recognitionRef.current.start()
            console.log('🔄 Speech recognition restarted')
          } catch (e: any) {
            if (e.name !== 'InvalidStateError' && e.name !== 'AbortError') {
              console.error('Failed to restart recognition:', e)
            }
          }
        }
      }, 150)
    }

    recognitionRef.current = recognition

    return () => {
      if (pauseTimerRef.current) {
        clearTimeout(pauseTimerRef.current)
      }
      if (!isRecordingRef.current && recognitionRef.current) {
        try {
          recognitionRef.current.abort()
        } catch (e) {
          // Ignore
        }
      }
    }
  }, [clerkId, isRecording, isVoiceMode, processNextQuery])

  const startVoiceInput = () => {
    if (!recognitionRef.current) {
      setStatusMessage('Speech recognition not available in this browser.')
      setStatusType('error')
      return
    }

    isRecordingRef.current = true
    setIsVoiceMode(true)
    setIsRecording(true)
    setStatusMessage('Listening... Please describe your service.')
    setStatusType('info')

    try {
      recognitionRef.current.start()
    } catch (e: any) {
      if (
        e.code === 11 ||
        e.name === 'InvalidStateError' ||
        e.name === 'AbortError'
      ) {
        console.log('Recognition already running or aborted')
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

    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort() // Use abort() for immediate termination
        console.log('🛑 Speech recognition aborted')
      } catch (e: any) {
        if (e.name !== 'InvalidStateError' && e.name !== 'AbortError') {
          console.warn('Error stopping recognition:', e)
        }
      }
    }

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

  const handleInputChange = (field: keyof BuilderServiceFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const generateDescription = async () => {
    setIsGeneratingDescription(true)
    setStatusMessage('Generating description...')
    setStatusType('info')

    try {
      if (!API_BASE_URL || !clerkId) {
        throw new Error('API URL or Clerk ID not available')
      }

      // Prepare service data for description generation
      const serviceData = {
        title: formData.title || 'Service',
        category: formData.category || '',
        base_price: formData.base_price ? parseFloat(formData.base_price) : null,
        price_unit: formData.price_unit || '',
        description: formData.description || '',
        service_features: formData.service_features || '',
      }

      const response = await fetch(
        `${API_BASE_URL}/api/builder/service/generate-description?clerk_id=${encodeURIComponent(clerkId)}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(serviceData),
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

      const audioFormData = new FormData()
      audioFormData.append('audio_file', file)

      const response = await fetch(
        `${API_BASE_URL}/api/builder/transcribe-audio?clerk_id=${encodeURIComponent(clerkId)}`,
        {
          method: 'POST',
          body: audioFormData,
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

        // Enable voice mode to connect WebSocket
        setIsVoiceMode(true)

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
    setStatusMessage('Creating builder service...')
    setStatusType('info')

    try {
      if (!API_BASE_URL || !clerkId) {
        throw new Error('API URL or Clerk ID not available')
      }

      const basePrice = parseFloat(formData.base_price)
      if (isNaN(basePrice) || basePrice <= 0) {
        throw new Error('Base price must be a valid positive number')
      }

      // Parse service features from comma-separated string to array
      const featuresArray = formData.service_features
        ? formData.service_features
            .split(',')
            .map((s) => s.trim())
            .filter((s) => s.length > 0)
        : []

      const payload: any = {
        title: formData.title.trim(),
        description: formData.description.trim(),
        category: formData.category.trim(),
        base_price: basePrice,
        price_unit: formData.price_unit.trim(),
        service_images: formData.service_images,
      }

      if (formData.estimated_duration.trim()) {
        payload.estimated_duration = formData.estimated_duration.trim()
      }
      if (featuresArray.length > 0) {
        payload.service_features = featuresArray
      }

      const response = await fetch(
        `${API_BASE_URL}/api/builder/service?clerk_id=${encodeURIComponent(clerkId)}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        },
      )

      if (!response.ok) {
        let errorMessage = 'Failed to create builder service'
        try {
          const errorData = await response.json()
          if (errorData.detail) {
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
          }
        } catch {
          errorMessage = `Server error: ${response.status}`
        }
        throw new Error(errorMessage)
      }

      setStatusMessage('Builder service created successfully!')
      setStatusType('success')

      setTimeout(() => {
        router.push('/builder')
      }, 2000)
    } catch (error: any) {
      console.error('Error creating service:', error)
      setStatusMessage(error.message || 'Failed to create builder service')
      setStatusType('error')
    } finally {
      setIsSubmitting(false)
    }
  }

  const MAX_IMAGES = 5

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    // Check if adding these files would exceed the limit
    const remainingSlots = MAX_IMAGES - formData.service_images.length
    if (remainingSlots <= 0) {
      setStatusMessage(`Maximum ${MAX_IMAGES} images allowed`)
      setStatusType('error')
      e.target.value = ''
      return
    }

    // Limit files to remaining slots
    const filesToUpload = Array.from(files).slice(0, remainingSlots)
    if (files.length > remainingSlots) {
      setStatusMessage(`Only uploading ${remainingSlots} image(s). Maximum ${MAX_IMAGES} allowed.`)
      setStatusType('info')
    }

    setUploadingImages(true)
    if (files.length <= remainingSlots) {
      setStatusMessage('Uploading images...')
      setStatusType('info')
    }

    try {
      if (!API_BASE_URL || !clerkId) {
        throw new Error('API URL or Clerk ID not available')
      }

      const uploadFormData = new FormData()
      filesToUpload.forEach((file) => {
        uploadFormData.append('files', file)
      })

      const response = await fetch(
        `${API_BASE_URL}/api/storage/upload?clerk_id=${encodeURIComponent(clerkId)}`,
        {
          method: 'POST',
          body: uploadFormData,
        },
      )

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }))
        throw new Error(errorData.detail || 'Failed to upload images')
      }

      const result = await response.json()
      setFormData((prev) => ({
        ...prev,
        service_images: [...prev.service_images, ...result.urls].slice(0, MAX_IMAGES),
      }))
      setStatusMessage(`${result.count} image(s) uploaded successfully!`)
      setStatusType('success')
    } catch (error: any) {
      console.error('Error uploading images:', error)
      setStatusMessage(error.message || 'Failed to upload images')
      setStatusType('error')
    } finally {
      setUploadingImages(false)
      e.target.value = ''
    }
  }

  const removeImage = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      service_images: prev.service_images.filter((_, i) => i !== index),
    }))
  }

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/sign-in')
    }
  }, [loading, isAuthenticated, router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-500 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading...</p>
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
          <button
            onClick={() => router.push('/builder')}
            className="flex items-center gap-2 text-slate-600 hover:text-slate-900 mb-4 transition-colors"
          >
            <ArrowLeftIcon className="h-5 w-5" />
            Back to Builder Dashboard
          </button>
          <h1 className="text-4xl font-bold mb-4 text-[color:var(--color-primary)]">
            Add New Service
          </h1>
          <p className="text-slate-700">
            Fill out the form manually or use voice input to describe your service. Fields will be
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
              {missing.map((field) => field.replace(/_/g, ' ')).join(', ')}
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
                      <MusicalNoteIcon className="h-5 w-5" />
                      Upload Audio File
                    </>
                  )}
                </label>
              </>
            ) : (
              <button
                onClick={stopVoiceInput}
                className="flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white bg-red-500 hover:bg-red-600 hover:scale-105 active:scale-95 transition-all shadow-md"
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
            {/* Service Title */}
            <div className="md:col-span-2">
              <label className="block text-sm font-semibold mb-2 text-slate-700">Service Title *</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => handleInputChange('title', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="e.g., Full Home Renovation"
                required
              />
            </div>

            {/* Category */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">Category *</label>
              <select
                value={formData.category}
                onChange={(e) => handleInputChange('category', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                required
              >
                <option value="">Select a category</option>
                {CATEGORY_OPTIONS.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            {/* Base Price */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">Base Price (PKR) *</label>
              <input
                type="number"
                value={formData.base_price}
                onChange={(e) => handleInputChange('base_price', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="e.g., 5000"
                min="0"
                required
              />
            </div>

            {/* Price Unit */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">Price Unit *</label>
              <select
                value={formData.price_unit}
                onChange={(e) => handleInputChange('price_unit', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                required
              >
                <option value="">Select pricing unit</option>
                {PRICE_UNIT_OPTIONS.map((unit) => (
                  <option key={unit} value={unit}>
                    {unit}
                  </option>
                ))}
              </select>
            </div>

            {/* Estimated Duration */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">Estimated Duration (Optional)</label>
              <input
                type="text"
                value={formData.estimated_duration}
                onChange={(e) => handleInputChange('estimated_duration', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="e.g., 2 weeks, 3 days"
              />
            </div>

            {/* Description */}
            <div className="md:col-span-2">
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-semibold text-slate-700">Description *</label>
                <button
                  type="button"
                  onClick={generateDescription}
                  disabled={isGeneratingDescription || (!formData.title && !formData.category)}
                  className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    isGeneratingDescription || (!formData.title && !formData.category)
                      ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                      : 'bg-[linear-gradient(to_right,#f59e0b,var(--color-accent-gold))] text-white hover:scale-105 active:scale-95 shadow-md'
                  }`}
                >
                  <SparklesIcon className="h-4 w-4" />
                  {isGeneratingDescription ? 'Generating...' : 'Generate Description'}
                </button>
              </div>
              <textarea
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                rows={4}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent resize-none"
                placeholder="Describe your service in detail..."
                required
              />
            </div>

            {/* Service Features */}
            <div className="md:col-span-2">
              <label className="block text-sm font-semibold mb-2 text-slate-700">Service Features (Optional)</label>
              <input
                type="text"
                value={formData.service_features}
                onChange={(e) => handleInputChange('service_features', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="e.g., Free consultation, Warranty, Quality materials"
              />
              <p className="text-xs text-slate-500 mt-1">Separate multiple features with commas</p>
            </div>
          </div>

          {/* Image Upload Section */}
          <div className="md:col-span-2">
            <label className="block text-sm font-semibold mb-2 text-slate-700">
              Service Images ({formData.service_images.length}/{MAX_IMAGES})
            </label>
            <div className="space-y-4">
              <div className="flex flex-wrap gap-4">
                <label
                  className={`flex items-center gap-2 px-6 py-3 rounded-xl font-semibold transition-all cursor-pointer ${
                    formData.service_images.length >= MAX_IMAGES || uploadingImages
                      ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                      : 'border-2 border-dashed border-slate-300 text-slate-600 hover:border-[color:var(--color-primary)] hover:text-[color:var(--color-primary)]'
                  }`}
                >
                  <PhotoIcon className="h-5 w-5" />
                  {uploadingImages ? 'Uploading...' : formData.service_images.length >= MAX_IMAGES ? 'Max Images Reached' : 'Upload Images'}
                  <input
                    type="file"
                    multiple
                    accept="image/*"
                    onChange={handleImageUpload}
                    className="hidden"
                    disabled={uploadingImages || formData.service_images.length >= MAX_IMAGES}
                  />
                </label>
                {uploadingImages && (
                  <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-blue-50 border border-blue-200">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    <span className="text-sm font-medium text-blue-800">Uploading...</span>
                  </div>
                )}
              </div>

              {/* Image Preview Grid */}
              {formData.service_images.length > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  {formData.service_images.map((url, index) => (
                    <div key={index} className="relative group">
                      <img
                        src={url}
                        alt={`Service ${index + 1}`}
                        className="w-full h-24 object-cover rounded-xl border border-slate-200"
                      />
                      <button
                        type="button"
                        onClick={() => removeImage(index)}
                        className="absolute top-1 right-1 p-1 rounded-full bg-red-500 text-white opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <p className="text-xs text-slate-500">Upload images showcasing this service (max {MAX_IMAGES})</p>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex justify-end gap-4 pt-4">
            <button
              type="button"
              onClick={() => router.push('/builder')}
              className="px-6 py-3 rounded-xl font-semibold text-slate-600 hover:text-slate-900 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || progress < 100}
              className={`px-8 py-3 rounded-xl font-semibold text-white transition-all ${
                isSubmitting || progress < 100
                  ? 'bg-slate-400 cursor-not-allowed'
                  : 'bg-[linear-gradient(to_right,#f59e0b,var(--color-accent-gold))] hover:scale-105 active:scale-95 shadow-md'
              }`}
            >
              {isSubmitting ? (
                <span className="flex items-center gap-2">
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Creating...
                </span>
              ) : (
                'Create Service'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
