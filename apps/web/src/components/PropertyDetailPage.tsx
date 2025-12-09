"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { MapPinIcon, CheckCircleIcon } from "@heroicons/react/24/outline"
import { ChevronLeftIcon, ChevronRightIcon } from "@heroicons/react/24/solid"
import ImageLightbox from "./modals/ImageLightbox"
import PropertyMap from "./PropertyMap"

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
  const [current, setCurrent] = useState(0)
  const [isLightboxOpen, setIsLightboxOpen] = useState(false)
  const images = property.images && property.images.length > 0 ? property.images : ["/placeholder.svg"]

  // Auto-slide every 5 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrent((prev) => (prev + 1) % images.length)
    }, 10000)
    return () => clearInterval(timer)
  }, [images.length])

  const next = () => setCurrent((prev) => (prev + 1) % images.length)
  const prev = () => setCurrent((prev) => (prev - 1 + images.length) % images.length)

  return (
    <div className="min-h-screen bg-[linear-gradient(to_bottom,rgba(249,249,249,0.85),rgba(237,236,232,0.9))] text-[color:var(--color-primary)]">
      {/* ImageLightbox - for fullscreen gallery */}
      <ImageLightbox
        isOpen={isLightboxOpen}
        images={images}
        title={property.title}
        currentIndex={current}
        onClose={() => setIsLightboxOpen(false)}
        onPrev={prev}
        onNext={next}
        onDotClick={setCurrent}
      />

      {/* Full-Width Hero Gallery */}
      <section className="relative h-[90vh] w-full overflow-hidden flex items-center justify-center">
        <AnimatePresence mode="wait">
          <motion.img
            key={current}
            src={images[current]}
            alt={property.title}
            initial={{ opacity: 0, scale: 1.05 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.05 }}
            transition={{ duration: 0.8 }}
            className="absolute inset-0 w-full h-full object-cover cursor-zoom-in"
            onClick={() => setIsLightboxOpen(true)}
          />
        </AnimatePresence>

        {/* Gradient Overlay */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/20 to-white/60 backdrop-blur-[2px] pointer-events-none" />

        {/* Title Overlay */}
        <div className="relative text-center max-w-4xl px-6 z-10">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-5xl md:text-6xl font-bold mb-4 text-white drop-shadow-lg"
          >
            {property.title}
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="text-lg text-white/90"
          >
            <MapPinIcon className="w-5 h-5 inline-block mr-1 text-[color:var(--color-accent-gold)]" />
            {property.city}
            {property.area ? ` • ${property.area}` : ""} • {property.property_type}
          </motion.p>
        </div>

        {/* Slider Controls */}
        {images.length > 1 && (
          <>
            <button
              onClick={prev}
              className="absolute left-8 top-1/2 -translate-y-1/2 bg-white/20 hover:bg-white/40 backdrop-blur-md transition-all rounded-full p-3 shadow-lg border border-white/40"
            >
              <ChevronLeftIcon className="w-6 h-6 text-white drop-shadow" />
            </button>
            <button
              onClick={next}
              className="absolute right-8 top-1/2 -translate-y-1/2 bg-white/20 hover:bg-white/40 backdrop-blur-md transition-all rounded-full p-3 shadow-lg border border-white/40"
            >
              <ChevronRightIcon className="w-6 h-6 text-white drop-shadow" />
            </button>

            {/* Dots Indicator */}
            <div className="absolute bottom-10 left-1/2 -translate-x-1/2 flex gap-3">
              {images.map((_, i) => (
                <div
                  key={i}
                  onClick={() => setCurrent(i)}
                  className={`w-3 h-3 rounded-full cursor-pointer transition-all duration-300 ${
                    i === current
                      ? "bg-[color:var(--color-accent-gold)] scale-125 shadow-[0_0_10px_var(--color-accent-gold)]"
                      : "bg-white/60 hover:bg-white/90"
                  }`}
                />
              ))}
            </div>

            {/* Thumbnails Row */}
            <div className="absolute bottom-20 left-1/2 -translate-x-1/2 w-[95%] md:w-[80%] flex gap-3 overflow-x-auto no-scrollbar rounded-xl bg-white/15 backdrop-blur-lg p-3 border border-white/20">
              {images.map((src, i) => (
                <button
                  key={i}
                  onClick={() => setCurrent(i)}
                  className={`relative shrink-0 rounded-xl overflow-hidden border-2 transition-all duration-300 ${
                    i === current
                      ? "border-[color:var(--color-accent-gold)] ring-2 ring-[color:var(--color-accent-gold)]/40"
                      : "border-transparent opacity-80 hover:opacity-100"
                  }`}
                  tabIndex={-1}
                  aria-label={`Go to image ${i + 1}`}
                >
                  <img src={src} alt={`Preview ${i + 1}`} className="h-20 w-32 object-cover" onClick={() => setIsLightboxOpen(true)} />
                </button>
              ))}
            </div>
          </>
        )}
      </section>

      {/* Property Overview Section */}
      <section className="relative py-20">
        <div className="absolute inset-x-0 top-0 mx-auto h-48 w-[80%] rounded-3xl bg-gradient-to-r from-cyan-50 to-teal-50 blur-3xl opacity-60 -z-10" />
        <div className="max-w-6xl mx-auto px-6 md:px-12 lg:px-20">
          <div className="grid md:grid-cols-3 gap-8">
            {/* Info Card */}
            <div className="md:col-span-2 space-y-8">
              <div className="rounded-3xl bg-white/70 backdrop-blur-xl border border-slate-200 shadow-lg p-8 hover:shadow-xl transition-all">
                <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-6">
                  <div>
                    <h2 className="text-3xl font-bold mb-2 text-[color:var(--color-primary)]">
                      Rs {Number(property.price).toLocaleString()}
                    </h2>
                    <p className="text-slate-600 font-medium capitalize">{property.property_type}</p>
                  </div>
                  <div className="flex flex-wrap gap-3 mt-4 sm:mt-0">
                    <div className="px-4 py-2 bg-[color:var(--color-primary)] text-white rounded-xl text-sm font-semibold shadow-md">
                      {property.bedrooms} Bedrooms
                    </div>
                    <div className="px-4 py-2 bg-[color:var(--color-primary)] text-white rounded-xl text-sm font-semibold shadow-md">
                      {property.bathrooms} Bathrooms
                    </div>
                    <div className="px-4 py-2 bg-[color:var(--color-primary)] text-white rounded-xl text-sm font-semibold shadow-md">
                      {property.area_sqft} sqft
                    </div>
                  </div>
                </div>
                <p className="text-slate-700 leading-relaxed">
                  {property.description || "No description provided for this property."}
                </p>
              </div>
            </div>

            {/* Sidebar */}
            <div>
              <div className="rounded-3xl bg-white/80 backdrop-blur-xl border border-slate-200 shadow-lg p-8 hover:shadow-xl transition-all">
                <h3 className="text-2xl font-bold text-[color:var(--color-primary)] mb-4">Interested?</h3>
                <p className="text-slate-600 mb-6">
                  Schedule a visit or connect with the builder today. Our team is available 24/7.
                </p>
                <button className="w-full py-3 rounded-xl font-semibold text-white bg-[linear-gradient(to_right,#f59e0b,var(--color-accent-gold))] hover:scale-[1.02] active:scale-95 transition-all shadow-md">
                  Contact Agent
                </button>
                <ul className="mt-6 space-y-3 text-sm text-slate-600">
                  <li className="flex items-center gap-2">
                    <CheckCircleIcon className="h-5 w-5 text-green-600" /> Verified Listing
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircleIcon className="h-5 w-5 text-green-600" /> No Hidden Fees
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircleIcon className="h-5 w-5 text-green-600" /> AI-Matched Recommendations
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Map Section */}
      {property.lat && property.lng && (
        <section className="relative py-20">
          <div className="absolute inset-x-0 top-0 mx-auto h-48 w-[80%] rounded-3xl bg-gradient-to-r from-cyan-50 to-teal-50 blur-3xl opacity-60 -z-10" />
          <div className="max-w-6xl mx-auto px-6 md:px-12 lg:px-20">
            <PropertyMap
              lat={property.lat}
              lng={property.lng}
              title={property.title}
              city={property.city}
              area={property.area}
            />
          </div>
        </section>
      )}

      {/* CTA Section */}
      <section
        className="py-28 relative overflow-hidden"
        style={{
          backgroundImage: "linear-gradient(to right, var(--color-primary), var(--color-accent-gold))",
        }}
      >
        <div className="absolute inset-0 bg-[radial-gradient(600px_300px_at_10%_10%,rgba(255,255,255,0.18),transparent),radial-gradient(700px_400px_at_90%_80%,rgba(255,255,255,0.15),transparent)]" />
        <div className="relative max-w-4xl mx-auto text-center px-6 md:px-12">
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Looking for More Properties Like This?
          </h2>
          <p className="text-lg text-white/90 mb-10">
            Explore similar listings with our AI-powered property search.
          </p>
          <a
            href="/chat"
            className="inline-block px-10 py-4 rounded-xl text-lg font-semibold transition-all duration-200 active:scale-95 transform hover:scale-105 shadow-xl bg-white text-[color:var(--color-primary)] hover:bg-slate-50"
          >
            Try AI Property Search
          </a>
        </div>
      </section>
    </div>
  )
}
