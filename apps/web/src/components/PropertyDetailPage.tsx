'use client'

import { useState } from 'react'
import { 
  HomeModernIcon,
  MapPinIcon,
  BanknotesIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'

type Property = {
  _id: string
  title: string
  price: number
  city: string
  area?: string
  bedrooms: number
  bathrooms: number
  area_sqft: number
  floors?: number
  images?: string[]
  property_type: string
  description?: string
  lat?: number
  lng?: number
}

export default function PropertyDetailPage({ property }: { property: Property }) {
  const [currentImageIndex, setCurrentImageIndex] = useState(0)

  const showNextImage = () => {
    if (!property?.images || property.images.length === 0) return
    setCurrentImageIndex((prev) => (prev + 1) % property.images.length)
  }

  const showPrevImage = () => {
    if (!property?.images || property.images.length === 0) return
    setCurrentImageIndex((prev) => (prev - 1 + property.images.length) % property.images.length)
  }

  return (
    <div className="max-w-7xl mx-auto p-4 lg:p-10 grid grid-cols-1 lg:grid-cols-3 gap-10">
      <div className="lg:col-span-2 space-y-10">
        {/* Hero Gallery */}
        <section className="rounded-3xl shadow-xl overflow-hidden bg-white">
          <div className="relative aspect-[5/3] bg-slate-100">
            {property.images && property.images.length > 0 ? (
              <img
                src={property.images[currentImageIndex]}
                alt={property.title}
                className="w-full h-full object-cover"
                onError={(e) => { (e.currentTarget as any).style.display = 'none' }}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <HomeModernIcon className="h-16 w-16 text-slate-400" />
              </div>
            )}

            {property.images && property.images.length > 1 && (
              <>
                <button
                  type="button"
                  onClick={showPrevImage}
                  className="absolute left-4 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white text-gray-700 rounded-full w-10 h-10 flex items-center justify-center shadow"
                  aria-label="Previous image"
                >
                  <ArrowLeftIcon className="w-5 h-5" />
                </button>
                <button
                  type="button"
                  onClick={showNextImage}
                  className="absolute right-4 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white text-gray-700 rounded-full w-10 h-10 flex items-center justify-center shadow"
                  aria-label="Next image"
                >
                  <ArrowRightIcon className="w-5 h-5" />
                </button>
              </>
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-black/10 to-transparent pointer-events-none" />
          </div>

          {property.images && property.images.length > 1 && (
            <div className="flex items-center justify-center gap-2 p-3">
              {property.images.map((_, idx) => (
                <button
                  key={idx}
                  className={`w-2.5 h-2.5 rounded-full ${idx === currentImageIndex ? 'bg-indigo-600' : 'bg-slate-300'} transition-colors`}
                  onClick={() => setCurrentImageIndex(idx)}
                  aria-label={`Go to image ${idx + 1}`}
                />
              ))}
            </div>
          )}
        </section>

        {/* Title & Price */}
        <section className="bg-white rounded-2xl p-6 shadow-md">
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
            <h1 className="text-3xl font-extrabold text-gray-900">{property.title}</h1>
            <div className="flex items-center">
              <BanknotesIcon className="h-6 w-6 text-green-600 mr-2" />
              <span className="text-4xl md:text-5xl font-extrabold text-green-700">Rs {Number(property.price || 0).toLocaleString()}</span>
            </div>
          </div>
          <div className="flex items-center flex-wrap gap-2 text-slate-600 mt-3">
            <span className="inline-flex items-center px-3 py-1 rounded-full bg-indigo-100 text-indigo-800 text-sm font-medium">
              <MapPinIcon className="h-4 w-4 mr-1" />
              {property.city}{property.area ? ` • ${property.area}` : ''}
            </span>
            <span className="inline-flex items-center px-3 py-1 rounded-full bg-slate-100 text-slate-700 text-sm font-medium capitalize">
              {property.property_type}
            </span>
          </div>
        </section>

        {/* Quick Facts */}
        <section className="bg-white rounded-2xl shadow-md overflow-hidden">
          <div className="flex justify-between divide-x divide-gray-200 p-4">
            <div className="flex-1 text-center">
              <HomeModernIcon className="h-6 w-6 text-indigo-600 mx-auto" />
              <p className="text-xl font-bold mt-1 text-gray-900">{property.bedrooms}</p>
              <p className="text-sm text-gray-500">Bedrooms</p>
            </div>
            <div className="flex-1 text-center">
              <HomeModernIcon className="h-6 w-6 text-indigo-600 mx-auto" />
              <p className="text-xl font-bold mt-1 text-gray-900">{property.bathrooms}</p>
              <p className="text-sm text-gray-500">Bathrooms</p>
            </div>
            <div className="flex-1 text-center">
              <span className="text-2xl font-bold text-indigo-600">📐</span>
              <p className="text-xl font-bold mt-1 text-gray-900">{Number(property.area_sqft || 0).toLocaleString()} sqft</p>
              <p className="text-sm text-gray-500">Area</p>
            </div>
          </div>
        </section>

        {/* Description */}
        {property.description && (
          <section className="bg-white rounded-2xl p-6 shadow-md">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Description</h2>
            <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{property.description}</p>
          </section>
        )}

        {/* Map Placeholder */}
        <section className="rounded-2xl shadow-md overflow-hidden bg-white">
          <div className="h-96 bg-gradient-to-br from-slate-100 to-slate-200 relative flex items-center justify-center">
            <div className="absolute top-4 left-4 inline-flex items-center px-3 py-1 rounded-full bg-indigo-600 text-white text-sm font-medium shadow">
              <MapPinIcon className="h-4 w-4 mr-1" /> {property.city}
            </div>
            <span className="text-slate-500">Map placeholder</span>
          </div>
        </section>
      </div>

      {/* Sticky Sidebar */}
      <aside className="lg:col-span-1 lg:sticky lg:top-8 h-fit">
        <div className="bg-white rounded-2xl p-6 shadow-xl border border-indigo-100">
          <h3 className="text-lg font-semibold text-gray-900">Interested in this property?</h3>
          <p className="text-sm text-slate-600 mt-1">Contact the agent to schedule a visit or learn more.</p>
          <button className="w-full mt-4 bg-indigo-600 text-white py-3.5 rounded-xl font-medium shadow-lg hover:bg-indigo-700 transition-colors">Contact Agent</button>
          <div className="mt-4 space-y-2 text-sm text-slate-600">
            <div className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-600 mr-2" /> Verified listing</div>
            <div className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-600 mr-2" /> No obligation enquiry</div>
          </div>
        </div>
      </aside>
    </div>
  )
}


