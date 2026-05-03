"use client"

import { useState } from "react"
import Link from "next/link"
import { XMarkIcon, HomeModernIcon, MapPinIcon, CalendarIcon, ChatBubbleLeftRightIcon } from "@heroicons/react/24/outline"
import { useCurrentUser } from "@/hooks/useCurrentUser"
import { startAndNavigateToConversation } from "@/lib/conversation-utils"

type Builder = {
  _id: string
  company_name: string
  specialization: string[]
  experience_years: number
  rating?: number
  location?: { city: string }
  about?: string
  score?: number
  portfolio_images?: string[]
  user_id?: string
}

interface BuilderModalProps {
  isOpen: boolean
  builder: Builder
  onClose: () => void
}

export default function BuilderModal({ isOpen, builder, onClose }: BuilderModalProps) {
  const { clerkId, isAuthenticated } = useCurrentUser()
  const [isStartingChat, setIsStartingChat] = useState(false)
  if (!isOpen || !builder) return null

  const handleContact = async () => {
    if (!isAuthenticated || !clerkId) {
      window.location.href = '/sign-in?redirect=/messages'
      return
    }
    const builderId = builder.user_id
    if (!builderId) {
      alert('Unable to contact builder. Builder user information not available.')
      return
    }
    setIsStartingChat(true)
    try {
      const result = await startAndNavigateToConversation({
        clerkId,
        participantId: builderId,
        conversationType: 'direct',
        initialMessage: `Hi, I'm interested in your services at ${builder.company_name}.`,
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
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="builder-modal-title"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" />
      <div
        className="relative bg-white rounded-2xl shadow-xl w-full max-w-3xl mx-4 overflow-hidden border border-slate-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <h2 id="builder-modal-title" className="text-lg font-semibold text-gray-900">
            {builder.company_name}
          </h2>
          <button aria-label="Close" onClick={onClose} className="p-2 rounded-lg hover:bg-slate-100 transition-colors">
            <XMarkIcon className="w-5 h-5 text-slate-600" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center">
                  <HomeModernIcon className="h-6 w-6 text-amber-700" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">{builder.company_name}</h3>
                  {builder.location?.city && (
                    <div className="flex items-center text-sm text-gray-600 mt-1">
                      <MapPinIcon className="h-4 w-4 mr-1" />
                      <span>{builder.location.city}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-sm text-gray-700 flex items-center">
                <CalendarIcon className="h-4 w-4 mr-1" />
                <span>{builder.experience_years} years</span>
              </div>
              {builder.rating && (
                <div className="text-sm text-gray-700 flex items-center">
                  <span className="text-yellow-500">★</span>
                  <span className="ml-1">{builder.rating}</span>
                </div>
              )}
            </div>
          </div>

          {builder.specialization && builder.specialization.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Specializations</h4>
              <div className="flex flex-wrap gap-2">
                {builder.specialization.map((spec, idx) => (
                  <span key={idx} className="bg-amber-100 text-amber-800 px-2 py-1 rounded-full text-xs">
                    {spec}
                  </span>
                ))}
              </div>
            </div>
          )}

          {builder.about && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">About</h4>
              <p className="text-sm text-gray-700 leading-relaxed">{builder.about}</p>
            </div>
          )}

          {builder.portfolio_images && builder.portfolio_images.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Portfolio</h4>
              <div className="grid grid-cols-3 gap-2">
                {builder.portfolio_images.slice(0, 6).map((url, idx) => (
                  <div key={idx} className="relative aspect-square overflow-hidden rounded-lg">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={url}
                      alt={`Portfolio ${idx + 1}`}
                      className="w-full h-full object-cover hover:scale-105 transition-transform"
                    />
                  </div>
                ))}
              </div>
              {builder.portfolio_images.length > 6 && (
                <p className="text-xs text-gray-500 mt-2">+{builder.portfolio_images.length - 6} more images</p>
              )}
            </div>
          )}

          {builder.score && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Match</span>
              <span className="bg-amber-100 text-amber-800 px-2 py-1 rounded">{Math.round(builder.score * 100)}%</span>
            </div>
          )}
        </div>

        <div className="px-5 py-4 border-t border-slate-200 flex justify-end gap-2">
          <Link
            href={`/builders/${builder._id}`}
            className="px-4 py-2 rounded-xl border border-amber-600 text-amber-700 hover:bg-amber-50 transition-colors"
          >
            View Full Profile
          </Link>
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


