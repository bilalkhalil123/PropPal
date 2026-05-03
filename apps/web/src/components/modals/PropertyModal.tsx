"use client"

import Link from "next/link"
import { useState } from "react"
import {
  XMarkIcon,
  HomeModernIcon,
  BanknotesIcon,
  MapPinIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  BuildingOffice2Icon,
  ChatBubbleLeftRightIcon,
} from "@heroicons/react/24/outline"
import { useCurrentUser } from "@/hooks/useCurrentUser"
import { startAndNavigateToConversation } from "@/lib/conversation-utils"

type Property = {
  _id: string
  title: string
  price: number
  city: string
  area?: string
  bedrooms: number
  bathrooms: number
  area_sqft: number
  amenity_summary?: string
  images?: string[]
  property_type: string
  score?: number
  user_id?: string
  owner_id?: string
}

interface PropertyModalProps {
  isOpen: boolean
  property: Property
  currentImageIndex: number
  onClose: () => void
  onPrev: () => void
  onNext: () => void
  onDotClick: (index: number) => void
  onOpenLightbox: () => void
}

export default function PropertyModal({
  isOpen,
  property,
  currentImageIndex,
  onClose,
  onPrev,
  onNext,
  onDotClick,
  onOpenLightbox,
}: PropertyModalProps) {
  const { clerkId, isAuthenticated } = useCurrentUser()
  const [isStartingChat, setIsStartingChat] = useState(false)

  if (!isOpen || !property) return null

  const handleContactAgent = async () => {
    if (!isAuthenticated || !clerkId) {
      window.location.href = '/sign-in?redirect=/chat'
      return
    }
    const ownerId = property.user_id || property.owner_id
    if (!ownerId) {
      alert('Unable to contact property owner. Owner information not available.')
      return
    }
    setIsStartingChat(true)
    try {
      const result = await startAndNavigateToConversation({
        clerkId,
        participantId: ownerId,
        conversationType: 'direct',
        initialMessage: `Hi, I'm interested in your property: ${property.title}`,
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

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="property-modal-title"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity" />
      <div
        className="relative bg-white border border-slate-200 rounded-3xl shadow-2xl w-full max-w-5xl max-h-[95vh] flex flex-col overflow-hidden animate-in fade-in-50 slide-in-from-bottom-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-white">
          <h2 id="property-modal-title" className="text-lg font-semibold text-slate-900 tracking-tight">
            {property.title}
          </h2>
          <button
            aria-label="Close"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-100 transition"
          >
            <XMarkIcon className="w-5 h-5 text-slate-600" />
          </button>
        </div>

        {/* Scrollable Content Container */}
        <div className="overflow-y-auto flex-1 min-h-0 custom-scrollbar">
          {/* Image Section */}
          <div className="relative shrink-0">
          <div
            className="relative h-80 sm:h-96 w-full overflow-hidden flex items-center justify-center cursor-zoom-in rounded-none"
            onClick={property?.images?.length ? onOpenLightbox : undefined}
          >
            {property.images && property.images.length > 0 ? (
              <>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={property.images[currentImageIndex] || "/placeholder.svg"}
                  alt={property.title}
                  className="w-full h-full object-cover transition-transform duration-500 hover:scale-105"
                />
              </>
            ) : (
              <HomeModernIcon className="h-16 w-16 text-slate-400" />
            )}

            {/* Overlay Gradient */}
            <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black/40 to-transparent"></div>

            {/* Navigation Buttons */}
            {property.images && property.images.length > 1 && (
              <>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    onPrev()
                  }}
                  className="absolute left-4 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white text-slate-700 rounded-full w-9 h-9 flex items-center justify-center shadow-md transition"
                >
                  <ChevronLeftIcon className="w-5 h-5" />
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    onNext()
                  }}
                  className="absolute right-4 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white text-slate-700 rounded-full w-9 h-9 flex items-center justify-center shadow-md transition"
                >
                  <ChevronRightIcon className="w-5 h-5" />
                </button>
              </>
            )}
          </div>

          {/* Image Dots */}
          {property.images && property.images.length > 1 && (
            <div className="flex items-center justify-center gap-2 mt-3 mb-4">
              {property.images.map((_, idx) => (
                <button
                  key={idx}
                  className={`w-2.5 h-2.5 rounded-full transition-all ${
                    idx === currentImageIndex
                      ? "bg-indigo-500 scale-110 shadow-md"
                      : "bg-slate-300 hover:bg-slate-400"
                  }`}
                  onClick={() => onDotClick(idx)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Details */}
        <div className="p-6 space-y-5 text-slate-800 bg-white">
          <div className="flex items-center gap-2">
            <BanknotesIcon className="h-6 w-6 text-green-600" />
            <span className="text-2xl font-bold text-green-700">
              Rs {property.price.toLocaleString()}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <MapPinIcon className="h-4 w-4 text-slate-500" />
              <span>{property.area ? `${property.area}, ${property.city}` : property.city}</span>
            </div>
            <div className="flex items-center gap-3">
              <span>{property.bedrooms} bed</span>
              <span>{property.bathrooms} bath</span>
              <span>{property.area_sqft} sqft</span>
            </div>
            <div className="flex items-center gap-2">
              <BuildingOffice2Icon className="h-4 w-4 text-slate-500" />
              <span className="text-xs uppercase tracking-wide text-slate-500">
                {property.property_type}
              </span>
            </div>
          </div>

          {property.score && (
            <div className="bg-indigo-50 text-indigo-700 px-3 py-2 rounded-lg inline-block text-xs font-medium border border-indigo-100 mt-2">
              Match Score: {Math.round(property.score * 100)}%
            </div>
          )}

          {property.amenity_summary && (
            <div className="mt-4 p-4 rounded-xl bg-gradient-to-br from-indigo-50/50 to-white border border-indigo-100/50">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">🏘️</span>
                <h4 className="font-semibold text-sm text-[color:var(--color-primary)]">Neighborhood Highlights</h4>
              </div>
              <p className="text-sm text-slate-600 leading-relaxed italic text-ellipsis overflow-hidden line-clamp-3">
                &quot;{property.amenity_summary}&quot;
              </p>
            </div>
          )}
        </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 bg-white flex flex-wrap justify-end gap-3 shrink-0">
          <Link
            href={`/properties/${property._id}`}
            className="px-4 py-2.5 rounded-xl border border-indigo-600 text-indigo-700 hover:bg-indigo-50 transition-colors font-medium"
          >
            View Details
          </Link>
          <button
            onClick={onClose}
            className="px-4 py-2.5 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors font-medium"
          >
            Close
          </button>
          <button
            onClick={handleContactAgent}
            disabled={isStartingChat}
            className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold hover:from-indigo-500 hover:to-purple-500 transition-colors shadow-lg flex items-center gap-2 disabled:opacity-50"
          >
            {isStartingChat ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Starting Chat...
              </>
            ) : (
              <>
                <ChatBubbleLeftRightIcon className="h-4 w-4" />
                Contact Agent
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
