'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { UserButton } from '@clerk/nextjs'
import Link from 'next/link'
import { HomeIcon, UserIcon, PlusCircleIcon, MicrophoneIcon, SparklesIcon, EyeIcon, EllipsisVerticalIcon, TrashIcon } from '@heroicons/react/24/outline'
import { motion } from 'framer-motion'
import RoleDropdown from '@/components/RoleDropdown'
import AuthRequired from '@/components/AuthRequired'

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
  const { user, loading, isAuthenticated, clerkId, isGuest } = useCurrentUser()
  const router = useRouter()
  const [currentRole, setCurrentRole] = useState<'buyer' | 'seller' | 'builder'>('seller')
  const [properties, setProperties] = useState<Property[]>([])
  const [loadingProperties, setLoadingProperties] = useState(true)
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL

  useEffect(() => {
    if (!loading && !isAuthenticated && !isGuest) {
      router.push('/sign-in')
    }
  }, [loading, isAuthenticated, isGuest, router])

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

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      if (menuOpenId && !target.closest('[data-menu-container]')) {
        setMenuOpenId(null)
      }
    }

    if (menuOpenId) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => {
        document.removeEventListener('mousedown', handleClickOutside)
      }
    }
  }, [menuOpenId])

  const handleDelete = async (propertyId: string) => {
    if (!API_BASE_URL || !clerkId) return
    const confirmed = window.confirm('Delete this property? This cannot be undone.')
    if (!confirmed) return
    setDeletingId(propertyId)
    try {
      const res = await fetch(`${API_BASE_URL}/api/properties/${propertyId}?clerk_id=${encodeURIComponent(clerkId)}`, {
        method: 'DELETE',
      })
      if (!res.ok) {
        console.error('Failed to delete property')
        return
      }
      setProperties((prev) => prev.filter((p) => p._id !== propertyId))
    } catch (err) {
      console.error('Error deleting property:', err)
    } finally {
      setDeletingId(null)
      setMenuOpenId(null)
    }
  }

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

  if (isGuest) {
    return (
      <div className="min-h-screen bg-slate-50 py-12">
        <AuthRequired 
          title="Seller Dashboard" 
          description="Sign in as a seller to list your properties, manage inquiries, and track your listing performance."
          role="seller"
        />
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
                  className="group relative bg-white rounded-2xl border border-slate-200 overflow-hidden hover:shadow-xl transition-all cursor-pointer flex flex-col h-full"
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
                    <div className="absolute top-3 left-3 px-3 py-1 rounded-full text-xs font-semibold bg-white/90 text-slate-700 border border-white/60">
                      {property.city || '—'}
                    </div>
                    <div className="absolute top-3 right-3 z-10" data-menu-container>
                      <button
                        className="p-1.5 rounded-lg bg-white/95 backdrop-blur-sm text-slate-600 shadow-md border border-slate-200 hover:bg-white hover:shadow-lg transition-all"
                        onClick={(e) => {
                          e.stopPropagation()
                          setMenuOpenId(menuOpenId === property._id ? null : property._id)
                        }}
                        aria-label="Actions"
                      >
                        <EllipsisVerticalIcon className="h-5 w-5" />
                      </button>
                      {menuOpenId === property._id && (
                        <div
                          className="absolute right-0 mt-1 w-44 rounded-xl bg-white shadow-xl border border-slate-200 py-1.5 overflow-hidden"
                          onClick={(e) => e.stopPropagation()}
                          data-menu-container
                        >
                          <button
                            className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            onClick={() => {
                              handleDelete(property._id)
                              setMenuOpenId(null)
                            }}
                            disabled={deletingId === property._id}
                          >
                            <TrashIcon className="h-4 w-4 flex-shrink-0" />
                            <span>{deletingId === property._id ? 'Deleting...' : 'Delete Property'}</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Content */}
                  <div className="p-6 flex-1 flex flex-col gap-3">
                    <div>
                      <h3 className="text-lg font-semibold text-slate-800 mb-1 line-clamp-1">
                        {property.title}
                      </h3>
                      <p className="text-slate-600 text-sm line-clamp-2">
                        {property.description}
                      </p>
                    </div>

                    {/* Details */}
                    <div className="grid grid-cols-2 gap-3 text-sm text-slate-600">
                      <span className="flex items-center gap-2">
                        <HomeIcon className="h-4 w-4" />
                        {property.property_type || 'Type'}
                      </span>
                      <span className="flex items-center gap-2">
                        <span className="inline-block w-2 h-2 rounded-full bg-slate-300"></span>
                        {property.area || 'Area'}
                      </span>
                      <span className="flex items-center gap-2">
                        <span className="inline-block w-2 h-2 rounded-full bg-slate-300"></span>
                        {property.bedrooms} bed
                      </span>
                      <span className="flex items-center gap-2">
                        <span className="inline-block w-2 h-2 rounded-full bg-slate-300"></span>
                        {property.bathrooms} bath
                      </span>
                    </div>

                    {/* Price */}
                    <div className="flex items-center justify-between pt-4 border-t border-slate-200 mt-auto">
                      <div>
                        <p className="text-2xl font-semibold text-slate-900">
                          PKR {property.price.toLocaleString()}
                        </p>
                        <p className="text-xs text-slate-500">{property.area || property.city}</p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          router.push(`/properties/${property._id}`)
                        }}
                        className="p-2 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 transition-all border border-slate-200"
                        aria-label="View listing"
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

        {/* Main Content Card */}
        <div className="mt-12 bg-white/70 backdrop-blur-xl border border-slate-200 shadow-lg rounded-3xl p-8 md:p-12">
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
      </div>
    </div>
  )
}

