'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { UserButton } from '@clerk/nextjs'
import Link from 'next/link'
import { HomeIcon, UserIcon, PlusCircleIcon, MicrophoneIcon, SparklesIcon, EyeIcon } from '@heroicons/react/24/outline'
import { motion } from 'framer-motion'
import RoleDropdown from '@/components/RoleDropdown'

interface Property {
  _id: string
  title: string
  description: string
  price: number
  property_type: string
  city: string
  area: string
  bedrooms: number
  bathrooms: number
  images: string[]
  created_at: string
}

export default function SellerPage() {
  const { user, loading, isAuthenticated, clerkId } = useCurrentUser()
  const router = useRouter()
  const [currentRole, setCurrentRole] = useState<'buyer' | 'seller' | 'builder'>('seller')
  const [properties, setProperties] = useState<Property[]>([])
  const [loadingProperties, setLoadingProperties] = useState(true)
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/sign-in')
    }
  }, [loading, isAuthenticated, router])

  // Fetch user's properties
  useEffect(() => {
    const fetchProperties = async () => {
      if (!clerkId || !API_BASE_URL) return
      
      setLoadingProperties(true)
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/properties?clerk_id=${encodeURIComponent(clerkId)}`
        )
        if (response.ok) {
          const data = await response.json()
          setProperties(data)
        } else {
          console.error('Failed to fetch properties')
        }
      } catch (error) {
        console.error('Error fetching properties:', error)
      } finally {
        setLoadingProperties(false)
      }
    }

    if (isAuthenticated && clerkId) {
      fetchProperties()
    }
  }, [isAuthenticated, clerkId, API_BASE_URL])

  // Show loading while user data is being fetched
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[linear-gradient(to_bottom,rgba(249,249,249,0.85),rgba(237,236,232,0.9))]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[color:var(--color-primary)] mx-auto mb-4"></div>
          <p className="text-[color:var(--color-primary)]">Loading...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="min-h-screen bg-[linear-gradient(to_bottom,rgba(249,249,249,0.85),rgba(237,236,232,0.9))] text-[color:var(--color-primary)]">
      <div className="max-w-7xl mx-auto px-6 md:px-12 lg:px-24 py-12">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2 text-[color:var(--color-primary)]">Seller Dashboard</h1>
          <p className="text-slate-700">Manage your property listings and reach potential buyers</p>
        </div>

        {/* Main Content Card */}
        <div className="bg-white/70 backdrop-blur-xl border border-slate-200 shadow-lg rounded-3xl p-8 md:p-12">
          <div className="text-center mb-8">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.5 }}
              className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-[linear-gradient(to_right,#f59e0b,var(--color-accent-gold))] mb-6"
            >
              <UserIcon className="h-10 w-10 text-white" />
            </motion.div>
            <h2 className="text-3xl font-bold mb-4 text-[color:var(--color-primary)]">Create Your Property Listing</h2>
            <p className="text-lg text-slate-700 max-w-2xl mx-auto mb-8">
              List your properties quickly and easily. Use our AI-powered voice input to describe your property,
              or fill out the form manually. Watch as your listing comes to life in real-time!
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => router.push('/listings/create')}
              className="flex items-center gap-3 px-8 py-4 rounded-xl font-semibold text-white bg-[linear-gradient(to_right,#f59e0b,var(--color-accent-gold))] hover:shadow-xl transition-all shadow-md"
            >
              <PlusCircleIcon className="h-6 w-6" />
              Create New Listing
            </motion.button>
          </div>

          {/* Features Grid */}
          <div className="mt-12 grid md:grid-cols-3 gap-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="p-6 rounded-2xl bg-slate-50 border border-slate-200 hover:shadow-md transition-all"
            >
              <div className="w-12 h-12 rounded-xl bg-[color:var(--color-primary)]/10 flex items-center justify-center mb-4">
                <MicrophoneIcon className="h-6 w-6 text-[color:var(--color-primary)]" />
              </div>
              <h3 className="text-xl font-bold mb-2 text-[color:var(--color-primary)]">Voice Input</h3>
              <p className="text-slate-600 text-sm">
                Describe your property naturally using voice. Our AI will extract all the details automatically.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="p-6 rounded-2xl bg-slate-50 border border-slate-200 hover:shadow-md transition-all"
            >
              <div className="w-12 h-12 rounded-xl bg-[color:var(--color-primary)]/10 flex items-center justify-center mb-4">
                <SparklesIcon className="h-6 w-6 text-[color:var(--color-primary)]" />
              </div>
              <h3 className="text-xl font-bold mb-2 text-[color:var(--color-primary)]">Real-Time Updates</h3>
              <p className="text-slate-600 text-sm">
                Watch as your form fields are filled in real-time as you speak. See progress and missing information instantly.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="p-6 rounded-2xl bg-slate-50 border border-slate-200 hover:shadow-md transition-all"
            >
              <div className="w-12 h-12 rounded-xl bg-[color:var(--color-primary)]/10 flex items-center justify-center mb-4">
                <HomeIcon className="h-6 w-6 text-[color:var(--color-primary)]" />
              </div>
              <h3 className="text-xl font-bold mb-2 text-[color:var(--color-primary)]">Easy Management</h3>
              <p className="text-slate-600 text-sm">
                Create, edit, and manage all your property listings from one convenient dashboard.
              </p>
            </motion.div>
          </div>

          {/* Quick Info */}
          <div className="mt-8 p-6 rounded-xl bg-blue-50 border border-blue-200">
            <p className="text-blue-800 text-sm text-center">
              <strong>💡 Tip:</strong> You can use either voice input or manual form filling, or both together!
              The form supports real-time updates from voice input while you can still edit fields manually.
            </p>
          </div>
        </div>

        {/* My Listings Section */}
        <div className="mt-12 bg-white/70 backdrop-blur-xl border border-slate-200 shadow-lg rounded-3xl p-8 md:p-12">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-3xl font-bold text-[color:var(--color-primary)]">My Listings</h2>
              <p className="text-slate-700 mt-2">View and manage all your property listings</p>
            </div>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => router.push('/listings/create')}
              className="flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white bg-[linear-gradient(to_right,#f59e0b,var(--color-accent-gold))] hover:shadow-xl transition-all shadow-md"
            >
              <PlusCircleIcon className="h-5 w-5" />
              New Listing
            </motion.button>
          </div>

          {loadingProperties ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[color:var(--color-primary)] mx-auto mb-4"></div>
              <p className="text-slate-600">Loading your listings...</p>
            </div>
          ) : properties.length === 0 ? (
            <div className="text-center py-12">
              <HomeIcon className="h-16 w-16 text-slate-400 mx-auto mb-4" />
              <p className="text-xl font-semibold text-slate-700 mb-2">No listings yet</p>
              <p className="text-slate-600 mb-6">Create your first property listing to get started!</p>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => router.push('/listings/create')}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white bg-[linear-gradient(to_right,#f59e0b,var(--color-accent-gold))] hover:shadow-xl transition-all shadow-md"
              >
                <PlusCircleIcon className="h-5 w-5" />
                Create Your First Listing
              </motion.button>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {properties.map((property) => (
                <motion.div
                  key={property._id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-white rounded-2xl border border-slate-200 overflow-hidden hover:shadow-xl transition-all cursor-pointer"
                  onClick={() => router.push(`/properties/${property._id}`)}
                >
                  {/* Image */}
                  <div className="h-48 bg-slate-200 relative overflow-hidden">
                    {property.images && property.images.length > 0 ? (
                      <img
                        src={property.images[0]}
                        alt={property.title}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <HomeIcon className="h-16 w-16 text-slate-400" />
                      </div>
                    )}
                  </div>

                  {/* Content */}
                  <div className="p-6">
                    <h3 className="text-xl font-bold text-[color:var(--color-primary)] mb-2 line-clamp-1">
                      {property.title}
                    </h3>
                    <p className="text-slate-600 text-sm mb-4 line-clamp-2">
                      {property.description}
                    </p>

                    {/* Details */}
                    <div className="flex flex-wrap gap-4 text-sm text-slate-600 mb-4">
                      <span className="flex items-center gap-1">
                        <HomeIcon className="h-4 w-4" />
                        {property.property_type}
                      </span>
                      <span>{property.bedrooms} bed</span>
                      <span>{property.bathrooms} bath</span>
                      <span>{property.city}</span>
                    </div>

                    {/* Price */}
                    <div className="flex items-center justify-between pt-4 border-t border-slate-200">
                      <div>
                        <p className="text-2xl font-bold text-[color:var(--color-primary)]">
                          PKR {property.price.toLocaleString()}
                        </p>
                        <p className="text-xs text-slate-500">{property.area}</p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          router.push(`/properties/${property._id}`)
                        }}
                        className="p-2 rounded-lg bg-[color:var(--color-primary)]/10 text-[color:var(--color-primary)] hover:bg-[color:var(--color-primary)]/20 transition-all"
                      >
                        <EyeIcon className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

