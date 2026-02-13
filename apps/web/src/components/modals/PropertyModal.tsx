"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useState } from "react"
import {
  XMarkIcon,
  HomeModernIcon,
  BanknotesIcon,
  MapPinIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  BuildingOffice2Icon,
} from "@heroicons/react/24/outline"
import { useCurrentUser } from "@/hooks/useCurrentUser"
import { api } from "@/lib/api-client"
import { useAuth, SignIn } from "@clerk/nextjs"

type Property = {
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
  const router = useRouter()
  const { isAuthenticated, loading: authLoading } = useCurrentUser()
  const { getToken } = useAuth()
  const [isContacting, setIsContacting] = useState(false)
  const [contactError, setContactError] = useState<string | null>(null)
  const [showAuthModal, setShowAuthModal] = useState(false)

  if (!isOpen || !property) return null

  const handleContactAgent = async () => {
    // Check if user is authenticated
    if (!isAuthenticated || authLoading) {
      // Open in-page auth modal instead of redirecting
      setShowAuthModal(true)
      return
    }

    // User is authenticated, proceed with contact
    setIsContacting(true)
    setContactError(null)

    try {
      // Get Clerk token for authenticated request
      const token = await getToken()
      if (!token) {
        throw new Error("Unable to get authentication token")
      }

      // Call the contact endpoint
      const response = await api.properties.contactSeller(property._id, undefined, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      // Show success message and redirect to chat or show seller info
      if (response.success) {
        // Option 1: Redirect to chat with pre-filled message
        const chatMessage = `Hi, I'm interested in ${property.title} (${property.city}). Can you tell me more about this property?`
        onClose() // Close modal first
        router.push(`/chat?q=${encodeURIComponent(chatMessage)}`)
      }
    } catch (error: any) {
      console.error("Error contacting seller:", error)
      setContactError(
        error.message || "Failed to contact seller. Please try again."
      )
    } finally {
      setIsContacting(false)
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
        className="relative bg-white border border-slate-200 rounded-3xl shadow-2xl w-full max-w-5xl overflow-hidden animate-in fade-in-50 slide-in-from-bottom-4"
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

        {/* Image Section */}
        <div className="relative">
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
              <span>{property.city}</span>
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
            <div className="bg-indigo-50 text-indigo-700 px-3 py-2 rounded-lg inline-block text-xs font-medium border border-indigo-100">
              Match Score: {Math.round(property.score * 100)}%
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 bg-white flex flex-wrap justify-end gap-3">
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
            disabled={isContacting || authLoading}
            className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold hover:from-indigo-500 hover:to-purple-500 transition-colors shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isContacting ? "Contacting..." : "Contact Agent"}
          </button>
          {contactError && (
            <p className="w-full text-sm text-red-600 mt-2">{contactError}</p>
          )}
        </div>
      </div>

      {/* Auth Modal for Contact Agent (shown when not logged in) */}
      {showAuthModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4">
          <div className="relative bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 border border-slate-200">
            <button
              aria-label="Close"
              onClick={() => setShowAuthModal(false)}
              className="absolute right-4 top-4 p-1.5 rounded-full hover:bg-slate-100 text-slate-500"
            >
              ✕
            </button>
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-slate-900">
                Sign in to contact the agent
              </h2>
              <p className="text-sm text-slate-600 mt-1">
                Please log in or sign up to send a message about this property.
              </p>
            </div>
            <div className="flex justify-center">
              <SignIn
                routing="hash"
                appearance={{
                  variables: {
                    colorPrimary: "var(--color-accent-gold)",
                    colorText: "#111827",
                    colorBackground: "#ffffff",
                    borderRadius: "12px",
                    fontSize: "15px",
                  },
                  elements: {
                    card: "shadow-none border-0 p-0",
                    headerTitle: "text-slate-900 text-lg font-semibold",
                    headerSubtitle: "text-slate-600 text-sm",
                    formButtonPrimary:
                      "text-white rounded-xl hover:ring-2 hover:ring-[color:var(--color-accent-gold)] active:scale-95 transition-all bg-[linear-gradient(to_right,var(--color-primary),var(--color-accent-gold))]",
                    formFieldInput:
                      "rounded-lg border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus:ring-2 focus:ring-[color:var(--color-accent-gold)] focus:border-[color:var(--color-accent-gold)]",
                    formFieldLabel: "text-slate-900",
                    dividerLine: "bg-slate-200",
                    dividerText: "text-slate-600",
                    footerActionText: "text-slate-700",
                    footerActionLink:
                      "text-[color:var(--color-accent-gold)] hover:text-amber-600",
                    socialButtonsBlockButton:
                      "rounded-lg border-slate-300 hover:bg-slate-50 text-slate-900",
                  },
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
