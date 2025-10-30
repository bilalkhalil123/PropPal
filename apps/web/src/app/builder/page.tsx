"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useCurrentUser } from "@/hooks/useCurrentUser"
import {
  MagnifyingGlassIcon,
  WrenchScrewdriverIcon,
  PlusIcon,
  ChatBubbleLeftRightIcon,
  StarIcon,
} from "@heroicons/react/24/outline"
import { api } from "@/lib/api-client"
import { Button } from "@/components/ui/button"

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
  title: string
  description: string
  category: string
  base_price?: number
  price_unit?: string
  service_features?: string[]
}

export default function BuilderPage() {
  const { user, loading, isAuthenticated, clerkId } = useCurrentUser()
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState("")
  const [builderProfile, setBuilderProfile] = useState<BuilderProfile | null>(null)
  const [builderServices, setBuilderServices] = useState<BuilderService[]>([])
  const [dataLoading, setDataLoading] = useState(false)
  const [dataError, setDataError] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated || loading) return
    if (!clerkId) return
    let cancelled = false
    const load = async () => {
      try {
        setDataLoading(true)
        setDataError(null)
        const [profile, services] = await Promise.all([
          api.builders.getProfile(clerkId).catch(() => null) as Promise<BuilderProfile | null>,
          api.builders.getServices(clerkId).catch(() => []) as Promise<BuilderService[]>,
        ])
        if (!cancelled) {
          setBuilderProfile(profile)
          setBuilderServices(services || [])
        }
      } catch (err: any) {
        if (!cancelled) setDataError(err?.message || "Failed to load builder data")
      } finally {
        if (!cancelled) setDataLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [isAuthenticated, loading, clerkId])

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push("/sign-in")
    }
  }, [loading, isAuthenticated, router])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      router.push(`/chat?q=${encodeURIComponent(searchQuery)}`)
    }
  }

  const handleCreateProfile = () => {
    router.push("/chat?q=Create my builder profile")
  }

  const handleManageServices = () => {
    router.push("/chat?q=Manage my services")
  }

  return (
    <div className="min-h-screen" style={{ background: "radial-gradient(1200px 600px at 10% -10%, rgba(224,164,88,0.06), transparent 60%), radial-gradient(800px 400px at 90% 10%, rgba(13,27,42,0.05), transparent 60%), var(--background)" }}>
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="space-y-8">
          {/* Search Section */}
          <div className="bg-white/70 backdrop-blur rounded-2xl shadow-card border border-slate-200 p-8">
            <div className="mb-6">
              <h1 className="text-4xl font-bold text-slate-900 mb-2">Builder Dashboard</h1>
              <p className="text-slate-600">Manage your profile, services, and connect with clients</p>
            </div>
            <form onSubmit={handleSearch} className="flex gap-3">
              <div className="flex-1 relative">
                <MagnifyingGlassIcon className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Ask me anything about your profile or services..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-3.5 border border-slate-300 rounded-xl focus:ring-2 focus:ring-[color:var(--color-gold)] focus:border-transparent transition-all text-slate-900 placeholder:text-slate-400 bg-white"
                />
              </div>
              <Button type="submit" className="flex items-center gap-2">
                <ChatBubbleLeftRightIcon className="h-5 w-5" />
                Chat
              </Button>
            </form>
            <p className="text-sm text-slate-500 mt-3">
              💡 Try: "Update my profile", "Add new service", "View my ratings"
            </p>
          </div>

          {/* Profile Section */}
          {dataLoading && (
            <div className="bg-white/70 backdrop-blur rounded-2xl shadow-card border border-slate-200 p-8">
              <p className="text-slate-600">Loading your builder data…</p>
            </div>
          )}

          {dataError && (
            <div className="bg-white rounded-2xl shadow-sm border border-red-200 p-8 bg-red-50">
              <p className="text-red-700 font-medium">{dataError}</p>
            </div>
          )}

          {builderProfile ? (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
              <div className="flex items-center justify-between mb-8">
                <div>
                  <h2 className="text-3xl font-bold text-slate-900">{builderProfile.company_name}</h2>
                  <p className="text-slate-600 mt-1">Your professional profile</p>
                </div>
                <Button onClick={() => router.push("/chat?q=Update my builder profile")} variant="ghost" className="px-6 py-2.5 text-sm">
                  Edit Profile
                </Button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Company Info */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-sm text-slate-600 font-medium">Experience</span>
                    <span className="text-lg font-bold text-slate-900">{builderProfile.experience_years} years</span>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-sm text-slate-600 font-medium">Founded</span>
                    <span className="text-lg font-bold text-slate-900">{builderProfile.founded_year}</span>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-sm text-slate-600 font-medium">Location</span>
                    <span className="text-lg font-bold text-slate-900">{builderProfile.location.city}</span>
                  </div>
                  {builderProfile.rating && (
                    <div className="flex items-center justify-between p-4 bg-amber-50 rounded-lg border border-amber-200">
                      <span className="text-sm text-slate-600 font-medium">Rating</span>
                      <div className="flex items-center gap-2">
                        <StarIcon className="h-5 w-5 text-amber-500 fill-amber-500" />
                        <span className="text-lg font-bold text-slate-900">{builderProfile.rating}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Specialization */}
                <div>
                  <h4 className="text-sm font-semibold text-slate-900 mb-4">Specializations</h4>
                  <div className="flex flex-wrap gap-2">
                    {builderProfile.specialization.map((spec, index) => (
                      <span
                        key={index}
                        className="bg-amber-100 text-amber-800 px-4 py-2 rounded-full text-sm font-medium"
                      >
                        {spec}
                      </span>
                    ))}
                  </div>
                  {builderProfile.about && (
                    <div className="mt-6">
                      <h4 className="text-sm font-semibold text-slate-900 mb-2">About</h4>
                      <p className="text-slate-600 leading-relaxed">{builderProfile.about}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white/70 backdrop-blur rounded-2xl shadow-card border border-slate-200 p-12 text-center">
              <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <WrenchScrewdriverIcon className="h-8 w-8 text-slate-400" />
              </div>
              <h2 className="text-2xl font-bold text-slate-900 mb-3">No Profile Found</h2>
              <p className="text-slate-600 mb-8 max-w-md mx-auto">
                Create your builder profile to start managing your services and connecting with clients.
              </p>
              <Button onClick={handleCreateProfile} className="inline-flex items-center gap-2">
                <PlusIcon className="h-5 w-5" />
                Create Your Profile
              </Button>
            </div>
          )}

          {/* Services Section */}
          {builderProfile && (
            <div className="bg-white/70 backdrop-blur rounded-2xl shadow-card border border-slate-200 p-8">
              <div className="flex items-center justify-between mb-8">
                <div>
                  <h2 className="text-2xl font-bold text-slate-900">Your Services</h2>
                  <p className="text-slate-600 mt-1">Manage and showcase your offerings</p>
                </div>
                <Button onClick={handleManageServices} variant="ghost" className="px-6 py-2.5 text-sm">
                  Manage Services
                </Button>
              </div>

              {builderServices.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {builderServices.map((service) => (
                    <div key={service._id} className="border border-slate-200 rounded-xl p-6 hover:shadow-elevated transition-all duration-300 bg-white/70 backdrop-blur">
                      <div className="flex items-start justify-between mb-3">
                        <h3 className="font-semibold text-lg text-slate-900 flex-1">{service.title}</h3>
                      </div>
                      <p className="text-sm text-slate-600 mb-4 line-clamp-2">{service.description}</p>
                      <div className="space-y-2 text-xs text-slate-500 mb-4 pb-4 border-b border-slate-200">
                        <div>
                          <span className="font-medium">Category:</span> {service.category}
                        </div>
                        {(service.base_price || service.price_unit) && (
                          <div>
                            <span className="font-medium">Price:</span>{" "}
                            {service.base_price ? `Rs ${service.base_price.toLocaleString()}` : ""}
                            {service.price_unit ? ` ${service.price_unit}` : ""}
                          </div>
                        )}
                      </div>
                      {service.service_features && service.service_features.length > 0 && (
                        <div className="text-xs">
                          <span className="font-medium text-slate-700">Features:</span>
                          <div className="flex flex-wrap gap-1 mt-2">
                            {service.service_features.slice(0, 3).map((feature, idx) => (
                              <span key={idx} className="bg-amber-100 text-amber-700 px-2 py-1 rounded">
                                {feature}
                              </span>
                            ))}
                            {service.service_features.length > 3 && (
                              <span className="text-slate-500">+{service.service_features.length - 3} more</span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 bg-slate-50 rounded-xl border border-slate-200">
                  <p className="text-slate-600 mb-4">No services added yet</p>
                  <button
                    onClick={handleManageServices}
                    className="text-amber-600 hover:text-amber-700 font-semibold text-sm"
                  >
                    Add your first service →
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

