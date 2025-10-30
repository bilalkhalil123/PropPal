"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useCurrentUser } from "@/hooks/useCurrentUser"
import Link from "next/link"
import { MagnifyingGlassIcon, MapPinIcon, BanknotesIcon, HomeIcon, SparklesIcon } from "@heroicons/react/24/outline"
import Button from "@/components/ui/Button"

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
  score?: number
}

export default function BuyerPage() {
  const { user, loading, isAuthenticated } = useCurrentUser()
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState("")

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push("/sign-in")
    }
  }, [loading, isAuthenticated, router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  const sampleProperties: Property[] = [
    {
      _id: "1",
      title: "Modern Villa in DHA Phase 5",
      price: 45000000,
      city: "Lahore",
      bedrooms: 4,
      bathrooms: 3,
      area_sqft: 2500,
      property_type: "Villa",
      images: ["/hero-house.svg"],
    },
    {
      _id: "2",
      title: "Luxury Apartment in Clifton",
      price: 25000000,
      city: "Karachi",
      bedrooms: 3,
      bathrooms: 2,
      area_sqft: 1800,
      property_type: "Apartment",
      images: ["/hero-house.svg"],
    },
    {
      _id: "3",
      title: "Spacious House in F-8",
      price: 35000000,
      city: "Islamabad",
      bedrooms: 5,
      bathrooms: 4,
      area_sqft: 3000,
      property_type: "House",
      images: ["/hero-house.svg"],
    },
    {
      _id: "4",
      title: "Cozy Home in Gulberg",
      price: 18000000,
      city: "Lahore",
      bedrooms: 2,
      bathrooms: 2,
      area_sqft: 1200,
      property_type: "House",
      images: ["/hero-house.svg"],
    },
    {
      _id: "5",
      title: "Penthouse in Defence",
      price: 65000000,
      city: "Karachi",
      bedrooms: 6,
      bathrooms: 5,
      area_sqft: 4000,
      property_type: "Penthouse",
      images: ["/hero-house.svg"],
    },
    {
      _id: "6",
      title: "Family Home in Blue Area",
      price: 28000000,
      city: "Islamabad",
      bedrooms: 4,
      bathrooms: 3,
      area_sqft: 2200,
      property_type: "House",
      images: ["/hero-house.svg"],
    },
  ]

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      router.push(`/chat?q=${encodeURIComponent(searchQuery)}`)
    }
  }

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat("en-PK", {
      style: "currency",
      currency: "PKR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(price)
  }

  return (
    <div className="min-h-screen" style={{ background: "radial-gradient(1200px 600px at 10% -10%, rgba(224,164,88,0.06), transparent 60%), radial-gradient(800px 400px at 90% 10%, rgba(13,27,42,0.05), transparent 60%), var(--background)" }}>
      {/* Search Section */}
      <div className="bg-white/70 backdrop-blur border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-6 py-10">
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-slate-900 mb-2">Find Your Dream Property</h1>
            <p className="text-lg text-slate-600">Explore thousands of properties across Pakistan</p>
          </div>
          <form onSubmit={handleSearch} className="flex gap-3">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
              <input
                type="text"
                placeholder="Search for properties... (e.g., 'Find houses in Lahore')"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-12 pr-4 py-3.5 border border-slate-300 rounded-xl focus:ring-2 focus:ring-[color:var(--color-gold)] focus:border-transparent transition-all text-slate-900 placeholder:text-slate-400 bg-white"
              />
            </div>
            <Button type="submit" className="flex items-center gap-2">
              <SparklesIcon className="h-5 w-5" />
              Search
            </Button>
          </form>
          <p className="text-sm text-slate-500 mt-3">
            💡 Try natural language queries like "Find houses under 50 lakhs" or "Show me apartments in Islamabad"
          </p>
        </div>
      </div>

      {/* Featured Properties */}
      <div className="max-w-6xl mx-auto px-6 py-16">
        <div className="mb-12">
          <h2 className="text-3xl font-bold text-slate-900 mb-2">Featured Properties</h2>
          <p className="text-slate-600">Discover amazing properties across Pakistan</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sampleProperties.map((property) => (
            <div
              key={property._id}
              className="group rounded-2xl overflow-hidden"
            >
              {/* Property Image */}
              <div className="h-48 flex items-center justify-center overflow-hidden group-hover:scale-105 transition-transform duration-300" style={{ backgroundImage: "linear-gradient(135deg, var(--color-primary), var(--color-accent))" }}>
                <HomeIcon className="h-16 w-16 text-white opacity-60" />
              </div>

              {/* Property Details */}
              <div className="p-5">
                <h3 className="font-semibold text-lg text-slate-900 mb-3 line-clamp-2 group-hover:text-teal-600 transition-colors">
                  {property.title}
                </h3>

                {/* Price */}
                <div className="flex items-center mb-3">
                  <BanknotesIcon className="h-5 w-5 text-[color:var(--color-gold)] mr-2" />
                  <span className="text-lg font-bold text-[color:var(--color-gold)]">{formatPrice(property.price)}</span>
                </div>

                {/* Location */}
                <div className="flex items-center mb-4">
                  <MapPinIcon className="h-4 w-4 text-slate-500 mr-2" />
                  <span className="text-sm text-slate-600">{property.city}</span>
                </div>

                {/* Property Details */}
                <div className="flex items-center justify-between text-sm text-slate-600 mb-4 pb-4 border-b border-slate-200">
                  <span className="font-medium">{property.bedrooms} beds</span>
                  <span className="font-medium">{property.bathrooms} baths</span>
                  <span className="font-medium">{property.area_sqft} sqft</span>
                </div>

                {/* Property Type & Action */}
                <div className="flex items-center justify-between">
                  <span className="px-3 py-1 rounded-full text-xs font-semibold" style={{ backgroundColor: "rgba(224,164,88,0.12)", color: "var(--color-gold)" }}>
                    {property.property_type}
                  </span>
                  <Button href={`/properties/${property._id}`} variant="ghost" className="font-semibold text-sm">
                    View →
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-gradient-to-r from-teal-600 to-cyan-600 text-white py-16">
        <div className="max-w-4xl mx-auto text-center px-6">
          <h2 className="text-3xl font-bold mb-4">Can't Find What You're Looking For?</h2>
          <p className="text-lg text-teal-100 mb-8">Use our AI-powered search to find exactly what you need</p>
          <button
            onClick={() => router.push("/chat")}
            className="bg-white text-teal-600 px-8 py-3 rounded-xl font-semibold hover:bg-slate-50 transition-colors shadow-lg hover:shadow-xl"
          >
            Try AI Search
          </button>
        </div>
      </div>
    </div>
  )
}

