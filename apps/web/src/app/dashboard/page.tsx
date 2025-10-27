'use client'

import { useEffect } from 'react'
import { useCurrentUser } from '@/hooks/useCurrentUser'
import { useRouter } from 'next/navigation'

export default function DashboardPage() {
  const { user, loading, isAuthenticated } = useCurrentUser()
  const router = useRouter()

  useEffect(() => {
    if (!loading && isAuthenticated && user) {
      // Redirect based on user role
      switch (user.role) {
        case 'buyer':
          router.push('/buyer')
          break
        case 'builder':
          router.push('/builder')
          break
        case 'seller':
          router.push('/seller')
          break
        default:
          // Default to buyer dashboard
          router.push('/buyer')
      }
    } else if (!loading && !isAuthenticated) {
      router.push('/sign-in')
    }
  }, [user, loading, isAuthenticated, router])

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Redirecting to your dashboard...</p>
      </div>
    </div>
  )
}
