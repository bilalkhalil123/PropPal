'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { UserButton } from '@clerk/nextjs'
import Link from 'next/link'
import { HomeIcon, MagnifyingGlassIcon, WrenchScrewdriverIcon, PlusIcon, ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline'
import RoleDropdown from '@/components/RoleDropdown'

interface BuilderProfile {
  _id: string
  company_name: string
  specialization: string[]
  experience_years: number
  rating?: number
  location: {
    city: string
    latitude: number
    longitude: number
  }
  about?: string
  founded_year?: number
  portfolio_images?: string[]
}

interface BuilderService {
  _id: string
  name: string
  description: string
  category: string
  price_range?: string
  availability: boolean
}

export default function BuilderPage() {
  const { user, loading, isAuthenticated } = useCurrentUser()
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState('')
  const [currentRole, setCurrentRole] = useState<'buyer' | 'seller' | 'builder'>('builder')

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
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  // Dummy data - in real app, this would come from API
  const [builderProfile, setBuilderProfile] = useState<BuilderProfile | null>({
    _id: 'builder_123',
    company_name: 'Elite Construction Co.',
    specialization: ['Residential Construction', 'Commercial Projects', 'Renovation'],
    experience_years: 15,
    rating: 4.8,
    location: {
      city: 'Lahore',
      latitude: 31.5204,
      longitude: 74.3587
    },
    about: 'We are a leading construction company with over 15 years of experience in delivering high-quality residential and commercial projects across Pakistan.',
    founded_year: 2008,
    portfolio_images: ['/hero-house.svg', '/hero-house.svg', '/hero-house.svg']
  })

  const [builderServices, setBuilderServices] = useState<BuilderService[]>([
    {
      _id: 'service_1',
      name: 'Home Construction',
      description: 'Complete home construction from foundation to finishing',
      category: 'Construction',
      price_range: 'Rs 2,000 - 3,000 per sqft',
      availability: true
    },
    {
      _id: 'service_2',
      name: 'Roof Repair',
      description: 'Professional roof repair and maintenance services',
      category: 'Repair',
      price_range: 'Rs 500 - 1,500 per sqft',
      availability: true
    },
    {
      _id: 'service_3',
      name: 'Interior Design',
      description: 'Modern interior design and decoration services',
      category: 'Design',
      price_range: 'Rs 1,000 - 2,000 per sqft',
      availability: true
    }
  ])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      router.push(`/chat?q=${encodeURIComponent(searchQuery)}`)
    }
  }

  const handleCreateProfile = () => {
    router.push('/chat?q=Create my builder profile')
  }

  const handleManageServices = () => {
    router.push('/chat?q=Manage my services')
  }

  return (
    <div className="min-h-screen bg-gray-50">

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="space-y-6">
          {/* Search Section */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">Builder Dashboard</h1>
            <form onSubmit={handleSearch} className="flex space-x-3">
              <div className="flex-1 relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Ask me anything about your profile or services..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-colors text-gray-900 placeholder:text-gray-400"
                />
              </div>
              <button
                type="submit"
                className="bg-orange-600 text-white px-6 py-3 rounded-xl font-semibold hover:bg-orange-700 transition-colors shadow-lg hover:shadow-xl flex items-center space-x-2"
              >
                <ChatBubbleLeftRightIcon className="h-5 w-5" />
                <span>Chat</span>
              </button>
            </form>
            <p className="text-sm text-gray-500 mt-2">
              💡 Try: "Update my profile", "Add new service", "View my ratings"
            </p>
          </div>

          {/* Profile Section */}
          {builderProfile ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">Your Profile</h2>
                <button
                  onClick={() => router.push('/chat?q=Update my builder profile')}
                  className="bg-orange-100 text-orange-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-200 transition-colors"
                >
                  Edit Profile
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Company Info */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">{builderProfile.company_name}</h3>
                  <div className="space-y-2">
                    <div className="flex items-center">
                      <span className="text-sm text-gray-600 w-24">Experience:</span>
                      <span className="text-sm font-medium text-gray-900">{builderProfile.experience_years} years</span>
                    </div>
                    <div className="flex items-center">
                      <span className="text-sm text-gray-600 w-24">Founded:</span>
                      <span className="text-sm font-medium text-gray-900">{builderProfile.founded_year}</span>
                    </div>
                    <div className="flex items-center">
                      <span className="text-sm text-gray-600 w-24">Location:</span>
                      <span className="text-sm font-medium text-gray-900">{builderProfile.location.city}</span>
                    </div>
                    {builderProfile.rating && (
                      <div className="flex items-center">
                        <span className="text-sm text-gray-600 w-24">Rating:</span>
                        <div className="flex items-center">
                          <span className="text-yellow-500">★</span>
                          <span className="text-sm font-medium text-gray-900 ml-1">{builderProfile.rating}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Specialization */}
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 mb-2">Specialization</h4>
                  <div className="flex flex-wrap gap-2">
                    {builderProfile.specialization.map((spec, index) => (
                      <span key={index} className="bg-orange-100 text-orange-800 px-3 py-1 rounded-full text-sm">
                        {spec}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* About */}
              {builderProfile.about && (
                <div className="mt-4">
                  <h4 className="text-sm font-semibold text-gray-900 mb-2">About</h4>
                  <p className="text-sm text-gray-600">{builderProfile.about}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 text-center">
              <WrenchScrewdriverIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <h2 className="text-xl font-bold text-gray-900 mb-2">No Profile Found</h2>
              <p className="text-gray-600 mb-6">Create your builder profile to start managing your services and connecting with clients.</p>
              <button
                onClick={handleCreateProfile}
                className="bg-orange-600 text-white px-6 py-3 rounded-xl font-semibold hover:bg-orange-700 transition-colors shadow-lg hover:shadow-xl flex items-center space-x-2 mx-auto"
              >
                <PlusIcon className="h-5 w-5" />
                <span>Create Your Profile</span>
              </button>
            </div>
          )}

          {/* Services Section */}
          {builderProfile && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">Your Services</h2>
                <button
                  onClick={handleManageServices}
                  className="bg-orange-100 text-orange-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-200 transition-colors"
                >
                  Manage Services
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {builderServices.map((service) => (
                  <div key={service._id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-semibold text-gray-900">{service.name}</h3>
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        service.availability 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {service.availability ? 'Available' : 'Unavailable'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{service.description}</p>
                    <div className="text-xs text-gray-500">
                      <div>Category: {service.category}</div>
                      {service.price_range && <div>Price: {service.price_range}</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

