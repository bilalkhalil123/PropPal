"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { MapPinIcon, CheckCircleIcon, HeartIcon as HeartOutline } from "@heroicons/react/24/outline"
import { ChevronLeftIcon, ChevronRightIcon, HeartIcon as HeartSolid } from "@heroicons/react/24/solid"
import ImageLightbox from "./modals/ImageLightbox"
import PropertyMap from "./PropertyMap"
import PropertyBookingChat from "./PropertyBookingChat"
import { useCurrentUser } from "@/hooks/useCurrentUser"
import { api } from "@/lib/api-client"
import { useAuth, SignIn } from "@clerk/nextjs"

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
  amenity_summary?: string
  nearby_amenities?: any
  lat?: number
  lng?: number
}

export default function PropertyDetailPage({ property }: { property: Property }) {
  const [current, setCurrent] = useState(0)
  const [isLightboxOpen, setIsLightboxOpen] = useState(false)
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [bookingChatOpen, setBookingChatOpen] = useState(false)
  
  const [isShortlisted, setIsShortlisted] = useState(false)
  const [toastMsg, setToastMsg] = useState("")
  
  // State for interactive amenity chips
  const [activeAmenityCategory, setActiveAmenityCategory] = useState<string | null>(null)
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState<boolean>(false)

  const { isAuthenticated, loading: authLoading } = useCurrentUser()
  const { getToken } = useAuth()
  const images = property.images && property.images.length > 0 ? property.images : ["/placeholder.svg"]

  // Calculate amenity counts from the raw JSON payload
  const amenityCounts = property.nearby_amenities 
    ? Object.entries(property.nearby_amenities).map(([category, items]: [string, any]) => ({
        category,
        count: Array.isArray(items) ? items.length : 0
      })).filter(c => c.count > 0)
    : []

  // Helper to map categories to emojis/icons
  const getCategoryIcon = (category: string) => {
    const map: Record<string, string> = {
      education: "🎓", healthcare: "🏥", transport: "🚉", 
      shopping: "🛍️", food: "🍽️", entertainment: "🍿",
      parks: "🌳", worship: "🕌", finance: "🏦"
    }
    return map[category] || "📍"
  }

  // Auto-slide every 5 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrent((prev) => (prev + 1) % images.length)
    }, 10000)
    return () => clearInterval(timer)
  }, [images.length])

  const next = () => setCurrent((prev) => (prev + 1) % images.length)
  const prev = () => setCurrent((prev) => (prev - 1 + images.length) % images.length)

  // Check shortlist status
  useEffect(() => {
    if (isAuthenticated) {
      const loadStatus = async () => {
        try {
          const token = await getToken()
          const res = (await api.properties.getFavorites({
            headers: { Authorization: `Bearer ${token}` }
          })) as any
          const isFav = res.properties?.some((p: any) => (p._id || p.id) === property._id)
          setIsShortlisted(!!isFav)
        } catch (error) {
          console.error('Error loading fallback status:', error)
        }
      }
      loadStatus()
    }
  }, [isAuthenticated, property._id, getToken])

  const showToast = (msg: string) => {
    setToastMsg(msg)
    setTimeout(() => setToastMsg(""), 3000)
  }

  const toggleShortlist = async () => {
    if (!isAuthenticated || authLoading) {
      showToast("Please sign in to shortlist properties!")
      return
    }

    const newFav = !isShortlisted
    setIsShortlisted(newFav) // optimistic
    try {
      const token = await getToken()
      const options = { headers: { Authorization: `Bearer ${token}` } }
      
      if (newFav) {
        await api.properties.favorite(property._id, options)
      } else {
        await api.properties.unfavorite(property._id, options)
      }
    } catch (error) {
      console.error("Failed to update shortlist:", error)
      showToast("Failed to update shortlist.")
      setIsShortlisted(!newFav) // revert
    }
  }

  const handleContactAgent = () => {
    if (!isAuthenticated || authLoading) {
      setShowAuthModal(true)
      return
    }
    setBookingChatOpen(true)
  }

  return (
    <div className="min-h-screen bg-[linear-gradient(to_bottom,rgba(249,249,249,0.85),rgba(237,236,232,0.9))] text-[color:var(--color-primary)]">
      {/* Toast Notification */}
      {toastMsg && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-slate-900 text-white px-6 py-3 rounded-full shadow-lg text-sm font-medium animate-in fade-in slide-in-from-top-5">
          {toastMsg}
        </div>
      )}

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
                <div className="relative">
                  <div className={`text-slate-700 leading-relaxed overflow-hidden transition-all duration-300 ${!isDescriptionExpanded ? "max-h-24 line-clamp-3" : ""} relative`}>
                    {property.description || "No description provided for this property."}
                    {!isDescriptionExpanded && property.description && property.description.length > 150 && (
                      <div className="absolute bottom-0 left-0 w-full h-12 bg-gradient-to-t from-white/20 to-transparent" />
                    )}
                  </div>
                  {property.description && property.description.length > 150 && (
                    <button
                      onClick={() => setIsDescriptionExpanded(!isDescriptionExpanded)}
                      className="text-[color:var(--color-primary)] font-semibold mt-2 hover:underline text-sm hover:text-[color:var(--color-accent-gold)] transition-colors"
                    >
                      {isDescriptionExpanded ? "Show Less" : "Read More"}
                    </button>
                  )}
                </div>

                {/* 🌟 Neighborhood Highlights Section */}
                {(property.amenity_summary || amenityCounts.length > 0) && (
                  <div className="mt-10 pt-8 border-t border-slate-100">
                    <h3 className="text-2xl font-bold mb-5 flex items-center gap-2 text-[color:var(--color-primary)]">
                      <span className="text-3xl">🏘️</span> Neighborhood Highlights
                    </h3>
                    
                    {/* Interactive Count Chips */}
                    {amenityCounts.length > 0 && (
                      <div className="flex flex-wrap gap-3 mb-6">
                        {amenityCounts.map((amenity) => (
                          <button
                            key={amenity.category}
                            onClick={() => setActiveAmenityCategory(
                              activeAmenityCategory === amenity.category ? null : amenity.category
                            )}
                            className={`px-4 py-2.5 rounded-full text-sm font-semibold transition-all duration-300 shadow-sm border ${
                              activeAmenityCategory === amenity.category
                                ? "bg-[color:var(--color-primary)] text-white border-[color:var(--color-primary)] scale-105 shadow-md"
                                : "bg-white text-slate-700 border-slate-200 hover:border-[color:var(--color-accent-gold)] hover:text-[color:var(--color-primary)]"
                            }`}
                          >
                            <span className="mr-2 text-base">{getCategoryIcon(amenity.category)}</span>
                            <span className="capitalize">{amenity.category.replace('_', ' ')}</span>
                            <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
                              activeAmenityCategory === amenity.category ? "bg-white/20" : "bg-slate-100 text-slate-500"
                            }`}>
                              {amenity.count}
                            </span>
                          </button>
                        ))}
                      </div>
                    )}
                    
                    {/* Expandable POI details if a category is active */}
                    <AnimatePresence>
                      {activeAmenityCategory && property.nearby_amenities?.[activeAmenityCategory] && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                          className="overflow-hidden mb-6"
                        >
                          <div className="bg-slate-50/80 rounded-2xl p-4 border border-slate-100 text-sm grid grid-cols-1 sm:grid-cols-2 gap-3 shadow-inner">
                            {property.nearby_amenities[activeAmenityCategory].slice(0, 8).map((poi: any, idx: number) => (
                              <div key={idx} className="flex items-center gap-3 bg-white p-3 rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-all">
                                <div className="flex-1 min-w-0">
                                  <p className="font-semibold text-slate-800 truncate">{poi.name || "Unnamed location"}</p>
                                  {(poi.distance_m || poi.distance) ? (
                                    <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1">
                                      <span className="inline-block w-1.5 h-1.5 rounded-full bg-[color:var(--color-accent-gold)]" />
                                      {Math.round(poi.distance_m || poi.distance)} meters away
                                    </p>
                                  ) : null}
                                </div>
                                {poi.rating && (
                                  <div className="flex items-center gap-1 bg-yellow-50 text-yellow-700 px-2 py-1 rounded-md text-xs font-bold border border-yellow-200 shrink-0">
                                    ★ {poi.rating.toFixed(1)}
                                  </div>
                                )}
                              </div>
                            ))}
                            {property.nearby_amenities[activeAmenityCategory].length > 8 && (
                              <div className="text-slate-500 italic text-xs mt-1 col-span-full font-medium ml-2">
                                + {property.nearby_amenities[activeAmenityCategory].length - 8} additional locations nearby
                              </div>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {/* AI Groq Summary Prose */}
                    {property.amenity_summary && (
                      <div className="relative p-6 rounded-2xl bg-gradient-to-br from-indigo-50/50 to-white border border-indigo-100/50">
                        <div className="absolute -top-3 -left-3 text-4xl opacity-20">✨</div>
                        <p className="text-slate-700 leading-relaxed relative z-10 italic">
                          &quot;{property.amenity_summary}&quot;
                        </p>
                        <div className="mt-3 text-right">
                          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 bg-slate-100 px-2 py-1 rounded-md">
                            AI Generated Summary
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Sidebar */}
            <div>
              <div className="rounded-3xl bg-white/80 backdrop-blur-xl border border-slate-200 shadow-lg p-8 hover:shadow-xl transition-all">
                <h3 className="text-2xl font-bold text-[color:var(--color-primary)] mb-4">Interested?</h3>
                <p className="text-slate-600 mb-6">
                  Schedule a visit or connect with the builder today. Our team is available 24/7.
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={handleContactAgent}
                    disabled={authLoading}
                    className="flex-1 py-3 rounded-xl font-semibold text-white bg-[linear-gradient(to_right,#f59e0b,var(--color-accent-gold))] hover:scale-[1.02] active:scale-95 transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Contact Agent
                  </button>
                  <button
                    onClick={toggleShortlist}
                    className="w-14 shrink-0 flex items-center justify-center rounded-xl font-semibold border shadow-sm hover:scale-[1.02] active:scale-95 transition-all bg-white hover:bg-slate-50 border-slate-200"
                    aria-label="Toggle Shortlist"
                  >
                    {isShortlisted ? (
                      <HeartSolid className="h-6 w-6 text-rose-500 hover:text-rose-600 transition-colors" />
                    ) : (
                      <HeartOutline className="h-6 w-6 text-slate-400 hover:text-rose-400 transition-colors" />
                    )}
                  </button>
                </div>
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

      <PropertyBookingChat
        propertyId={property._id}
        propertyName={property.title}
        isAuthenticated={isAuthenticated}
        authLoading={authLoading}
        open={bookingChatOpen}
        onOpenChange={setBookingChatOpen}
      />

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
              amenities={property.nearby_amenities}
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
