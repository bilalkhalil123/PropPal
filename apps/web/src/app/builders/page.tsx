'use client'

import { useState } from 'react'
import Link from 'next/link'
import { 
  HomeIcon,
  StarIcon,
  MapPinIcon,
  BriefcaseIcon,
  UserIcon,
  PhoneIcon,
  EnvelopeIcon,
  EyeIcon,
  ChatBubbleLeftRightIcon
} from '@heroicons/react/24/outline'

interface Builder {
  id: string
  name: string
  company: string
  specialties: string[]
  experience: number
  location: string
  rating: number
  reviewsCount: number
  completedProjects: number
  phone: string
  email: string
  description: string
  profileImage: string
  portfolio: {
    image: string
    title: string
    type: string
  }[]
  priceRange: {
    min: number
    max: number
  }
  availability: 'available' | 'busy' | 'booked'
}

// Mock builders data
const mockBuilders: Builder[] = [
  {
    id: '1',
    name: 'John Smith',
    company: 'Smith Construction & Design',
    specialties: ['Custom Interior Design', 'Residential Construction', 'Kitchen Remodeling'],
    experience: 12,
    location: 'Lahore, Punjab',
    rating: 4.8,
    reviewsCount: 127,
    completedProjects: 85,
    phone: '+92 300 1234567',
    email: 'john@smithconstruction.com',
    description: 'Experienced builder specializing in high-end residential construction and custom interior design. Committed to delivering exceptional quality and innovative solutions.',
    profileImage: '/builder1.jpg',
    portfolio: [
      { image: '/portfolio1.jpg', title: 'Modern Villa', type: 'Residential' },
      { image: '/portfolio2.jpg', title: 'Luxury Kitchen', type: 'Interior' },
      { image: '/portfolio3.jpg', title: 'Office Complex', type: 'Commercial' }
    ],
    priceRange: { min: 5000000, max: 50000000 },
    availability: 'available'
  },
  {
    id: '2',
    name: 'Sarah Ahmed',
    company: 'Elite Builders',
    specialties: ['Luxury Construction', 'Commercial Buildings', 'Renovation'],
    experience: 15,
    location: 'Islamabad, ICT',
    rating: 4.9,
    reviewsCount: 203,
    completedProjects: 142,
    phone: '+92 301 9876543',
    email: 'sarah@elitebuilders.pk',
    description: 'Award-winning builder with expertise in luxury residential and commercial construction. Known for attention to detail and premium finishes.',
    profileImage: '/builder2.jpg',
    portfolio: [
      { image: '/portfolio4.jpg', title: 'Luxury Apartment', type: 'Residential' },
      { image: '/portfolio5.jpg', title: 'Shopping Mall', type: 'Commercial' },
      { image: '/portfolio6.jpg', title: 'Hotel Renovation', type: 'Renovation' }
    ],
    priceRange: { min: 10000000, max: 100000000 },
    availability: 'available'
  },
  {
    id: '3',
    name: 'Ahmed Hassan',
    company: 'Hassan Constructions',
    specialties: ['Affordable Housing', 'Residential Construction', 'Home Extensions'],
    experience: 8,
    location: 'Karachi, Sindh',
    rating: 4.6,
    reviewsCount: 89,
    completedProjects: 156,
    phone: '+92 333 5555555',
    email: 'ahmed@hassanconstructions.com',
    description: 'Specializing in affordable yet quality housing solutions. Expert in residential construction with focus on cost-effective building methods.',
    profileImage: '/builder3.jpg',
    portfolio: [
      { image: '/portfolio7.jpg', title: 'Family Home', type: 'Residential' },
      { image: '/portfolio8.jpg', title: 'Home Extension', type: 'Extension' },
      { image: '/portfolio9.jpg', title: 'Duplex House', type: 'Residential' }
    ],
    priceRange: { min: 2000000, max: 25000000 },
    availability: 'busy'
  }
]

export default function BrowseBuilders() {
  const [builders] = useState<Builder[]>(mockBuilders)
  const [selectedSpecialty, setSelectedSpecialty] = useState<string>('')
  const [selectedLocation, setSelectedLocation] = useState<string>('')
  const [priceRange, setPriceRange] = useState<string>('')
  const [selectedBuilder, setSelectedBuilder] = useState<Builder | null>(null)

  // Get unique specialties and locations for filters
  const allSpecialties = Array.from(new Set(builders.flatMap(b => b.specialties)))
  const allLocations = Array.from(new Set(builders.map(b => b.location)))

  // Filter builders based on selected criteria
  const filteredBuilders = builders.filter(builder => {
    if (selectedSpecialty && !builder.specialties.includes(selectedSpecialty)) return false
    if (selectedLocation && builder.location !== selectedLocation) return false
    if (priceRange) {
      const [min, max] = priceRange.split('-').map(Number)
      if (builder.priceRange.min > max || builder.priceRange.max < min) return false
    }
    return true
  })

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-PK', {
      style: 'currency',
      currency: 'PKR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  const getAvailabilityColor = (availability: string) => {
    switch (availability) {
      case 'available': return 'bg-green-100 text-green-800'
      case 'busy': return 'bg-yellow-100 text-yellow-800'
      case 'booked': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center space-x-2 text-blue-600 hover:text-blue-700">
              <HomeIcon className="h-8 w-8" />
              <span className="text-2xl font-bold">PropPal</span>
            </Link>
            <nav className="hidden md:flex space-x-8">
              <Link href="/" className="text-gray-600 hover:text-gray-900">Home</Link>
              <Link href="/chat" className="text-gray-600 hover:text-gray-900">AI Chat</Link>
              <Link href="/builders" className="text-blue-600 font-medium">Find Builders</Link>
              <Link href="/builder" className="text-gray-600 hover:text-gray-900">Builder Portal</Link>
            </nav>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Page Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Find Expert Builders</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Connect with experienced builders and contractors for your construction projects. 
            Browse profiles, compare expertise, and hire the perfect builder for your needs.
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Filter Builders</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label htmlFor="specialty" className="block text-sm font-medium text-gray-700 mb-2">
                Specialty
              </label>
              <select
                id="specialty"
                value={selectedSpecialty}
                onChange={(e) => setSelectedSpecialty(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">All Specialties</option>
                {allSpecialties.map(specialty => (
                  <option key={specialty} value={specialty}>{specialty}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="location" className="block text-sm font-medium text-gray-700 mb-2">
                Location
              </label>
              <select
                id="location"
                value={selectedLocation}
                onChange={(e) => setSelectedLocation(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">All Locations</option>
                {allLocations.map(location => (
                  <option key={location} value={location}>{location}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="priceRange" className="block text-sm font-medium text-gray-700 mb-2">
                Budget Range
              </label>
              <select
                id="priceRange"
                value={priceRange}
                onChange={(e) => setPriceRange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Any Budget</option>
                <option value="0-10000000">Under ₹1 Crore</option>
                <option value="10000000-25000000">₹1-2.5 Crore</option>
                <option value="25000000-50000000">₹2.5-5 Crore</option>
                <option value="50000000-999999999">Above ₹5 Crore</option>
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={() => {
                  setSelectedSpecialty('')
                  setSelectedLocation('')
                  setPriceRange('')
                }}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Clear Filters
              </button>
            </div>
          </div>
        </div>

        {/* Results Count */}
        <div className="mb-6">
          <p className="text-gray-600">
            Showing {filteredBuilders.length} of {builders.length} builders
          </p>
        </div>

        {/* Builders Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {filteredBuilders.map((builder) => (
            <div key={builder.id} className="bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow">
              {/* Builder Header */}
              <div className="p-6 border-b border-gray-200">
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="w-16 h-16 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center">
                      <UserIcon className="h-8 w-8 text-white" />
                    </div>
                    <div>
                      <h3 className="text-xl font-semibold text-gray-900">{builder.name}</h3>
                      <p className="text-gray-600">{builder.company}</p>
                      <div className="flex items-center mt-1">
                        <div className="flex items-center">
                          {[...Array(5)].map((_, i) => (
                            <StarIcon
                              key={i}
                              className={`h-4 w-4 ${
                                i < Math.floor(builder.rating)
                                  ? 'text-yellow-400 fill-current'
                                  : 'text-gray-300'
                              }`}
                            />
                          ))}
                        </div>
                        <span className="ml-2 text-sm text-gray-600">
                          {builder.rating} ({builder.reviewsCount} reviews)
                        </span>
                      </div>
                    </div>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${getAvailabilityColor(builder.availability)}`}>
                    {builder.availability.charAt(0).toUpperCase() + builder.availability.slice(1)}
                  </span>
                </div>
              </div>

              {/* Builder Details */}
              <div className="p-6">
                <p className="text-gray-600 mb-4">{builder.description}</p>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">{builder.experience}</div>
                    <div className="text-sm text-gray-600">Years Experience</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">{builder.completedProjects}</div>
                    <div className="text-sm text-gray-600">Projects Done</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-600">{builder.rating}</div>
                    <div className="text-sm text-gray-600">Rating</div>
                  </div>
                </div>

                {/* Location and Price Range */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center">
                    <MapPinIcon className="h-4 w-4 text-gray-500 mr-2" />
                    <span className="text-sm text-gray-600">{builder.location}</span>
                  </div>
                  <div className="text-sm text-gray-600">
                    {formatCurrency(builder.priceRange.min)} - {formatCurrency(builder.priceRange.max)}
                  </div>
                </div>

                {/* Specialties */}
                <div className="mb-6">
                  <div className="flex flex-wrap gap-2">
                    {builder.specialties.map((specialty, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                      >
                        {specialty}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Contact and Action Buttons */}
                <div className="flex items-center justify-between">
                  <div className="flex space-x-4">
                    <a
                      href={`tel:${builder.phone}`}
                      className="flex items-center text-gray-600 hover:text-blue-600 transition-colors"
                    >
                      <PhoneIcon className="h-4 w-4 mr-1" />
                      <span className="text-sm">Call</span>
                    </a>
                    <a
                      href={`mailto:${builder.email}`}
                      className="flex items-center text-gray-600 hover:text-blue-600 transition-colors"
                    >
                      <EnvelopeIcon className="h-4 w-4 mr-1" />
                      <span className="text-sm">Email</span>
                    </a>
                  </div>

                  <div className="flex space-x-2">
                    <button
                      onClick={() => setSelectedBuilder(builder)}
                      className="px-4 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 transition-colors flex items-center"
                    >
                      <EyeIcon className="h-4 w-4 mr-2" />
                      View Profile
                    </button>
                    <Link
                      href={`/builders/${builder.id}/hire`}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center"
                    >
                      <ChatBubbleLeftRightIcon className="h-4 w-4 mr-2" />
                      Hire Builder
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* No Results */}
        {filteredBuilders.length === 0 && (
          <div className="text-center py-12">
            <BriefcaseIcon className="h-24 w-24 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-medium text-gray-900 mb-2">No builders found</h3>
            <p className="text-gray-600 mb-4">Try adjusting your filters to see more results</p>
            <button
              onClick={() => {
                setSelectedSpecialty('')
                setSelectedLocation('')
                setPriceRange('')
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Clear All Filters
            </button>
          </div>
        )}
      </div>

      {/* Builder Profile Modal */}
      {selectedBuilder && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-900">Builder Profile</h2>
                <button
                  onClick={() => setSelectedBuilder(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            
            <div className="p-6">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Builder Info */}
                <div className="lg:col-span-1">
                  <div className="text-center mb-6">
                    <div className="w-24 h-24 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                      <UserIcon className="h-12 w-12 text-white" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900">{selectedBuilder.name}</h3>
                    <p className="text-gray-600">{selectedBuilder.company}</p>
                    <div className="flex items-center justify-center mt-2">
                      <div className="flex items-center">
                        {[...Array(5)].map((_, i) => (
                          <StarIcon
                            key={i}
                            className={`h-4 w-4 ${
                              i < Math.floor(selectedBuilder.rating)
                                ? 'text-yellow-400 fill-current'
                                : 'text-gray-300'
                            }`}
                          />
                        ))}
                      </div>
                      <span className="ml-2 text-sm text-gray-600">
                        {selectedBuilder.rating} ({selectedBuilder.reviewsCount} reviews)
                      </span>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <h4 className="font-semibold text-gray-900 mb-2">Contact</h4>
                      <div className="space-y-2">
                        <div className="flex items-center">
                          <PhoneIcon className="h-4 w-4 text-gray-500 mr-2" />
                          <span className="text-sm text-gray-600">{selectedBuilder.phone}</span>
                        </div>
                        <div className="flex items-center">
                          <EnvelopeIcon className="h-4 w-4 text-gray-500 mr-2" />
                          <span className="text-sm text-gray-600">{selectedBuilder.email}</span>
                        </div>
                        <div className="flex items-center">
                          <MapPinIcon className="h-4 w-4 text-gray-500 mr-2" />
                          <span className="text-sm text-gray-600">{selectedBuilder.location}</span>
                        </div>
                      </div>
                    </div>

                    <div>
                      <h4 className="font-semibold text-gray-900 mb-2">Specialties</h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedBuilder.specialties.map((specialty, index) => (
                          <span
                            key={index}
                            className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs"
                          >
                            {specialty}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Portfolio and Details */}
                <div className="lg:col-span-2">
                  <div className="space-y-6">
                    <div>
                      <h4 className="font-semibold text-gray-900 mb-2">About</h4>
                      <p className="text-gray-600">{selectedBuilder.description}</p>
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                      <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="text-2xl font-bold text-blue-600">{selectedBuilder.experience}</div>
                        <div className="text-sm text-gray-600">Years Experience</div>
                      </div>
                      <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="text-2xl font-bold text-green-600">{selectedBuilder.completedProjects}</div>
                        <div className="text-sm text-gray-600">Projects Completed</div>
                      </div>
                      <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="text-2xl font-bold text-purple-600">{selectedBuilder.rating}</div>
                        <div className="text-sm text-gray-600">Average Rating</div>
                      </div>
                    </div>

                    <div>
                      <h4 className="font-semibold text-gray-900 mb-4">Portfolio</h4>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {selectedBuilder.portfolio.map((item, index) => (
                          <div key={index} className="bg-gray-100 rounded-lg p-4">
                            <div className="h-32 bg-gradient-to-br from-gray-300 to-gray-400 rounded-lg mb-3 flex items-center justify-center">
                              <BriefcaseIcon className="h-8 w-8 text-gray-600" />
                            </div>
                            <h5 className="font-medium text-gray-900">{item.title}</h5>
                            <p className="text-sm text-gray-600">{item.type}</p>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="flex space-x-4">
                      <Link
                        href={`/builders/${selectedBuilder.id}/hire`}
                        className="flex-1 bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 transition-colors text-center"
                      >
                        Hire This Builder
                      </Link>
                      <button
                        onClick={() => setSelectedBuilder(null)}
                        className="flex-1 border border-gray-300 text-gray-700 py-3 px-4 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        Close
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

