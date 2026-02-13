'use client'

import React, { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { api } from '@/lib/api-client'
import {
  MagnifyingGlassIcon,
  MapPinIcon,
  HomeIcon,
  FunnelIcon,
  SparklesIcon,
  HomeModernIcon,
  BanknotesIcon,
} from '@heroicons/react/24/outline'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select'
import { Sheet, SheetTrigger, SheetContent } from '@/components/ui/sheet'

interface Property {
  _id: string
  title: string
  price: number
  city: string
  bedrooms: number
  bathrooms: number
  area_sqft: number
  images?: string[]
  property_type: string
}

export default function BuyerPage() {
  const { user, loading, isAuthenticated, userId } = useCurrentUser()
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState('')
  const [priceRange, setPriceRange] = useState([0, 50000000])
  const [selectedCity, setSelectedCity] = useState<string | null>(null)
  const [selectedType, setSelectedType] = useState<string | null>(null)
  const [properties, setProperties] = useState<Property[]>([])
  const [loadingProperties, setLoadingProperties] = useState(false)
  const dbUserId = (user as any)?._id || userId || null
  const propertiesContainerRef = useRef<HTMLDivElement>(null)
  const hasLoadedRef = useRef(false)

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      router.push(`/chat?q=${encodeURIComponent(searchQuery)}`)
    }
  }

  // Lazy load recommended properties when component is visible
  useEffect(() => {
    // Always allow loading for unauthenticated users (they see popular properties)
    if (loading || hasLoadedRef.current) {
      return
    }

    const loadRecommendations = async () => {
      if (loadingProperties || hasLoadedRef.current) {
        return // Already loading or loaded
      }

      hasLoadedRef.current = true
      setLoadingProperties(true)
      
      try {
        // Load popular properties first (fast)
        const popularResponse = (await api.recommendations.properties('', 12)) as any
        if (popularResponse?.properties) {
          setProperties(popularResponse.properties)
          setLoadingProperties(false)
        }

        // Then, if user is logged in, load personalized recommendations in background
        if (dbUserId) {
          try {
            const response = (await api.recommendations.properties(dbUserId, 12)) as any
            if (response?.properties && response.source === 'recent_searches') {
              // Update with personalized recommendations
              setProperties(response.properties)
            }
          } catch (error: any) {
            console.error('Error loading personalized recommendations:', error)
            // Keep popular properties on error
          }
        }
      } catch (error: any) {
        console.error('Error loading recommendations:', error)
        setLoadingProperties(false)
        hasLoadedRef.current = false // Allow retry on error
      }
    }

    // Use Intersection Observer for lazy loading
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !hasLoadedRef.current) {
            // Start loading when the properties section becomes visible
            loadRecommendations()
          }
        })
      },
      {
        rootMargin: '200px', // Start loading 200px before the section is visible
        threshold: 0.1,
      }
    )

    // Observe the properties container element using ref
    const container = propertiesContainerRef.current
    if (container) {
      observer.observe(container)
    }

    // Fallback: Load after a short delay if Intersection Observer is not supported
    const fallbackTimer = setTimeout(() => {
      if (!hasLoadedRef.current) {
        loadRecommendations()
      }
    }, 1000)

    return () => {
      if (container) {
        observer.unobserve(container)
      }
      clearTimeout(fallbackTimer)
    }
  }, [dbUserId, isAuthenticated, loading])

  const filteredProperties = properties.filter((property) => {
    const matchesCity = selectedCity ? property.city === selectedCity : true
    const matchesType = selectedType ? property.property_type === selectedType : true
    const matchesPrice = property.price >= priceRange[0] && property.price <= priceRange[1]
    const matchesSearch = property.title.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesCity && matchesType && matchesPrice && matchesSearch
  })

  const formatPrice = (price: number) =>
    new Intl.NumberFormat('en-PK', {
      style: 'currency',
      currency: 'PKR',
      minimumFractionDigits: 0,
    }).format(price)

  const openPropertyModal = (property: Property) => {
    // Navigate to property details page
    router.push(`/properties/${property._id}`)
  }

  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--background)]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-[color:var(--color-primary)]"></div>
      </div>
    )

  return (
    <div
      className="min-h-screen"
      style={{
        background: 'linear-gradient(to bottom right, var(--background), #f8f6f3)',
      }}
    >
      {/* Hero Section with AI Search */}
      <section className="border-b border-slate-200/50 bg-white/70 backdrop-blur-md py-16 text-center">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-[color:var(--foreground)] mb-4">
          Discover Your Next Home
        </h1>
        <p className="text-slate-600 mb-6">
          Use AI to find homes that perfectly match your preferences.
        </p>

        <form
          onSubmit={handleSearch}
          className="flex justify-center flex-col sm:flex-row gap-3 px-6"
        >
          <div className="relative w-full sm:w-96">
            <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
            <Input
              placeholder='Try "Homes under 50 lakhs in Islamabad"...'
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-12 rounded-xl bg-white/70 border border-slate-300"
              />
            </div>
          <Button
              type="submit"
            className="rounded-xl px-6 py-3 text-sm font-semibold bg-[linear-gradient(to_right,var(--color-primary),var(--color-accent-gold))] text-white shadow-md hover:shadow-lg transition-all"
            >
            <SparklesIcon className="h-5 w-5 mr-1" />
            AI Search
          </Button>
          </form>
      </section>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-12 grid md:grid-cols-[280px_1fr] gap-8">
        {/* Sidebar Filters */}
        <aside className="hidden md:block sticky top-24 h-fit bg-white/70 backdrop-blur-md p-6 rounded-2xl border border-slate-200/70 shadow-sm">
          <h3 className="text-lg font-semibold mb-4 text-[color:var(--foreground)]">Filters</h3>

          <div className="space-y-6">
            {/* City Filter */}
            <div>
              <label className="text-sm font-medium text-slate-700">City</label>
              <Select onValueChange={setSelectedCity}>
                <SelectTrigger className="w-full mt-2 bg-white/60 rounded-lg">
                  <SelectValue placeholder="Select city" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Lahore">Lahore</SelectItem>
                  <SelectItem value="Karachi">Karachi</SelectItem>
                  <SelectItem value="Islamabad">Islamabad</SelectItem>
                </SelectContent>
              </Select>
      </div>

            {/* Property Type */}
            <div>
              <label className="text-sm font-medium text-slate-700">Property Type</label>
              <Select onValueChange={setSelectedType}>
                <SelectTrigger className="w-full mt-2 bg-white/60 rounded-lg">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Villa">Villa</SelectItem>
                  <SelectItem value="Apartment">Apartment</SelectItem>
                  <SelectItem value="House">House</SelectItem>
                </SelectContent>
              </Select>
        </div>

            {/* Price Range */}
            <div>
              <label className="text-sm font-medium text-slate-700 mb-2 block">Price Range</label>
              <Slider
                min={0}
                max={50000000}
                step={5000000}
                value={priceRange}
                onValueChange={setPriceRange}
              />
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>{formatPrice(priceRange[0])}</span>
                <span>{formatPrice(priceRange[1])}</span>
              </div>
              </div>
              
            <Button
              onClick={() => {
                setSelectedCity(null)
                setSelectedType(null)
                setPriceRange([0, 50000000])
                setSearchQuery('')
              }}
              className="w-full mt-4 rounded-xl bg-[color:var(--color-primary)] text-white hover:bg-[color:var(--color-accent-gold)] transition"
            >
              Reset Filters
            </Button>
          </div>
        </aside>
                
        {/* Mobile Filter Sheet */}
        <div className="md:hidden flex justify-end mb-4">
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline" className="flex items-center gap-2 border-slate-300">
                <FunnelIcon className="h-5 w-5" />
                Filters
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="p-6">
              <h3 className="text-lg font-semibold mb-4 text-[color:var(--foreground)]">Filters</h3>
              {/* ...same filter content as sidebar (reuse here if needed)... */}
            </SheetContent>
          </Sheet>
                </div>
                
        {/* Property Cards */}
        <div ref={propertiesContainerRef}>
        {loadingProperties ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, idx) => (
              <div
                key={idx}
                className="bg-white rounded-xl shadow-sm border border-slate-200/50 overflow-hidden animate-pulse"
              >
                {/* Image Skeleton */}
                <div className="h-40 bg-gradient-to-br from-slate-200 to-slate-300"></div>
                
                {/* Content Skeleton */}
                <div className="p-4 space-y-3">
                  {/* Title Skeleton */}
                  <div className="h-4 bg-slate-200 rounded w-3/4"></div>
                  <div className="h-4 bg-slate-200 rounded w-1/2"></div>
                  
                  {/* Price Skeleton */}
                  <div className="h-6 bg-slate-200 rounded w-1/3"></div>
                  
                  {/* Location Skeleton */}
                  <div className="h-4 bg-slate-200 rounded w-1/4"></div>
                  
                  {/* Stats Skeleton */}
                  <div className="flex items-center justify-between bg-slate-50 rounded-lg p-2">
                    <div className="h-3 bg-slate-200 rounded w-16"></div>
                    <div className="h-3 bg-slate-200 rounded w-16"></div>
                    <div className="h-3 bg-slate-200 rounded w-16"></div>
                  </div>
                  
                  {/* Buttons Skeleton */}
                  <div className="flex space-x-2 pt-3">
                    <div className="h-9 bg-slate-200 rounded flex-1"></div>
                    <div className="h-9 bg-slate-200 rounded flex-1"></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : filteredProperties.length === 0 ? (
          <div className="text-center py-12">
            <HomeIcon className="h-16 w-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-700 mb-2">No properties found</h3>
            <p className="text-slate-500 mb-4">
              {searchQuery || selectedCity || selectedType
                ? 'Try adjusting your filters or search query.'
                : dbUserId
                ? "We couldn't find any recommendations. Start searching to get personalized recommendations!"
                : 'Sign in to see personalized property recommendations based on your search history.'}
            </p>
            {!searchQuery && !selectedCity && !selectedType && (
              <Button
                onClick={() => router.push('/chat')}
                className="rounded-xl px-6 py-3 text-sm font-semibold bg-[linear-gradient(to_right,var(--color-primary),var(--color-accent-gold))] text-white"
              >
                <SparklesIcon className="h-5 w-5 mr-1" />
                Start Searching
              </Button>
            )}
          </div>
        ) : (
          <motion.div layout className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredProperties.map((property, idx) => (
              <motion.div
                key={property._id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1 }}
                viewport={{ once: true }}
              >
                <div
                  className="bg-white rounded-xl shadow-sm border border-slate-200/50 overflow-hidden hover:shadow-lg hover:border-slate-300 transition-all duration-300 cursor-pointer flex flex-col h-full group"
                  onClick={() => openPropertyModal(property)}
                >
                  {/* Property Image */}
                  <div className="h-40 bg-gradient-to-br from-slate-200 to-slate-300 flex items-center justify-center overflow-hidden flex-shrink-0 relative">
                    {property.images && property.images.length > 0 ? (
                      <img
                        src={property.images[0] || '/placeholder.svg'}
                        alt={property.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        onError={(e) => {
                          const target = e.currentTarget as HTMLElement
                          target.style.display = 'none'
                          const nextSibling = target.nextElementSibling as HTMLElement
                          if (nextSibling) {
                            nextSibling.style.display = 'flex'
                          }
                        }}
                      />
                    ) : null}
                    <div
                      className={`h-full w-full flex items-center justify-center ${property.images && property.images.length > 0 ? 'hidden' : 'flex'}`}
                    >
                      <HomeModernIcon className="h-12 w-12 text-slate-400" />
                    </div>
                  </div>

                  {/* Property Details */}
                  <div className="p-4 flex flex-col flex-grow">
                    <h3 className="font-semibold font-serif text-base text-slate-900 mb-2 line-clamp-2">
                      {property.title}
                    </h3>

                    {/* Price */}
                    <div className="flex items-center mb-3">
                      <BanknotesIcon className="h-4 w-4 text-teal-600 mr-2" />
                      <span className="text-lg font-bold text-teal-600">
                        Rs {property.price.toLocaleString()}
                      </span>
                    </div>

                    {/* Location */}
                    <div className="flex items-center mb-3">
                      <MapPinIcon className="h-4 w-4 text-slate-500 mr-2" />
                      <span className="text-sm text-slate-600">
                        {property.city}
                      </span>
                    </div>

                    {/* Property Stats */}
                    <div className="flex items-center justify-between mb-3 text-xs text-slate-600 bg-slate-50 rounded-lg p-2">
                      <span>{property.bedrooms} bed</span>
                      <span className="text-slate-300">•</span>
                      <span>{property.bathrooms} bath</span>
                      <span className="text-slate-300">•</span>
                      <span>{property.area_sqft} sqft</span>
                    </div>

                    {/* Property Type */}
                    <div className="flex items-center justify-between mb-3 text-xs">
                      <span className="text-slate-500">
                        {property.property_type}
                      </span>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex space-x-2 mt-auto pt-3">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          openPropertyModal(property)
                        }}
                        className="flex-1 bg-gradient-to-r from-teal-500 to-cyan-600 text-white py-2 px-3 rounded-lg text-sm font-medium hover:shadow-md transition-all"
                      >
                        View Details
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          router.push(`/chat?q=${encodeURIComponent(`Tell me more about property ${property.title} in ${property.city}`)}`)
                        }}
                        className="flex-1 border border-slate-300 text-slate-700 py-2 px-3 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
                      >
                        Ask AI
                      </button>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
        </div>
      </div>
    </div>
  )
}
