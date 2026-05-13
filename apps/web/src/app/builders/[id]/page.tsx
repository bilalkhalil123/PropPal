"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { HomeModernIcon, MapPinIcon, CalendarIcon, ChatBubbleLeftRightIcon, ArrowLeftIcon } from "@heroicons/react/24/outline"
import { api } from "@/lib/api-client"
import { useCurrentUser } from "@/hooks/useCurrentUser"
import { startAndNavigateToConversation } from "@/lib/conversation-utils"
import ServiceModal from "@/components/modals/ServiceModal"

type Builder = {
  id?: string
  _id?: string
  company_name: string
  specialization: string[]
  experience_years: number
  rating?: number
  location?: { city: string }
  about?: string
  portfolio_images?: string[]
  user_id?: string
}

type Service = {
  id?: string
  _id?: string
  title: string
  description: string
  category: string
  base_price: number
  price_unit: string
  estimated_duration?: string
  service_features?: string[]
  service_images?: string[]
  builder_id: string
}

export default function BuilderProfilePage() {
  const params = useParams()
  const router = useRouter()
  const { clerkId, isAuthenticated } = useCurrentUser()
  
  const [builder, setBuilder] = useState<Builder | null>(null)
  const [services, setServices] = useState<Service[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  const [isStartingChat, setIsStartingChat] = useState(false)
  const [selectedService, setSelectedService] = useState<Service | null>(null)

  useEffect(() => {
    async function fetchData() {
      if (!params.id) return
      
      try {
        setLoading(true)
        const [builderData, servicesData] = await Promise.all([
          api.builders.getById(params.id as string),
          api.builders.getServicesByBuilderId(params.id as string)
        ])
        
        setBuilder(builderData as Builder)
        setServices((servicesData as any) || [])
      } catch (err: any) {
        console.error("Failed to fetch builder data:", err)
        setError(err.message || "Failed to load builder profile")
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
  }, [params.id])

  const handleContact = async () => {
    if (!isAuthenticated || !clerkId) {
      window.location.href = `/sign-in?redirect=/builders/${params.id}`
      return
    }
    const builderUserId = builder?.user_id
    if (!builderUserId) {
      alert('Unable to contact builder. Builder user information not available.')
      return
    }
    setIsStartingChat(true)
    try {
      const result = await startAndNavigateToConversation({
        clerkId,
        participantId: builderUserId,
        conversationType: 'direct',
        initialMessage: `Hi, I'm interested in your services at ${builder.company_name}.`,
      })
      if (!result.success) {
        alert(result.error || 'Failed to start conversation')
      }
    } catch (error) {
      console.error('Error starting conversation:', error)
      alert('Failed to start conversation')
    } finally {
      setIsStartingChat(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-amber-600"></div>
      </div>
    )
  }

  if (error || !builder) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="bg-red-50 text-red-600 p-4 rounded-xl flex items-center justify-center">
          <p>{error || "Builder not found."}</p>
        </div>
        <button onClick={() => router.back()} className="mt-4 flex items-center text-amber-600 hover:text-amber-700">
          <ArrowLeftIcon className="h-4 w-4 mr-1" />
          Back
        </button>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 py-12">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <button 
          onClick={() => router.back()} 
          className="flex items-center text-slate-500 hover:text-amber-600 transition-colors"
        >
          <ArrowLeftIcon className="h-4 w-4 mr-1" />
          Back to results
        </button>

        {/* Builder Profile Header */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="p-8">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
                  <HomeModernIcon className="h-8 w-8 text-amber-700" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">{builder.company_name}</h1>
                  {builder.location?.city && (
                    <div className="flex items-center text-gray-600 mt-1">
                      <MapPinIcon className="h-4 w-4 mr-1" />
                      <span>{builder.location.city}</span>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
                <div className="flex items-center gap-4 text-sm text-gray-700 border-r border-slate-200 pr-4">
                  <div className="flex items-center">
                    <CalendarIcon className="h-5 w-5 text-gray-400 mr-1.5" />
                    <span className="font-medium">{builder.experience_years} years</span>
                  </div>
                  {builder.rating && (
                    <div className="flex items-center">
                      <span className="text-yellow-500 text-lg leading-none mr-1">★</span>
                      <span className="font-medium">{builder.rating}</span>
                    </div>
                  )}
                </div>
                <button
                  onClick={handleContact}
                  disabled={isStartingChat}
                  className="px-6 py-2.5 rounded-xl bg-amber-600 text-white font-medium hover:bg-amber-700 transition-colors flex items-center gap-2 disabled:opacity-50 shadow-sm"
                >
                  {isStartingChat ? (
                    <>
                      <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Starting...
                    </>
                  ) : (
                    <>
                      <ChatBubbleLeftRightIcon className="h-5 w-5" />
                      Contact Builder
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="md:col-span-2 space-y-6">
                {builder.about && (
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 mb-3">About Us</h2>
                    <p className="text-gray-600 leading-relaxed">{builder.about}</p>
                  </div>
                )}
                
                {builder.portfolio_images && builder.portfolio_images.length > 0 && (
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 mb-3">Portfolio</h2>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                      {builder.portfolio_images.map((url, idx) => (
                        <div key={idx} className="relative aspect-video overflow-hidden rounded-xl bg-gray-100">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={url}
                            alt={`Portfolio ${idx + 1}`}
                            className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              
              <div>
                {builder.specialization && builder.specialization.length > 0 && (
                  <div className="bg-slate-50 rounded-xl p-5 border border-slate-100">
                    <h2 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wider">Specializations</h2>
                    <div className="flex flex-wrap gap-2">
                      {builder.specialization.map((spec, idx) => (
                        <span key={idx} className="bg-white text-amber-800 border border-amber-200 px-3 py-1.5 rounded-lg text-sm font-medium">
                          {spec}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Builder Services List */}
        <div>
          <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
            Services Offered
            <span className="bg-amber-100 text-amber-800 text-sm py-0.5 px-2.5 rounded-full font-medium">
              {services.length}
            </span>
          </h2>
          
          {services.length === 0 ? (
            <div className="bg-white rounded-2xl p-8 text-center border border-slate-200 text-slate-500">
              No services listed by this builder yet.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {services.map((service, idx) => (
                <div key={service.id || service._id || idx} className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 hover:shadow-md transition-shadow flex flex-col">
                  <div className="mb-4 flex justify-between items-start">
                    <span className="inline-block px-2.5 py-1 bg-slate-100 text-slate-700 text-xs font-medium rounded-lg uppercase tracking-wider mb-2">
                      {service.category}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-gray-900 mb-2 line-clamp-2">{service.title}</h3>
                  <p className="text-gray-600 text-sm line-clamp-3 mb-6 flex-grow">{service.description}</p>
                  
                  <div className="flex items-end justify-between mt-auto pt-4 border-t border-slate-100">
                    <div>
                      <div className="text-xs text-gray-500 mb-0.5">Starting at</div>
                      <div className="text-lg font-bold text-amber-600">
                        ${service.base_price.toLocaleString()} <span className="text-sm font-normal text-gray-500">/ {service.price_unit}</span>
                      </div>
                    </div>
                    <button
                      onClick={() => setSelectedService(service)}
                      className="px-4 py-2 bg-amber-50 text-amber-700 font-medium text-sm rounded-xl hover:bg-amber-100 transition-colors"
                    >
                      View Details
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      
      {/* Service Modal */}
      {selectedService && (
        <ServiceModal
          isOpen={!!selectedService}
          service={selectedService as any}
          onClose={() => setSelectedService(null)}
        />
      )}
    </div>
  )
}
