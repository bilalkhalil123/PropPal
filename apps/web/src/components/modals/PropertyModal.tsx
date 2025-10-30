"use client"

import Link from "next/link"
import { XMarkIcon, HomeModernIcon, BanknotesIcon, MapPinIcon } from "@heroicons/react/24/outline"

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
  if (!isOpen || !property) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="property-modal-title"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" />
      <div
        className="relative bg-white rounded-2xl shadow-xl w-full max-w-4xl mx-4 overflow-hidden border border-slate-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <h2 id="property-modal-title" className="text-lg font-semibold text-gray-900">
            {property.title}
          </h2>
          <button aria-label="Close" onClick={onClose} className="p-2 rounded-lg hover:bg-slate-100 transition-colors">
            <XMarkIcon className="w-5 h-5 text-slate-600" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div className="w-full">
            <div
              className="relative h-80 w-full bg-slate-100 rounded-xl overflow-hidden flex items-center justify-center cursor-zoom-in"
              onClick={() => {
                if (property?.images && property.images.length > 0) {
                  onOpenLightbox()
                }
              }}
            >
              {property.images && property.images.length > 0 ? (
                <img
                  src={property.images[currentImageIndex] || "/placeholder.svg"}
                  alt={property.title}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    const target = e.currentTarget as HTMLElement
                    // @ts-expect-error style exists on HTMLElement
                    target.style.display = "none"
                  }}
                />
              ) : (
                <HomeModernIcon className="h-14 w-14 text-slate-400" />
              )}

              {property.images && property.images.length > 1 && (
                <>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      onPrev()
                    }}
                    className="absolute left-2 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white text-gray-700 rounded-full w-9 h-9 flex items-center justify-center shadow-sm"
                    aria-label="Previous image"
                  >
                    ‹
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      onNext()
                    }}
                    className="absolute right-2 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white text-gray-700 rounded-full w-9 h-9 flex items-center justify-center shadow-sm"
                    aria-label="Next image"
                  >
                    ›
                  </button>
                </>
              )}
            </div>

            {property.images && property.images.length > 1 && (
              <div className="flex items-center justify-center gap-2 mt-3">
                {property.images.map((_, idx) => (
                  <button
                    key={idx}
                    aria-label={`Go to image ${idx + 1}`}
                    className={`w-2.5 h-2.5 rounded-full ${idx === currentImageIndex ? "bg-indigo-600" : "bg-slate-300"} transition-colors`}
                    onClick={() => onDotClick(idx)}
                  />
                ))}
              </div>
            )}
          </div>

          <div className="flex items-center">
            <BanknotesIcon className="h-5 w-5 text-green-600 mr-2" />
            <span className="text-2xl font-bold text-green-600">Rs {property.price.toLocaleString()}</span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm text-gray-700">
            <div className="flex items-center">
              <MapPinIcon className="h-4 w-4 text-gray-500 mr-2" />
              <span>{property.city}</span>
            </div>
            <div className="flex items-center justify-start gap-4">
              <span>{property.bedrooms} bed</span>
              <span>{property.bathrooms} bath</span>
              <span>{property.area_sqft} sqft</span>
            </div>
            <div className="col-span-2 flex items-center justify-between">
              <span className="text-xs uppercase tracking-wide text-gray-500">{property.property_type}</span>
              {property.score && (
                <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                  Match: {Math.round(property.score * 100)}%
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="px-5 py-4 border-t border-slate-200 flex justify-end gap-2">
          <Link
            href={`/properties/${property._id}`}
            className="px-4 py-2 rounded-xl border border-indigo-600 text-indigo-600 hover:bg-indigo-50 transition-colors"
          >
            View Full Details
          </Link>
          <button
            onClick={onClose}
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
  )
}


