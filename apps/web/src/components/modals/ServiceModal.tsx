'use client'

import { useState } from 'react'
import Link from 'next/link'
import { XMarkIcon, BanknotesIcon, CalendarIcon, SparklesIcon, ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { startAndNavigateToConversation } from '@/lib/conversation-utils'
import { api } from '@/lib/api-client'

type Service = {
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

interface ServiceModalProps {
  isOpen: boolean
  service: Service
  onClose: () => void
}

export default function ServiceModal({ isOpen, service, onClose }: ServiceModalProps) {
  const { clerkId, isAuthenticated } = useCurrentUser()
  const [isStartingChat, setIsStartingChat] = useState(false)

  if (!isOpen || !service) return null

  const handleContact = async () => {
    if (!isAuthenticated || !clerkId) {
      window.location.href = '/sign-in?redirect=/chat'
      return
    }
    if (!service.builder_id) {
      alert('Unable to contact. Builder information not available.')
      return
    }
    
    setIsStartingChat(true)
    try {
      const builder: any = await api.builders.getById(service.builder_id)
      if (!builder || !builder.user_id) {
        alert('Unable to contact builder. Builder user information not available.')
        return
      }
      const serviceName = service.service_name || service.title || 'Service'
      const result = await startAndNavigateToConversation({
        clerkId,
        participantId: builder.user_id,
        conversationType: 'direct',
        initialMessage: `Hi, I'm interested in your service: ${serviceName}`,
      })
      if (!result.success) {
        alert(result.error || 'Failed to start conversation')
      }
    } catch (error) {
      console.error('Error starting conversation:', error)
      alert('Failed to start conversation')
    } finally {
      setIsStartingChat(false)
    }
  }

  const serviceTitle = service.service_name || service.title || 'Service'
  const priceDisplay = service.base_price
    ? `Rs ${service.base_price.toLocaleString()} ${service.price_unit || ''}`
    : service.price_range_min || service.price_range_max
      ? `Rs ${service.price_range_min?.toLocaleString() || ''} - Rs ${service.price_range_max?.toLocaleString() || ''}`
      : 'Price on request'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="service-modal-title"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" />
      <div
        className="relative bg-white rounded-2xl shadow-xl w-full max-w-3xl mx-4 overflow-hidden border border-slate-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <h2 id="service-modal-title" className="text-lg font-semibold text-gray-900">
            {serviceTitle}
          </h2>
          <button
            aria-label="Close"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <XMarkIcon className="w-5 h-5 text-slate-600" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center">
                  <SparklesIcon className="h-6 w-6 text-amber-700" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">{serviceTitle}</h3>
                  {service.category && (
                    <div className="flex items-center text-sm text-gray-600 mt-1">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                        {service.category}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
            {service.score && (
              <div className="flex items-center gap-4">
                <div className="text-sm text-gray-700 flex items-center">
                  <span className="bg-amber-100 text-amber-800 px-2 py-1 rounded-full text-xs font-medium">
                    {Math.round(service.score * 100)}% match
                  </span>
                </div>
              </div>
            )}
          </div>

          {service.description && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Description</h4>
              <p className="text-sm text-gray-700 leading-relaxed">{service.description}</p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center gap-2">
              <BanknotesIcon className="h-5 w-5 text-teal-600" />
              <div>
                <p className="text-xs text-gray-500">Price</p>
                <p className="text-sm font-semibold text-gray-900">{priceDisplay}</p>
              </div>
            </div>

            {service.estimated_duration && (
              <div className="flex items-center gap-2">
                <CalendarIcon className="h-5 w-5 text-amber-600" />
                <div>
                  <p className="text-xs text-gray-500">Estimated Duration</p>
                  <p className="text-sm font-semibold text-gray-900">
                    {service.estimated_duration}
                  </p>
                </div>
              </div>
            )}
          </div>

          {service.service_features && service.service_features.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Features</h4>
              <div className="flex flex-wrap gap-2">
                {service.service_features.map((feature, idx) => (
                  <span
                    key={idx}
                    className="bg-teal-100 text-teal-800 px-2 py-1 rounded-full text-xs"
                  >
                    {feature}
                  </span>
                ))}
              </div>
            </div>
          )}

          {service.service_images && service.service_images.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Service Images</h4>
              <div className="grid grid-cols-3 gap-2">
                {service.service_images.slice(0, 6).map((url, idx) => (
                  <div key={idx} className="relative aspect-square overflow-hidden rounded-lg">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={url}
                      alt={`Service ${idx + 1}`}
                      className="w-full h-full object-cover hover:scale-105 transition-transform"
                    />
                  </div>
                ))}
              </div>
              {service.service_images.length > 6 && (
                <p className="text-xs text-gray-500 mt-2">+{service.service_images.length - 6} more images</p>
              )}
            </div>
          )}
        </div>

        <div className="px-5 py-4 border-t border-slate-200 flex justify-end gap-2">
          {service.builder_id && (
            <Link
              href={`/builders/${service.builder_id}`}
              className="px-4 py-2 rounded-xl border border-amber-600 text-amber-700 hover:bg-amber-50 transition-colors"
            >
              View Builder
            </Link>
          )}
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-slate-300 text-gray-700 hover:bg-slate-50 transition-colors"
          >
            Close
          </button>
          <button 
            onClick={handleContact}
            disabled={isStartingChat}
            className="px-4 py-2 rounded-xl bg-amber-600 text-white hover:bg-amber-700 transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            {isStartingChat ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Starting...
              </>
            ) : (
              <>
                <ChatBubbleLeftRightIcon className="h-4 w-4" />
                Contact
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
