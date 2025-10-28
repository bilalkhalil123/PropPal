'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { UserButton } from '@clerk/nextjs'
import Link from 'next/link'
import { MagnifyingGlassIcon, MapPinIcon, CurrencyDollarIcon, HomeIcon } from '@heroicons/react/24/outline'
import RoleDropdown from '@/components/RoleDropdown'

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
  const [searchQuery, setSearchQuery] = useState('')
  const [currentRole, setCurrentRole] = useState<'buyer' | 'seller' | 'builder'>('buyer')

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/sign-in')
    }
  }, [loading, isAuthenticated, router])

  // Show loading while user data is being fetched
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  // Sample properties for display
  const sampleProperties: Property[] = [
    {
      _id: '1',
      title: 'Modern Villa in DHA Phase 5',
      price: 45000000,
      city: 'Lahore',
      bedrooms: 4,
      bathrooms: 3,
      area_sqft: 2500,
      property_type: 'Villa',
      images: ['/hero-house.svg']
    },
    {
      _id: '2',
      title: 'Luxury Apartment in Clifton',
      price: 25000000,
      city: 'Karachi',
      bedrooms: 3,
      bathrooms: 2,
      area_sqft: 1800,
      property_type: 'Apartment',
      images: ['/hero-house.svg']
    },
    {
      _id: '3',
      title: 'Spacious House in F-8',
      price: 35000000,
      city: 'Islamabad',
      bedrooms: 5,
      bathrooms: 4,
      area_sqft: 3000,
      property_type: 'House',
      images: ['/hero-house.svg']
    },
    {
      _id: '4',
      title: 'Cozy Home in Gulberg',
      price: 18000000,
      city: 'Lahore',
      bedrooms: 2,
      bathrooms: 2,
      area_sqft: 1200,
      property_type: 'House',
      images: ['/hero-house.svg']
    },
    {
      _id: '5',
      title: 'Penthouse in Defence',
      price: 65000000,
      city: 'Karachi',
      bedrooms: 6,
      bathrooms: 5,
      area_sqft: 4000,
      property_type: 'Penthouse',
      images: ['/hero-house.svg']
    },
    {
      _id: '6',
      title: 'Family Home in Blue Area',
      price: 28000000,
      city: 'Islamabad',
      bedrooms: 4,
      bathrooms: 3,
      area_sqft: 2200,
      property_type: 'House',
      images: ['/hero-house.svg']
    }
  ]

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      // Navigate to chat with search query
      router.push(`/chat?q=${encodeURIComponent(searchQuery)}`)
    }
  }

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-PK', {
      style: 'currency',
      currency: 'PKR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(price)
  }

  return (
    <div className="min-h-screen bg-gray-50">

      {/* Search Section */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">Find Your Dream Property</h1>
          <form onSubmit={handleSearch} className="flex space-x-3">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search for properties... (e.g., 'Find houses in Lahore', '3 bedroom apartment in Karachi')"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors text-gray-900 placeholder:text-gray-400"
              />
            </div>
            <button
              type="submit"
              className="bg-blue-600 text-white px-8 py-3 rounded-xl font-semibold hover:bg-blue-700 transition-colors shadow-lg hover:shadow-xl"
            >
              Search with AI
            </button>
          </form>
          <p className="text-sm text-gray-500 mt-2">
            💡 Try natural language queries like "Find houses under 50 lakhs" or "Show me apartments in Islamabad"
          </p>
        </div>
      </div>

      {/* Featured Properties */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Featured Properties</h2>
          <p className="text-gray-600">Discover amazing properties across Pakistan</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sampleProperties.map((property) => (
            <div key={property._id} className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow">
              {/* Property Image */}
              <div className="h-48 bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center">
                <HomeIcon className="h-16 w-16 text-white opacity-80" />
              </div>
              
              {/* Property Details */}
              <div className="p-4">
                <h3 className="font-semibold text-lg text-gray-900 mb-2">{property.title}</h3>
                
                {/* Price */}
                <div className="flex items-center mb-2">
                  <CurrencyDollarIcon className="h-4 w-4 text-green-600 mr-1" />
                  <span className="text-lg font-bold text-green-600">{formatPrice(property.price)}</span>
                </div>
                
                {/* Location */}
                <div className="flex items-center mb-3">
                  <MapPinIcon className="h-4 w-4 text-gray-500 mr-1" />
                  <span className="text-sm text-gray-600">{property.city}</span>
                </div>
                
                {/* Property Details */}
                <div className="flex items-center justify-between text-sm text-gray-600 mb-3">
                  <span>{property.bedrooms} beds</span>
                  <span>{property.bathrooms} baths</span>
                  <span>{property.area_sqft} sqft</span>
                </div>
                
                {/* Property Type */}
                <div className="flex items-center justify-between">
                  <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-medium">
                    {property.property_type}
                  </span>
                  <button className="text-blue-600 hover:text-blue-800 font-medium text-sm">
                    View Details
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-blue-600 text-white py-12">
        <div className="max-w-4xl mx-auto text-center px-4">
          <h2 className="text-3xl font-bold mb-4">Can't Find What You're Looking For?</h2>
          <p className="text-xl text-blue-100 mb-6">
            Use our AI-powered search to find exactly what you need
          </p>
          <button
            onClick={() => router.push('/chat')}
            className="bg-white text-blue-600 px-8 py-3 rounded-xl font-semibold hover:bg-gray-100 transition-colors shadow-lg hover:shadow-xl"
          >
            Try AI Search
          </button>
        </div>
      </div>
    </div>
  )
}

