'use client'

import UserProfile from '@/components/UserProfile'
import AuthRequired from '@/components/AuthRequired'
import { useCurrentUser } from '@/hooks/useCurrentUser'

export default function ProfilePage() {
  const { isGuest, loading } = useCurrentUser()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[color:var(--color-accent-gold)]"></div>
      </div>
    )
  }

  if (isGuest) {
    return (
      <div className="min-h-screen bg-gray-50 py-12">
        <AuthRequired 
          title="Your Profile" 
          description="Sign in to view and manage your account details, track your activity, and customize your experience."
          role="user"
        />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="py-8">
        <UserProfile />
      </div>
    </div>
  )
}
