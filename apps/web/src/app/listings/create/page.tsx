'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  SparklesIcon,
  PhotoIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import dynamic from 'next/dynamic'

// Dynamically import LocationPicker to avoid SSR issues with Leaflet
const LocationPicker = dynamic(() => import('@/components/LocationPicker'), {
  ssr: false,
  loading: () => (
    <div className="h-[350px] w-full bg-slate-200 animate-pulse rounded-2xl" />
  ),
})

interface PropertyFormData {
  title: string
  description: string
  price: string
  property_type: string
  area_sqft: string
  bedrooms: string
  bathrooms: string
  floors: string
  city: string
  area: string
  lng: string
  lat: string
  images: string[]
}

const REQUIRED_FIELDS: (keyof PropertyFormData)[] = [
  'title',
  'description',
  'price',
  'property_type',
  'area_sqft',
  'bedrooms',
  'bathrooms',
  'city',
  'area',
]

export default function CreateListingPage() {
  const { isAuthenticated, clerkId, loading } = useCurrentUser()
  const router = useRouter()
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL

  const [formData, setFormData] = useState<PropertyFormData>({
    title: '',
    description: '',
    price: '',
    property_type: '',
    area_sqft: '',
    bedrooms: '',
    bathrooms: '',
    floors: '1',
    city: '',
    area: '',
    lng: '',
    lat: '',
    images: [],
  })

  const [statusMessage, setStatusMessage] = useState<string>('')
  const [statusType, setStatusType] = useState<'info' | 'success' | 'error'>('info')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [uploadingImages, setUploadingImages] = useState(false)
  const [isGeneratingDescription, setIsGeneratingDescription] = useState(false)

  const handleInputChange = (field: keyof PropertyFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const handleLocationChange = (lat: number, lng: number) => {
    setFormData((prev) => ({
      ...prev,
      lat: lat.toString(),
      lng: lng.toString(),
    }))
  }

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setUploadingImages(true)
    setStatusMessage('Uploading images...')
    setStatusType('info')

    try {
      if (!API_BASE_URL || !clerkId) {
        throw new Error('API URL or Clerk ID not available')
      }

      const fd = new FormData()
      Array.from(files).forEach((file) => {
        fd.append('files', file)
      })

      const response = await fetch(
        `${API_BASE_URL}/api/storage/upload?clerk_id=${encodeURIComponent(clerkId)}`,
        { method: 'POST', body: fd },
      )

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }))
        throw new Error(errorData.detail || 'Failed to upload images')
      }

      const result = await response.json()
      setFormData((prev) => ({
        ...prev,
        images: [...prev.images, ...result.urls],
      }))
      setStatusMessage(`${result.count} image(s) uploaded successfully!`)
      setStatusType('success')
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : 'Failed to upload images'
      console.error('Error uploading images:', error)
      setStatusMessage(msg)
      setStatusType('error')
    } finally {
      setUploadingImages(false)
      e.target.value = ''
    }
  }

  const removeImage = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      images: prev.images.filter((_, i) => i !== index),
    }))
  }

  const generateDescription = async () => {
    setIsGeneratingDescription(true)
    setStatusMessage('Generating description...')
    setStatusType('info')

    try {
      if (!API_BASE_URL || !clerkId) {
        throw new Error('API URL or Clerk ID not available')
      }

      const propertyData = {
        title: formData.title || 'Property',
        description: formData.description || '',
        price: formData.price ? parseFloat(formData.price) : null,
        property_type: formData.property_type || '',
        area_sqft: formData.area_sqft ? parseFloat(formData.area_sqft) : null,
        bedrooms: formData.bedrooms ? parseInt(formData.bedrooms) : null,
        bathrooms: formData.bathrooms ? parseInt(formData.bathrooms) : null,
        floors: formData.floors ? parseInt(formData.floors) : null,
        city: formData.city || '',
        area: formData.area || '',
      }

      const response = await fetch(
        `${API_BASE_URL}/api/properties/generate-description?clerk_id=${encodeURIComponent(clerkId)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(propertyData),
        },
      )

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ detail: 'Failed to generate description' }))
        throw new Error(errorData.detail || 'Failed to generate description')
      }

      const result = await response.json()
      if (result.description) {
        setFormData((prev) => ({ ...prev, description: result.description }))
        setStatusMessage('Description generated successfully!')
        setStatusType('success')
      } else {
        throw new Error('No description generated')
      }
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : 'Failed to generate description'
      console.error('Error generating description:', error)
      setStatusMessage(msg)
      setStatusType('error')
    } finally {
      setIsGeneratingDescription(false)
    }
  }

  const getMissingFieldsList = () => {
    return REQUIRED_FIELDS.filter((field) => {
      const value = formData[field]
      return !value || value === ''
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setStatusMessage('Creating property listing...')
    setStatusType('info')

    try {
      if (!API_BASE_URL || !clerkId) {
        throw new Error('API URL or Clerk ID not available')
      }

      const price = parseFloat(formData.price)
      const areaSqft = parseFloat(formData.area_sqft)
      const bedrooms = parseInt(formData.bedrooms)
      const bathrooms = parseInt(formData.bathrooms)
      const lng = formData.lng ? parseFloat(formData.lng) : null
      const lat = formData.lat ? parseFloat(formData.lat) : null

      if (isNaN(price) || price <= 0) throw new Error('Price must be a valid positive number')
      if (isNaN(areaSqft) || areaSqft <= 0) throw new Error('Area must be a valid positive number')
      if (isNaN(bedrooms) || bedrooms < 0) throw new Error('Bedrooms must be a valid non-negative number')
      if (isNaN(bathrooms) || bathrooms < 0) throw new Error('Bathrooms must be a valid non-negative number')
      if (formData.lng && (lng === null || isNaN(lng))) throw new Error('Longitude must be a valid number')
      if (formData.lat && (lat === null || isNaN(lat))) throw new Error('Latitude must be a valid number')

      const payload: Record<string, unknown> = {
        title: formData.title.trim(),
        description: formData.description.trim(),
        price,
        property_type: formData.property_type,
        area_sqft: areaSqft,
        bedrooms,
        bathrooms,
        floors: parseInt(formData.floors) || 1,
        city: formData.city.trim(),
        area: formData.area.trim(),
        images: formData.images.filter((img) => img.trim() !== ''),
      }

      if (lng !== null && !isNaN(lng)) payload.lng = lng
      if (lat !== null && !isNaN(lat)) payload.lat = lat

      const response = await fetch(
        `${API_BASE_URL}/api/properties?clerk_id=${encodeURIComponent(clerkId)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        },
      )

      if (!response.ok) {
        let errorMessage = 'Failed to create property listing'
        try {
          const errorData = await response.json()
          if (errorData.detail) {
            if (Array.isArray(errorData.detail)) {
              errorMessage = errorData.detail
                .map((err: Record<string, unknown>) => {
                  if (typeof err === 'object' && err.msg) {
                    return `${(err.loc as string[])?.join('.')}: ${err.msg}`
                  }
                  return String(err)
                })
                .join(', ')
            } else {
              errorMessage = String(errorData.detail)
            }
          } else if (errorData.message) {
            errorMessage = String(errorData.message)
          }
        } catch {
          errorMessage = response.statusText || 'Unknown error occurred'
        }
        throw new Error(errorMessage)
      }

      setStatusMessage('Property listing created successfully! Amenities will be enriched shortly.')
      setStatusType('success')

      setTimeout(() => {
        router.push('/seller')
      }, 1500)
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : 'Failed to create property listing'
      console.error('Error creating property:', error)
      setStatusMessage(msg)
      setStatusType('error')
    } finally {
      setIsSubmitting(false)
    }
  }

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/sign-in')
    }
  }, [loading, isAuthenticated, router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[linear-gradient(to_bottom,rgba(249,249,249,0.85),rgba(237,236,232,0.9))]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[color:var(--color-primary)] mx-auto mb-4" />
          <p className="text-[color:var(--color-primary)]">Loading...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  const missing = getMissingFieldsList()

  return (
    <div className="min-h-screen bg-[linear-gradient(to_bottom,rgba(249,249,249,0.85),rgba(237,236,232,0.9))] text-[color:var(--color-primary)]">
      <div className="max-w-4xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-4 text-[color:var(--color-primary)]">
            Create Property Listing
          </h1>
          <p className="text-slate-700">
            Fill out the details below. Pick your property location on the map and we&apos;ll
            automatically find nearby amenities. Use AI to generate a compelling description.
          </p>
        </div>

        {/* Status Message */}
        <AnimatePresence>
          {statusMessage && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className={`mb-6 rounded-xl p-4 flex items-center gap-3 ${
                statusType === 'success'
                  ? 'bg-green-50 border border-green-200 text-green-800'
                  : statusType === 'error'
                    ? 'bg-red-50 border border-red-200 text-red-800'
                    : 'bg-blue-50 border border-blue-200 text-blue-800'
              }`}
            >
              {statusType === 'success' ? (
                <CheckCircleIcon className="h-5 w-5 flex-shrink-0" />
              ) : statusType === 'error' ? (
                <ExclamationCircleIcon className="h-5 w-5 flex-shrink-0" />
              ) : (
                <SparklesIcon className="h-5 w-5 flex-shrink-0" />
              )}
              <span className="text-sm font-medium">{statusMessage}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid md:grid-cols-2 gap-6">
            {/* Title */}
            <div className="md:col-span-2">
              <label className="block text-sm font-semibold mb-2 text-slate-700">Title *</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => handleInputChange('title', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="e.g., Beautiful 3-Bedroom House in F-10"
                required
              />
            </div>

            {/* Price */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">
                Price (PKR) *
              </label>
              <input
                type="number"
                value={formData.price}
                onChange={(e) => handleInputChange('price', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="15000000"
                required
                min="0"
                step="0.01"
              />
            </div>

            {/* Property Type */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">
                Property Type *
              </label>
              <select
                value={formData.property_type}
                onChange={(e) => handleInputChange('property_type', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                required
              >
                <option value="">Select type</option>
                <option value="house">House</option>
                <option value="apartment">Apartment</option>
                <option value="plot">Plot</option>
                <option value="commercial">Commercial</option>
                <option value="villa">Villa</option>
                <option value="flat">Flat</option>
              </select>
            </div>

            {/* Area (sqft) */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">
                Area (sqft) *
              </label>
              <input
                type="number"
                value={formData.area_sqft}
                onChange={(e) => handleInputChange('area_sqft', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="2500"
                required
                min="0"
                step="0.01"
              />
            </div>

            {/* Bedrooms */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">Bedrooms *</label>
              <input
                type="number"
                value={formData.bedrooms}
                onChange={(e) => handleInputChange('bedrooms', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="3"
                required
                min="0"
              />
            </div>

            {/* Bathrooms */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">Bathrooms *</label>
              <input
                type="number"
                value={formData.bathrooms}
                onChange={(e) => handleInputChange('bathrooms', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="2"
                required
                min="0"
              />
            </div>

            {/* Floors */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">Floors</label>
              <input
                type="number"
                value={formData.floors}
                onChange={(e) => handleInputChange('floors', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="1"
                min="1"
              />
            </div>

            {/* City */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">City *</label>
              <input
                type="text"
                value={formData.city}
                onChange={(e) => handleInputChange('city', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="Islamabad"
                required
              />
            </div>

            {/* Area/Sector */}
            <div>
              <label className="block text-sm font-semibold mb-2 text-slate-700">
                Area/Sector *
              </label>
              <input
                type="text"
                value={formData.area}
                onChange={(e) => handleInputChange('area', e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="F-10/3"
                required
              />
            </div>
          </div>

          {/* Location Picker Map */}
          <div>
            <label className="block text-sm font-semibold mb-2 text-slate-700">
              Property Location *
            </label>
            <p className="text-xs text-slate-500 mb-3">
              Click on the map to pin your property&apos;s exact location. Nearby amenities (schools, hospitals, etc.) will be automatically detected.
            </p>
            <LocationPicker
              lat={formData.lat ? parseFloat(formData.lat) : undefined}
              lng={formData.lng ? parseFloat(formData.lng) : undefined}
              onLocationChange={handleLocationChange}
            />
          </div>

          {/* Image Upload Section */}
          <div>
            <label className="block text-sm font-semibold mb-2 text-slate-700">
              Property Images
            </label>
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 cursor-pointer transition-all">
                  <PhotoIcon className="h-5 w-5" />
                  {uploadingImages ? 'Uploading...' : 'Upload Images'}
                  <input
                    type="file"
                    multiple
                    accept="image/*"
                    onChange={handleImageUpload}
                    className="hidden"
                    disabled={uploadingImages}
                  />
                </label>
                {uploadingImages && (
                  <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[color:var(--color-primary)]" />
                    <span className="text-sm text-slate-600">Uploading...</span>
                  </div>
                )}
              </div>

              {/* Image Preview Grid */}
              {formData.images.length > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {formData.images.map((url, index) => (
                    <div key={index} className="relative group">
                      <img
                        src={url}
                        alt={`Property ${index + 1}`}
                        className="w-full h-32 object-cover rounded-xl border border-slate-200"
                      />
                      <button
                        type="button"
                        onClick={() => removeImage(index)}
                        className="absolute top-2 right-2 p-1 rounded-full bg-red-500 text-white opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Description — at the bottom so user fills all fields first, then generates */}
          <div>
            <label className="block text-sm font-semibold mb-2 text-slate-700">
              Description *
            </label>
            <p className="text-xs text-slate-500 mb-3">
              Fill in all details above first, then use AI to generate a professional description.
            </p>
            <div className="relative">
              <textarea
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                rows={5}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-[color:var(--color-primary)] focus:border-transparent"
                placeholder="Describe your property or click Generate below..."
                required
              />
              <button
                type="button"
                onClick={generateDescription}
                disabled={isGeneratingDescription}
                className="mt-2 px-5 py-2.5 text-sm font-semibold rounded-xl bg-[linear-gradient(to_right,#6366f1,#8b5cf6)] text-white hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
              >
                {isGeneratingDescription ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                    Generating...
                  </>
                ) : (
                  <>
                    <SparklesIcon className="h-4 w-4" />
                    Generate Description with AI
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex gap-4 pt-6">
            <button
              type="submit"
              disabled={isSubmitting || missing.length > 0}
              className="flex-1 px-8 py-4 rounded-xl font-semibold text-white bg-[linear-gradient(to_right,#f59e0b,var(--color-accent-gold))] hover:scale-105 active:scale-95 transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
            >
              {isSubmitting ? 'Creating...' : 'Create Listing'}
            </button>
            <button
              type="button"
              onClick={() => router.back()}
              className="px-6 py-4 rounded-xl font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 transition-all"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
