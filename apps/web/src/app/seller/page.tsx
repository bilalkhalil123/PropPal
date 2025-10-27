'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { UserButton } from '@clerk/nextjs'
import Link from 'next/link'
import { HomeIcon, UserIcon } from '@heroicons/react/24/outline'
import RoleDropdown from '@/components/RoleDropdown'

export default function SellerPage() {
  const { user, loading, isAuthenticated } = useCurrentUser()
  const router = useRouter()
  const [currentRole, setCurrentRole] = useState<'buyer' | 'seller' | 'builder'>('seller')

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
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center space-x-2 text-blue-600 hover:text-blue-700 transition-colors">
              <HomeIcon className="h-8 w-8" />
              <span className="text-2xl font-bold">PropPal</span>
            </Link>
            
            <div className="flex items-center space-x-4">
              <RoleDropdown currentRole={currentRole} onRoleChange={setCurrentRole} />
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600">Welcome, {user?.name || 'User'}</span>
                <UserButton afterSignOutUrl="/" />
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 text-center">
          <UserIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Seller Dashboard</h2>
          <p className="text-gray-600 mb-6">Coming soon! This will be where you can manage your property listings.</p>
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-green-800 text-sm">
              <strong>Note:</strong> Seller functionality will be implemented in the next iteration.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

