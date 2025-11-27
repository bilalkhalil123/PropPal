'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  MagnifyingGlassIcon,
  MapPinIcon,
  HomeIcon,
  FunnelIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
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
  const { user, loading, isAuthenticated } = useCurrentUser()
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState('')
  const [priceRange, setPriceRange] = useState([0, 50000000])
  const [selectedCity, setSelectedCity] = useState<string | null>(null)
  const [selectedType, setSelectedType] = useState<string | null>(null)

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/sign-in')
    }
  }, [loading, isAuthenticated, router])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      router.push(`/chat?q=${encodeURIComponent(searchQuery)}`)
    }
  }

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
      images: ['/hero-house.svg'],
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
      images: ['/hero-house.svg'],
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
      images: ['/hero-house.svg'],
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
      images: ['/hero-house.svg'],
    },
  ]

  const filteredProperties = sampleProperties.filter((property) => {
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

  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--background)]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-[color:var(--color-primary)]"></div>
      </div>
    )

  if (!isAuthenticated) return null

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
        <motion.div layout className="grid sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {filteredProperties.map((property, idx) => (
            <motion.div
              key={property._id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              viewport={{ once: true }}
            >
              <Card className="group rounded-2xl bg-white/60 backdrop-blur-md border border-slate-200/70 hover:shadow-xl hover:scale-[1.02] transition-all">
                <div className="h-48 relative bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-accent-gold)] flex items-center justify-center">
                  <HomeIcon className="h-16 w-16 text-white/70" />
                </div>
                <CardHeader>
                  <CardTitle className="text-lg font-semibold text-slate-900 group-hover:text-[color:var(--color-primary)] transition-colors">
                    {property.title}
                  </CardTitle>
                  <CardDescription className="flex items-center gap-1 text-slate-600 text-sm">
                    <MapPinIcon className="h-4 w-4" /> {property.city}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-lg font-semibold text-[color:var(--color-accent-gold)]">
                      {formatPrice(property.price)}
                    </span>
                    <Badge
                      variant="secondary"
                      className="bg-[rgba(224,164,88,0.15)] text-[color:var(--color-accent-gold)] rounded-full"
                    >
                      {property.property_type}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-3 text-sm text-slate-600 border-t border-slate-200 pt-3">
                  <span>{property.bedrooms} beds</span>
                  <span>{property.bathrooms} baths</span>
                  <span>{property.area_sqft} sqft</span>
                </div>
                  <div className="mt-4 flex justify-end">
                    <Link
                      href={`/properties/${property._id}`}
                      className="text-sm font-semibold text-[color:var(--color-primary)] hover:text-[color:var(--color-accent-gold)] transition-all"
                    >
                      View →
                    </Link>
            </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </div>
  )
}
